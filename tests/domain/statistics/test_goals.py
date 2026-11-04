"""Soll-Ist je Aufgabe: verloste Zuteilungen im Fenster der Regel gegen das Soll."""

import datetime as dt

from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.enums import Period
from custom_components.task_wheel.domain.models import EveryRound, Interval, MaxPerPeriod
from custom_components.task_wheel.domain.statistics.goals import build_goals, goals_start

from .. import factories as f

NOW = f.NOW  # siehe factories
S1 = [f.schedule(id="s1", task_ids=("a",))]


def placed(task_id: str, days_ago: int, status: S = S.ON_TIME, schedule_id: str = "s1"):
    when = NOW - dt.timedelta(days=days_ago)
    done = when if status in (S.ON_TIME, S.LATE) else None
    return f.assignment(task_id=task_id, status=status, done_at=done, schedule_id=schedule_id), when


def schedules(*pairs: tuple[str, tuple[str, ...]], **overrides):
    return [
        f.schedule(id=ident, name=ident, slug=ident, task_ids=ids, **overrides)
        for ident, ids in pairs
    ]


def tasks(**frequencies):
    return {
        ident: f.task(id=ident, name=ident, frequency=frequency)
        for ident, frequency in frequencies.items()
    }


def test_current_and_past_windows_count_drawn_and_done():
    rule = MaxPerPeriod(count=3, period=Period.MONTH, every=2)
    first = build_goals(S1, tasks(a=rule), [], NOW)[0].windows[0]
    drawn = [placed("a", d) for d in (0, 1, 5)] + [placed("a", 2, S.OPEN)]
    (goal,) = build_goals(S1, tasks(a=rule), drawn, NOW)
    current = goal.windows[0]
    assert (goal.target, goal.every, goal.period) == (3, 2, Period.MONTH)
    assert (current.start, current.assigned) == (first.start, 4)
    assert current.done == 3  # die offene zählt als verlost, nicht als erledigt
    assert len(goal.windows) == 4
    # frühere Fenster schließen lückenlos an
    assert goal.windows[1].end == goal.windows[0].start - dt.timedelta(days=1)
    assert goal.windows[1].assigned == 0


def test_past_window_counts_its_own_assignments():
    rule = MaxPerPeriod(count=1, period=Period.WEEK, every=1)
    (goal,) = build_goals(S1, tasks(a=rule), [placed("a", 8), placed("a", 9), placed("a", 0)], NOW)
    # 03.11. (diese Woche), 26.10. (Vorwoche), 25.10. (davor, Sonntag)
    assert [w.assigned for w in goal.windows[:3]] == [1, 1, 1]


def test_tasks_without_target_are_left_out():
    found = build_goals(
        schedules(("s1", ("a", "b", "c"))),
        tasks(a=EveryRound(), b=Interval(days=3), c=MaxPerPeriod(count=1, period=Period.WEEK)),
        [],
        NOW,
    )
    assert [goal.task_id for goal in found] == ["c"]


def test_goals_start_reaches_back_over_all_windows():
    rule = MaxPerPeriod(count=1, period=Period.MONTH, every=2)
    start = goals_start(tasks(a=rule).values(), NOW)
    assert start == build_goals(S1, tasks(a=rule), [], NOW)[0].windows[-1].start
    assert goals_start(tasks(a=EveryRound()).values(), NOW) == NOW.date()


def test_goals_are_counted_per_schedule_for_a_task_in_several_schedules():
    rule = MaxPerPeriod(count=2, period=Period.WEEK)
    drawn = [placed("a", 0), placed("a", 0, schedule_id="s2"), placed("a", 1, schedule_id="s2")]
    found = build_goals(schedules(("s1", ("a",)), ("s2", ("a",))), tasks(a=rule), drawn, NOW)
    assert [(g.schedule_id, g.task_id, g.windows[0].assigned) for g in found] == [
        ("s1", "a", 1),
        ("s2", "a", 2),
    ]


def test_archived_schedules_and_unknown_tasks_are_left_out():
    rule = MaxPerPeriod(count=1, period=Period.WEEK)
    plans = [
        f.schedule(id="s1", task_ids=("a", "gone")),
        f.schedule(id="s2", task_ids=("a",), enabled=False, archived=True),
    ]
    assert [(g.schedule_id, g.task_id) for g in build_goals(plans, tasks(a=rule), [], NOW)] == [
        ("s1", "a")
    ]
