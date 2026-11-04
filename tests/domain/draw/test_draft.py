"""RoundDraft: schrittweise Ziehung, fortlaufender Kontext, Umwandlung in eine Runde."""

import datetime as dt
from itertools import count

import pytest

from custom_components.task_wheel.domain.deadline import DeadlineWindow
from custom_components.task_wheel.domain.draw import draft as draft_module
from custom_components.task_wheel.domain.draw.candidates import CandidateSelector
from custom_components.task_wheel.domain.draw.draft import RoundDraft
from custom_components.task_wheel.domain.draw.engine import DrawEngine
from custom_components.task_wheel.domain.draw.weighting import UniformWeighting
from custom_components.task_wheel.domain.enums import RoundOrigin
from custom_components.task_wheel.domain.errors import DrawRejectedError
from custom_components.task_wheel.domain.models import WeeklyDaysAbsence

from ..factories import NOW, task
from .helpers import FixedRandom, make_context, make_person


def engine(*randoms: float) -> DrawEngine:
    return DrawEngine(UniformWeighting(), FixedRandom(*randoms))


def ids():
    numbers = count(1)
    return lambda: f"a{next(numbers)}"


def draft(tasks, persons=None, **kwargs) -> RoundDraft:
    people = persons or [make_person("p1"), make_person("p2")]
    return RoundDraft("s1", RoundOrigin.MANUAL, NOW, make_context(people, **kwargs), tuple(tasks))


def tasks_ab():
    return [task(id="t1", name="A", points=5), task(id="t2", name="B", points=2)]


def test_spin_draws_one_task_and_keeps_the_original():
    start = draft(tasks_ab())
    after = start.spin(engine(0.1))
    assert [t.id for t in after.pending] == ["t2"]
    assert after.results[0].winner_id == "p1"
    assert start.results == () and not start.complete


def test_points_and_last_holder_flow_into_the_next_spin():
    after = draft(tasks_ab()).spin(engine(0.1))
    assert after.context.points == {"p1": 5}
    assert after.context.last_holders == {"t1": "p1"}
    assert after.context.round_holders == {"p1"}


def test_spin_rest_draws_everything_that_is_left():
    done = draft(tasks_ab()).spin(engine(0.1)).spin_rest(engine(0.9))
    assert done.complete and [r.winner_id for r in done.results] == ["p1", "p2"]


def test_spin_after_the_end_is_rejected():
    done = draft(tasks_ab()).spin_rest(engine(0.1))
    with pytest.raises(DrawRejectedError):
        done.spin(engine(0.1))


def test_to_round_requires_a_complete_draft():
    with pytest.raises(DrawRejectedError):
        draft(tasks_ab()).spin(engine(0.1)).to_round("r1", ids(), NOW)


def test_to_round_creates_assignments_with_points_chance_and_due_date():
    round_ = draft(tasks_ab()).spin_rest(engine(0.1, 0.9)).to_round("r1", ids(), NOW)
    first, second = round_.assignments
    assert (round_.id, round_.schedule_id, round_.origin) == ("r1", "s1", RoundOrigin.MANUAL)
    assert (first.id, first.task_id, first.person_id, first.points) == ("a1", "t1", "p1", 5)
    assert (second.person_id, second.chance) == ("p2", 1.0)
    assert first.due_at == NOW + dt.timedelta(days=7)
    assert round_.started_at == NOW and round_.finished_at == NOW


def test_task_without_candidates_gets_no_assignment():
    absent = WeeklyDaysAbsence(weekdays=frozenset(range(7)))
    persons = [make_person("p1", absences=(absent,)), make_person("p2", absences=(absent,))]
    round_ = draft(tasks_ab(), persons).spin_rest(engine(0.1)).to_round("r1", ids(), NOW)
    assert round_.assignments == ()


def test_assignment_carries_the_window_of_the_round():
    window = DeadlineWindow(NOW + dt.timedelta(hours=18), NOW + dt.timedelta(hours=22))
    context = make_context([make_person("p1")], window=window)
    one = RoundDraft("s1", RoundOrigin.AUTO, NOW, context, (task(id="t1"),))
    assignment = one.spin_rest(engine(0.1)).to_round("r1", ids(), NOW).assignments[0]
    assert (assignment.starts_at, assignment.due_at) == (window.start, window.end)


def test_round_remembers_the_regular_run_it_replaces():
    context = make_context([make_person("p1")])
    run = NOW + dt.timedelta(days=3)
    one = RoundDraft("s1", RoundOrigin.MANUAL, NOW, context, (task(id="t1"),), replaces=run)
    assert one.spin_rest(engine(0.1)).to_round("r1", ids(), NOW).replaces == run


def test_capacity_and_reach_are_computed_once_and_shared_by_every_step(monkeypatch):
    calls = []
    real = draft_module.capacities
    monkeypatch.setattr(draft_module, "capacities", lambda ctx: calls.append(1) or real(ctx))
    start = draft(tasks_ab())
    done = start.spin(engine(0.1)).spin(engine(0.1))
    assert len(calls) == 1
    assert done.capacity is start.capacity
    assert done.reach is start.reach
    assert set(start.reach) == {"t2"}  # nur das, was als Rest einer Ziehung gebraucht wurde


def test_reach_is_not_recomputed_for_known_tasks():
    selector, ctx = CandidateSelector(), make_context([make_person("p1")])
    memo: dict[str, frozenset[str]] = {}
    assert selector._reach(memo, task(id="t1"), ctx) == frozenset({"p1"})
    memo["t1"] = frozenset({"cached"})
    assert selector._reach(memo, task(id="t1"), ctx) == frozenset({"cached"})
