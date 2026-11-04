"""ScheduleService: Zeitreise durch alle Zeitplanarten mit simulierten Zeitgebern."""

import datetime as dt
import logging
from zoneinfo import ZoneInfo

import pytest

from custom_components.task_wheel.application.schedule_service import (
    TIMER_REMINDERS,
    timer_key,
)
from custom_components.task_wheel.const import limits
from custom_components.task_wheel.domain.deadline import DeadlineWindow
from custom_components.task_wheel.domain.enums import AfterOnce, Period, RoundOrigin
from custom_components.task_wheel.domain.models import (
    ManualTrigger,
    MaxPerPeriod,
    OnceTrigger,
    Recurring,
)

from ..domain import factories as f
from .world import DAY, World

BERLIN = ZoneInfo("Europe/Berlin")
KEY = timer_key("s1")
START = dt.datetime(2026, 11, 3, 10, tzinfo=BERLIN)  # Dienstag
MON, THU = 0, 3


def weekly(*weekdays: int, **overrides: object) -> Recurring:
    return Recurring(weekdays=frozenset(weekdays), time=dt.time(7), **overrides)  # type: ignore[arg-type]


def test_recurring_schedule_keeps_firing_week_after_week():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    assert world.schedules.arm("s1", START) == dt.datetime(2026, 11, 9, 7, tzinfo=BERLIN)
    for _ in range(4):
        world.timers.fire(KEY)
    starts = [
        r.started_at for r in sorted(world.history.rounds.values(), key=lambda r: r.started_at)
    ]
    assert starts == [dt.datetime(2026, 11, 9 + 7 * week, 7, tzinfo=BERLIN) for week in range(4)]
    assert {r.origin for r in world.history.rounds.values()} == {RoundOrigin.AUTO}
    assert world.timers.timers[KEY][0] == dt.datetime(2026, 12, 7, 7, tzinfo=BERLIN)
    assert len(world.events.drawn) == 4


def test_every_other_week_skips_the_week_in_between():
    world = World()
    world.put_schedule(trigger=weekly(MON, every_n_weeks=2, anchor=dt.date(2026, 11, 2)))
    world.schedules.arm("s1", START)
    world.timers.fire(KEY)
    assert world.timers.timers[KEY][0] == dt.datetime(2026, 11, 30, 7, tzinfo=BERLIN)


def test_early_callback_does_not_fire_the_same_slot_twice():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    planned = world.schedules.arm("s1", START)
    world.timers.fire(KEY, planned - dt.timedelta(seconds=2))
    assert world.timers.timers[KEY][0] == planned + 7 * DAY


@pytest.mark.parametrize(
    ("after", "expected_trigger", "expected_enabled", "expected_archived", "remains"),
    [
        (AfterOnce.KEEP_MANUAL, ManualTrigger(), True, False, True),
        (AfterOnce.ARCHIVE, None, False, True, True),
        (AfterOnce.DELETE, None, None, None, False),
    ],
)
def test_once_schedule_is_drawn_once_and_then_handled(
    after, expected_trigger, expected_enabled, expected_archived, remains
):
    world = World()
    when = dt.datetime(2026, 12, 19, 10, tzinfo=BERLIN)
    world.put_schedule(trigger=OnceTrigger(at=when, after=after))
    assert world.schedules.arm("s1", START) == when
    world.timers.fire(KEY)
    assert len(world.history.rounds) == 1
    assert KEY not in world.timers.timers
    stored = world.config.schedules.get("s1")
    assert (stored is not None) is remains
    if remains and expected_trigger is not None:
        assert stored.trigger == expected_trigger
    if remains:
        assert (stored.enabled, stored.archived) == (expected_enabled, expected_archived)


def test_manual_disabled_and_archived_schedules_get_no_timer():
    world = World()
    world.put_schedule(trigger=ManualTrigger())
    assert world.schedules.arm("s1", START) is None
    world.put_schedule(trigger=weekly(MON), enabled=False)
    assert world.schedules.arm("s1", START) is None
    world.put_schedule(trigger=weekly(MON), enabled=False, archived=True)
    assert world.schedules.arm("s1", START) is None
    assert world.timers.timers == {}


def test_changing_a_schedule_resets_only_its_own_timer():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    world.put_schedule(id="s2", slug="zweiter", name="Zweiter", trigger=weekly(THU))
    world.schedules.arm_all(START)
    other = world.timers.timers[timer_key("s2")]
    world.put_schedule(trigger=weekly(THU))
    world.schedules.arm("s1", START)
    assert world.timers.timers[KEY][0] == dt.datetime(2026, 11, 5, 7, tzinfo=BERLIN)
    assert world.timers.timers[timer_key("s2")] == other


