"""DrawService: automatische und schrittweise Runden gegen In-Memory-Speicher."""

import datetime as dt

import pytest

from custom_components.task_wheel.const.limits import MAX_OPEN_PANEL_ROUNDS
from custom_components.task_wheel.domain.enums import (
    AssignmentStatus,
    Period,
    RoundOrigin,
    WeightingKind,
)
from custom_components.task_wheel.domain.errors import (
    DrawRejectedError,
    LimitReachedError,
    NotFoundError,
)
from custom_components.task_wheel.domain.models import MaxPerPeriod, WeeklyDaysAbsence

from ..domain import factories as f
from .world import DAY, World

NOW = f.NOW
AUTO, MANUAL = RoundOrigin.AUTO, RoundOrigin.MANUAL


def test_automatic_round_is_drawn_stored_and_reported():
    world = World(0.1, 0.9)
    round_ = world.draws.draw("s1", AUTO, NOW)
    assert world.history.rounds[round_.id] == round_
    assert world.events.drawn == [round_]
    assert (round_.origin, round_.started_at, round_.finished_at) == (AUTO, NOW, NOW)
    assert [(a.task_id, a.person_id, a.status) for a in round_.assignments] == [
        ("t1", "p1", AssignmentStatus.OPEN),
        ("t2", "p2", AssignmentStatus.OPEN),
    ]
    assert round_.assignments[0].due_at == NOW + 7 * DAY


def test_unknown_schedule_is_not_found():
    with pytest.raises(NotFoundError):
        World().draws.draw("fehlt", AUTO, NOW)


def test_archived_schedule_cannot_be_drawn_at_all():
    world = World()
    world.put_schedule(enabled=False, archived=True)
    for origin in (AUTO, MANUAL):
        with pytest.raises(DrawRejectedError):
            world.draws.draw("s1", origin, NOW)


def test_paused_schedule_is_skipped_automatically_but_can_be_drawn_by_hand():
    world = World()
    world.put_schedule(enabled=False)
    with pytest.raises(DrawRejectedError):
        world.draws.draw("s1", AUTO, NOW)
    assert world.draws.draw("s1", RoundOrigin.SERVICE, NOW).origin is RoundOrigin.SERVICE


def test_frequency_rule_removes_tasks_that_are_not_due():
    world = World(0.1)
    world.config.put_task(
        f.task(
            id="t1",
            allowed=frozenset({"p1", "p2"}),
            points=5,
            frequency=MaxPerPeriod(count=1, period=Period.DAY),
        )
    )
    world.draws.draw("s1", AUTO, NOW)
    second = world.draws.draw("s1", AUTO, NOW + dt.timedelta(hours=1))
    assert [a.task_id for a in second.assignments] == ["t2"]
    third = world.draws.draw("s1", AUTO, NOW + DAY)
    assert [a.task_id for a in third.assignments] == ["t1", "t2"]


def test_deleted_tasks_are_skipped():
    world = World()
    world.config.remove_task("t2")
    assert [a.task_id for a in world.draws.draw("s1", AUTO, NOW).assignments] == ["t1"]


def test_open_assignments_count_as_load_for_the_next_round():
    world = World(0.1)
    world.config.set_settings(f.settings(weighting=WeightingKind.FAIRNESS))
    first = world.draws.draw("s1", AUTO, NOW)
    assert {a.person_id for a in first.assignments} == {"p1"}
    second = world.draws.draw("s1", AUTO, NOW + DAY)
    # p1 trägt bereits offene Punkte: sein Segment im Rad ist deutlich kleiner als das von p2
    assert second.assignments[0].person_id == "p1"
    assert second.assignments[0].chance < 0.2


def test_absence_is_ignored_when_the_schedule_does_not_skip_absent():
    always = WeeklyDaysAbsence(weekdays=frozenset(range(7)))
    world = World(0.1)
    for ident in ("p1", "p2"):
        world.config.put_person(f.person(id=ident, slug=ident, name=ident, absences=(always,)))
    assert world.draws.draw("s1", AUTO, NOW).assignments == ()
    world.put_schedule(skip_absent=False)
    assert len(world.draws.draw("s1", AUTO, NOW + DAY).assignments) == 2


def test_panel_round_runs_step_by_step_and_is_stored_on_commit():
    world = World(0.1, 0.9)
    panel = world.draws.begin("s1", NOW)
    assert world.history.rounds == {}
    first = world.draws.spin(panel.id, NOW)
    assert (first.task_id, first.winner_id) == ("t1", "p1")
    rest = world.draws.spin_rest(panel.id, NOW)
    assert [(r.task_id, r.winner_id) for r in rest] == [("t2", "p2")]
    round_ = world.draws.commit(panel.id, NOW + dt.timedelta(minutes=1))
    assert round_.origin is MANUAL and round_.finished_at == NOW + dt.timedelta(minutes=1)
    assert world.history.rounds[round_.id] == round_ and world.events.drawn == [round_]
    assert world.draws.open_rounds(NOW) == ()


def test_commit_before_the_last_spin_is_rejected_and_keeps_the_round_open():
    world = World()
    panel = world.draws.begin("s1", NOW)
    world.draws.spin(panel.id, NOW)
    with pytest.raises(DrawRejectedError):
        world.draws.commit(panel.id, NOW)
    assert world.draws.get(panel.id, NOW).draft.pending


def test_spin_after_the_last_task_is_rejected():
    world = World()
    panel = world.draws.begin("s1", NOW)
    world.draws.spin_rest(panel.id, NOW)
    with pytest.raises(DrawRejectedError):
        world.draws.spin(panel.id, NOW)


def test_cancel_discards_without_trace():
    world = World()
    panel = world.draws.begin("s1", NOW)
    world.draws.cancel(panel.id, NOW)
    assert world.history.rounds == {} and world.events.drawn == []
    with pytest.raises(NotFoundError):
        world.draws.get(panel.id, NOW)


def test_panel_round_expires_after_the_time_limit():
    world = World()
    panel = world.draws.begin("s1", NOW)
    assert world.draws.get(panel.id, panel.expires_at - dt.timedelta(seconds=1))
    with pytest.raises(NotFoundError):
        world.draws.spin(panel.id, panel.expires_at)
    with pytest.raises(NotFoundError):
        world.draws.commit(panel.id, panel.expires_at)


def test_begin_replaces_an_open_round_of_the_same_schedule():
    world = World()
    first = world.draws.begin("s1", NOW)
    second = world.draws.begin("s1", NOW)
    assert [p.id for p in world.draws.open_rounds(NOW)] == [second.id]
    with pytest.raises(NotFoundError):
        world.draws.get(first.id, NOW)


def test_automatic_round_does_not_wait_for_an_open_panel_round():
    world = World()
    panel = world.draws.begin("s1", NOW)
    world.draws.draw("s1", AUTO, NOW)
    with pytest.raises(NotFoundError):
        world.draws.get(panel.id, NOW)


def test_number_of_open_panel_rounds_is_limited():
    world = World()
    for number in range(MAX_OPEN_PANEL_ROUNDS):
        world.put_schedule(id=f"s{number + 2}", slug=f"plan{number}", name=f"Plan {number}")
        world.draws.begin(f"s{number + 2}", NOW)
    with pytest.raises(LimitReachedError):
        world.draws.begin("s1", NOW)
    assert len(world.draws.open_rounds(NOW)) == MAX_OPEN_PANEL_ROUNDS
    assert world.draws.open_rounds(NOW + dt.timedelta(hours=1)) == ()
