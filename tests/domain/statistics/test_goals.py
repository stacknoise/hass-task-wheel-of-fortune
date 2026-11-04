"""Erreichungsgrad der Zeitpläne: Soll aus der Häufigkeitsregel gegen Erledigtes im Fenster."""

import datetime as dt

from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.enums import Period
from custom_components.task_wheel.domain.models import EveryRound, Interval, MaxPerPeriod
from custom_components.task_wheel.domain.statistics.goals import build_goals

from .. import factories as f

NOW = f.NOW


def placed(task_id: str, days_ago: int, status: S = S.ON_TIME):
    when = NOW - dt.timedelta(days=days_ago)
    done = when if status in (S.ON_TIME, S.LATE) else None
    return f.assignment(task_id=task_id, status=status, done_at=done), when


def tasks(**frequencies):
    return {
        ident: f.task(id=ident, name=ident, frequency=frequency)
        for ident, frequency in frequencies.items()
    }


def test_goal_counts_done_in_the_window_against_the_target():
    monthly = MaxPerPeriod(count=5, period=Period.MONTH, every=2)
    found = build_goals(
        [f.schedule(task_ids=("a",))],
        tasks(a=monthly),
        [placed("a", 1), placed("a", 2, S.LATE), placed("a", 3, S.OPEN), placed("a", 400)],
        NOW,
    )
    (goal,) = found
    (task,) = goal.tasks
    assert (task.target, task.assigned, task.done) == (5, 3, 2)
    assert (goal.target, goal.reached, goal.rate) == (5, 2, 0.4)


def test_reached_is_capped_at_the_target():
    weekly = MaxPerPeriod(count=1, period=Period.DAY, every=3)
    (goal,) = build_goals(
        [f.schedule(task_ids=("a",))], tasks(a=weekly), [placed("a", 0), placed("a", 1)], NOW
    )
    assert (goal.reached, goal.rate) == (1, 1.0)


def test_schedules_without_target_or_archived_are_left_out():
    found = build_goals(
        [
            f.schedule(id="s1", task_ids=("a", "b")),
            f.schedule(id="s2", task_ids=("c",), archived=True, enabled=False),
        ],
        tasks(a=EveryRound(), b=Interval(days=3), c=MaxPerPeriod(count=1, period=Period.WEEK)),
        [],
        NOW,
    )
    assert found == ()


def test_unknown_tasks_are_skipped():
    found = build_goals(
        [f.schedule(task_ids=("gone", "a"))],
        tasks(a=MaxPerPeriod(count=2, period=Period.WEEK)),
        [],
        NOW,
    )
    assert [task.task_id for task in found[0].tasks] == ["a"]