def test_pausing_a_schedule_cancels_its_timer():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    world.schedules.arm("s1", START)
    world.put_schedule(trigger=weekly(MON), enabled=False)
    world.schedules.arm("s1", START)
    assert KEY not in world.timers.timers


def test_removed_schedule_cancels_its_timer_and_a_late_callback_does_nothing():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    world.schedules.arm("s1", START)
    _, callback = world.timers.timers[KEY]
    world.config.remove_schedule("s1")
    callback(START + 7 * DAY)
    assert world.history.rounds == {}
    world.schedules.arm("s1", START)
    assert KEY not in world.timers.timers


def test_failed_automatic_draw_is_logged_and_the_next_timer_is_still_set(caplog):
    world = World()
    world.put_schedule(trigger=weekly(MON))
    world.schedules.arm("s1", START)
    world.put_schedule(trigger=weekly(MON), enabled=False)  # ohne arm(): Zeitgeber läuft noch
    world.timers.fire(KEY)
    assert world.history.rounds == {} and KEY not in world.timers.timers
    assert "fehlgeschlagen" in caplog.text


def test_automatic_draw_with_nothing_due_is_skipped_quietly(caplog):
    world = World()
    world.put_schedule(trigger=weekly(MON))
    for task_id in ("t1", "t2"):
        world.config.put_task(
            f.task(id=task_id, frequency=MaxPerPeriod(count=1, period=Period.DAY))
        )
    caplog.set_level(logging.INFO)
    planned = world.schedules.arm("s1", START)
    world.draws.draw("s1", RoundOrigin.AUTO, planned)
    _, callback = world.timers.timers[KEY]
    callback(planned)
    assert "übersprungen" in caplog.text and "fehlgeschlagen" not in caplog.text
    assert len(world.history.rounds) == 1 and KEY in world.timers.timers


def test_next_run_is_none_unless_the_schedule_is_active_and_automatic():
    world = World()
    assert world.schedules.next_run(f.schedule(trigger=weekly(MON)), START) is not None
    assert world.schedules.next_run(f.schedule(trigger=weekly(MON), enabled=False), START) is None
    assert world.schedules.next_run(f.schedule(trigger=ManualTrigger()), START) is None


def test_arm_all_and_disarm_all_cover_every_schedule_and_the_reminder_check():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    world.put_schedule(id="s2", slug="zweiter", name="Zweiter", trigger=weekly(THU))
    world.schedules.arm_all(START)
    assert set(world.timers.timers) == {KEY, timer_key("s2"), TIMER_REMINDERS}
    world.schedules.disarm("s2")
    assert timer_key("s2") not in world.timers.timers
    world.schedules.disarm_all()
    assert world.timers.timers == {}


def test_reminder_check_runs_daily_at_nine_local_time():
    world = World()
    world.schedules.arm_reminders(START)
    assert world.timers.timers[TIMER_REMINDERS][0] == dt.datetime(2026, 11, 4, 9, tzinfo=BERLIN)
    world.timers.fire(TIMER_REMINDERS)
    assert world.timers.timers[TIMER_REMINDERS][0] == dt.datetime(2026, 11, 5, 9, tzinfo=BERLIN)


def test_manual_schedule_reminds_after_the_set_number_of_days():
    world = World()
    world.put_schedule(trigger=ManualTrigger(remind_after_days=7))
    world.draws.draw("s1", RoundOrigin.MANUAL, START)
    world.events.reminders.clear()
    world.schedules.arm_reminders(START)
    for day in range(1, 16):
        at = START + day * DAY
        world.timers.fire(TIMER_REMINDERS, at)
    assert [days for _, days in world.events.reminders] == [7, 14]
    assert {s.id for s, _ in world.events.reminders} == {"s1"}


def test_manual_draw_resets_the_reminder_clock():
    world = World()
    world.put_schedule(trigger=ManualTrigger(remind_after_days=7))
    world.draws.draw("s1", RoundOrigin.MANUAL, START)
    world.draws.draw("s1", RoundOrigin.MANUAL, START + 6 * DAY)
    world.schedules.check_reminders(START + 7 * DAY)
    assert world.events.reminders == []
    world.schedules.check_reminders(START + 13 * DAY)
    assert [days for _, days in world.events.reminders] == [7]


def test_failed_draw_leaves_a_once_schedule_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World()
    when = dt.datetime(2026, 12, 19, 10, tzinfo=BERLIN)
    world.put_schedule(trigger=OnceTrigger(at=when, after=AfterOnce.DELETE))
    world.schedules.arm("s1", START)
    monkeypatch.setattr(limits, "MAX_STORED_ROUNDS", 0)
    world.timers.fire(KEY)
    assert not world.history.rounds
    assert world.config.schedules["s1"].trigger == OnceTrigger(at=when, after=AfterOnce.DELETE)


