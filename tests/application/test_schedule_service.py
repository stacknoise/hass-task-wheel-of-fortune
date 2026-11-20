"""ScheduleService: Termine im Raster, Zeitgeber, automatisches Auslosen, Erinnerung."""

import datetime as dt
import logging
from zoneinfo import ZoneInfo

import pytest

from custom_components.task_wheel.application.schedule_service import timer_key
from custom_components.task_wheel.domain.enums import IntervalUnit, RoundOrigin
from custom_components.task_wheel.domain.models import Interval

from ..domain import factories as f
from .world import DAY, World

BERLIN = ZoneInfo("Europe/Berlin")
KEY = timer_key("s1")
BEGIN = dt.datetime(2026, 11, 3, 18, tzinfo=BERLIN)
EVERY_THIRD_DAY = Interval(unit=IntervalUnit.DAY, every=3)


def auto(world: World, **overrides: object):
    values = {"start": BEGIN, "interval": EVERY_THIRD_DAY, "automatic": True} | overrides
    return world.put_schedule(**values)


def test_timer_runs_at_every_slot_of_the_grid_and_draws_automatically():
    world = World()
    auto(world)
    assert world.schedules.arm("s1", BEGIN - DAY) == BEGIN
    for index in range(3):
        planned, _ = world.timers.timers[KEY]
        assert planned == BEGIN + 3 * DAY * index
        world.timers.fire(KEY)
    assert sorted(r.period_index for r in world.history.rounds.values()) == [0, 1, 2]
    assert all(r.origin is RoundOrigin.AUTO for r in world.history.rounds.values())
    assert world.timers.timers[KEY][0] == BEGIN + 9 * DAY


def test_a_draw_gives_the_assignments_the_window_of_its_period():
    world = World()
    auto(world)
    world.schedules.arm("s1", BEGIN - DAY)
    world.timers.fire(KEY)
    (round_,) = world.history.rounds.values()
    assert {(a.starts_at, a.due_at) for a in round_.assignments} == {(BEGIN, BEGIN + 3 * DAY)}


def test_period_already_drawn_by_hand_is_not_drawn_again(caplog):
    world = World()
    auto(world)
    world.draws.draw("s1", RoundOrigin.MANUAL, BEGIN)  # Periode 0 von Hand
    caplog.set_level(logging.INFO)
    world.schedules.arm("s1", BEGIN - DAY)
    world.timers.fire(KEY)
    assert len(world.history.rounds) == 1
    assert "übersprungen" in caplog.text and KEY in world.timers.timers


def test_deleted_period_is_not_made_up_by_the_next_slot():
    world = World()
    auto(world)
    world.schedules.arm("s1", BEGIN - DAY)
    world.timers.fire(KEY)
    world.timers.fire(KEY)
    newest = max(world.history.rounds.values(), key=lambda r: r.period_index)
    world.history.remove_round(newest.id)
    world.timers.fire(KEY)
    assert sorted(r.period_index for r in world.history.rounds.values()) == [0, 2]


def test_manual_schedule_reminds_instead_of_drawing_when_a_period_is_due():
    world = World()
    world.put_schedule(start=BEGIN, interval=EVERY_THIRD_DAY, automatic=False)
    world.schedules.arm("s1", BEGIN - DAY)
    world.timers.fire(KEY)
    assert not world.history.rounds
    assert [(s.id, days) for s, days in world.events.reminders] == [("s1", 0)]


def test_manual_schedule_does_not_remind_when_the_open_period_lies_ahead():
    world = World()
    world.put_schedule(start=BEGIN, interval=EVERY_THIRD_DAY, automatic=False)
    world.draws.draw("s1", RoundOrigin.MANUAL, BEGIN)
    world.draws.draw("s1", RoundOrigin.MANUAL, BEGIN + dt.timedelta(minutes=5))
    world.schedules.arm("s1", BEGIN)
    world.timers.fire(KEY)  # Termin der Periode 1, Periode 2 ist die offene
    assert world.events.reminders == []


def test_manual_reminder_counts_the_days_since_the_last_draw():
    world = World()
    world.put_schedule(start=BEGIN, interval=EVERY_THIRD_DAY, automatic=False)
    world.draws.draw("s1", RoundOrigin.MANUAL, BEGIN)
    world.schedules.arm("s1", BEGIN)
    world.timers.fire(KEY)
    world.timers.fire(KEY)
    assert world.events.reminders[-1][1] == 6


