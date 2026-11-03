"""RoundDraft: schrittweise Ziehung, fortlaufender Kontext, Umwandlung in eine Runde."""

import datetime as dt
from itertools import count
from zoneinfo import ZoneInfo

import pytest

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
    assert (second.person_id, second.chance) == ("p2", 0.5)
    assert first.due_at == NOW + dt.timedelta(days=7)
    assert round_.started_at == NOW and round_.finished_at == NOW


def test_task_without_candidates_gets_no_assignment():
    absent = WeeklyDaysAbsence(weekdays=frozenset(range(7)))
    persons = [make_person("p1", absences=(absent,)), make_person("p2", absences=(absent,))]
    round_ = draft(tasks_ab(), persons).spin_rest(engine(0.1)).to_round("r1", ids(), NOW)
    assert round_.assignments == ()


def test_due_date_keeps_local_wall_clock_across_dst_change():
    berlin = ZoneInfo("Europe/Berlin")
    start = dt.datetime(2026, 10, 20, 10, tzinfo=berlin)
    context = make_context([make_person("p1")], now=start)
    one = RoundDraft("s1", RoundOrigin.AUTO, start, context, (task(id="t1", due_days=7),))
    assignment = one.spin_rest(engine(0.1)).to_round("r1", ids(), start).assignments[0]
    assert assignment.due_at == dt.datetime(2026, 10, 27, 10, tzinfo=berlin)
    assert assignment.due_at.utcoffset() == dt.timedelta(hours=1)