def test_unexpected_error_still_arms_the_next_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World()
    world.put_schedule(trigger=weekly(MON))
    planned = world.schedules.arm("s1", START)

    def boom(*_args: object) -> None:
        raise KeyError

    monkeypatch.setattr(world.draws, "draw", boom)
    with pytest.raises(KeyError):
        world.timers.fire(KEY)
    assert world.timers.timers[KEY][0] == planned + 7 * DAY


def test_reminder_check_arms_the_next_check_even_if_reporting_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = World()
    world.put_schedule(trigger=ManualTrigger(remind_after_days=7))
    world.draws.draw("s1", RoundOrigin.MANUAL, START)

    def boom(*_args: object) -> None:
        raise KeyError

    monkeypatch.setattr(world.events, "reminder_due", boom)
    with pytest.raises(KeyError):
        world.schedules.check_reminders(START + 7 * DAY)
    assert TIMER_REMINDERS in world.timers.timers


def test_start_catches_up_a_once_schedule_missed_while_down() -> None:
    world = World()
    when = dt.datetime(2026, 11, 1, 10, tzinfo=BERLIN)
    world.put_schedule(trigger=OnceTrigger(at=when, after=AfterOnce.DELETE))
    world.schedules.arm_all(START)
    assert len(world.history.rounds) == 1
    assert "s1" not in world.config.schedules


def test_start_does_not_repeat_a_once_schedule_that_was_already_drawn() -> None:
    world = World()
    when = dt.datetime(2026, 11, 1, 10, tzinfo=BERLIN)
    world.put_schedule(trigger=OnceTrigger(at=when, after=AfterOnce.KEEP_MANUAL))
    world.schedules.arm_all(START)
    world.put_schedule(trigger=OnceTrigger(at=when, after=AfterOnce.KEEP_MANUAL))
    world.schedules.arm_all(START + DAY)
    assert len(world.history.rounds) == 1


def test_start_ignores_future_and_paused_once_schedules() -> None:
    world = World()
    world.put_schedule(trigger=OnceTrigger(at=START + DAY, after=AfterOnce.DELETE))
    world.put_schedule(
        id="s2",
        slug="zwei",
        name="Zwei",
        enabled=False,
        trigger=OnceTrigger(at=START - DAY, after=AfterOnce.DELETE),
    )
    world.schedules.arm_all(START)
    assert not world.history.rounds


# --- Manuelle Auslosung zieht den nächsten regulären Lauf vor ----------------------------------

WINDOW = DeadlineWindow(START, START + 2 * DAY)


def _commit_manual(world: World, now: dt.datetime = START):
    panel = world.draws.begin("s1", now, WINDOW, replace_next=True)
    world.draws.spin_rest(panel.id, now)
    round_ = world.draws.commit(panel.id, now)
    world.schedules.round_committed(round_, now)
    return round_


def test_manual_draw_replaces_the_next_regular_run_and_the_schedule_continues_after_it():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    assert world.schedules.arm("s1", START) == dt.datetime(2026, 11, 9, 7, tzinfo=BERLIN)
    round_ = _commit_manual(world)
    assert round_.replaces == dt.datetime(2026, 11, 9, 7, tzinfo=BERLIN)
    assert world.timers.timers[KEY][0] == dt.datetime(2026, 11, 16, 7, tzinfo=BERLIN)


def test_a_second_manual_draw_replaces_the_following_run():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    _commit_manual(world)
    later = START + dt.timedelta(minutes=5)
    assert _commit_manual(world, later).replaces == dt.datetime(2026, 11, 16, 7, tzinfo=BERLIN)
    assert world.schedules.next_run(world.config.schedules["s1"], later) == dt.datetime(
        2026, 11, 23, 7, tzinfo=BERLIN
    )


def test_replaced_run_stays_skipped_after_a_restart():
    world = World()
    world.put_schedule(trigger=weekly(MON))
    _commit_manual(world)
    world.timers.cancel_all()
    world.schedules.arm_all(START + DAY)
    assert world.timers.timers[KEY][0] == dt.datetime(2026, 11, 16, 7, tzinfo=BERLIN)


def test_manual_draw_of_a_once_schedule_finishes_it():
    world = World()
    at = dt.datetime(2026, 11, 20, 7, tzinfo=BERLIN)
    world.put_schedule(trigger=OnceTrigger(at=at, after=AfterOnce.ARCHIVE))
    world.schedules.arm("s1", START)
    _commit_manual(world)
    assert world.config.schedules["s1"].archived
    assert KEY not in world.timers.timers


def test_manual_only_schedule_needs_no_confirmation_and_replaces_nothing():
    world = World()
    panel = world.draws.begin("s1", START, WINDOW)
    world.draws.spin_rest(panel.id, START)
    assert world.draws.commit(panel.id, START).replaces is None