def test_next_run_depends_on_mode_and_state():
    world = World()
    plan = auto(world)
    assert world.schedules.next_run(plan, BEGIN + DAY) == BEGIN + 3 * DAY
    assert world.schedules.next_run(plan, BEGIN - DAY) == BEGIN
    manual = world.put_schedule(start=BEGIN, interval=EVERY_THIRD_DAY, automatic=False)
    assert world.schedules.next_run(manual, BEGIN + 9 * DAY) == BEGIN  # offene Periode 0, fällig
    world.draws.draw("s1", RoundOrigin.MANUAL, BEGIN)
    assert world.schedules.next_run(manual, BEGIN) == BEGIN + 3 * DAY
    paused = f.schedule(enabled=False)
    assert world.schedules.next_run(paused, BEGIN) is None
    archived = f.schedule(enabled=False, archived=True)
    assert world.schedules.next_run(archived, BEGIN) is None


def test_disabled_archived_or_removed_schedules_get_no_timer():
    world = World()
    auto(world, enabled=False)
    assert world.schedules.arm("s1", BEGIN) is None and KEY not in world.timers.timers
    auto(world, enabled=False, archived=True)
    assert world.schedules.arm("s1", BEGIN) is None
    assert world.schedules.arm("fehlt", BEGIN) is None


def test_changing_a_schedule_resets_only_its_own_timer():
    world = World()
    auto(world)
    world.put_schedule(id="s2", slug="s2", start=BEGIN, automatic=True)
    world.schedules.arm_all(BEGIN - DAY)
    other = world.timers.timers[timer_key("s2")]
    world.schedules.save(auto(world, start=BEGIN + 5 * DAY), BEGIN - DAY)
    assert world.timers.timers[KEY][0] == BEGIN + 5 * DAY
    assert world.timers.timers[timer_key("s2")] == other


def test_pausing_or_deleting_cancels_the_timer_and_a_late_callback_does_nothing():
    world = World()
    auto(world)
    world.schedules.arm("s1", BEGIN - DAY)
    _, callback = world.timers.timers[KEY]
    world.schedules.delete("s1")
    assert KEY not in world.timers.timers
    callback(BEGIN)
    assert not world.history.rounds
    auto(world)
    world.schedules.arm("s1", BEGIN - DAY)
    world.schedules.disarm_all()
    assert not world.timers.timers


def test_failed_automatic_draw_is_logged_and_the_next_timer_is_still_set(caplog):
    world = World()
    auto(world)
    world.schedules.arm("s1", BEGIN - DAY)
    auto(world, enabled=False)  # ohne arm(): der Zeitgeber läuft noch, Auslosen ist abgelehnt
    world.timers.fire(KEY)
    assert world.history.rounds == {} and KEY not in world.timers.timers
    assert "fehlgeschlagen" in caplog.text


def test_automatic_draw_with_nobody_available_is_skipped_quietly(caplog):
    world = World()
    auto(world)
    for ident in ("p1", "p2"):
        world.config.remove_person(ident)
    caplog.set_level(logging.INFO)
    world.schedules.arm("s1", BEGIN - DAY)
    world.timers.fire(KEY)
    assert "übersprungen" in caplog.text and "fehlgeschlagen" not in caplog.text
    assert KEY in world.timers.timers


def test_unexpected_error_still_arms_the_next_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World()
    auto(world)
    planned = world.schedules.arm("s1", BEGIN - DAY)

    def boom(*_args: object) -> None:
        raise KeyError

    monkeypatch.setattr(world.draws, "draw", boom)
    with pytest.raises(KeyError):
        world.timers.fire(KEY)
    assert world.timers.timers[KEY][0] == planned + 3 * DAY


def test_early_callback_does_not_fire_the_same_slot_twice():
    world = World()
    auto(world)
    planned = world.schedules.arm("s1", BEGIN - DAY)
    world.timers.fire(KEY, planned - dt.timedelta(minutes=1))
    assert world.timers.timers[KEY][0] == planned + 3 * DAY
    assert len(world.history.rounds) == 1


def test_arm_all_arms_every_schedule_without_catching_up():
    world = World()
    auto(world)
    world.put_schedule(id="s2", slug="s2", start=BEGIN, automatic=False)
    world.schedules.arm_all(BEGIN + 10 * DAY)
    assert set(world.timers.timers) == {KEY, timer_key("s2")}
    assert not world.history.rounds
