"""Soll-Ist je Zeitplan und Aufgabe: verloste Zuteilungen je Lauf gegen die Mindesthäufigkeit."""

import datetime as dt

from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.models import Interval, Round
from custom_components.task_wheel.domain.statistics.goals import build_goals, schedule_goals

from .. import factories as f

DAY = dt.timedelta(days=1)
# 7 Tage Lauf, täglich: 7 Auslosungen je Lauf; „now“ liegt am Tag 9 (Periode 9, zweiter Lauf)
PLAN = f.schedule(
    entries=f.entries("a", every_draw=False, min_count=3) + f.entries("b"),
    run_days=7,
    interval=Interval(),
)
NOW = f.NOW + 9 * DAY


def drawn(period: int, task_id: str = "a", status: S = S.ON_TIME) -> Round:
    done = f.NOW if status in (S.ON_TIME, S.LATE) else None
    item = f.assignment(
        id=f"a{period}{task_id}",
        round_id=f"r{period}",
        task_id=task_id,
        status=status,
        done_at=done,
    )
    return f.finished_round(id=f"r{period}", period_index=period, assignments=(item,))


def test_target_per_run_and_current_run_first():
    goals = {g.task_id: g for g in schedule_goals(PLAN, [], NOW)}
    assert goals["a"].target == 3
    assert goals["b"].target == 7  # „jede Auslosung“: eine Zuteilung je Auslosung
    current, previous = goals["a"].windows[:2]
    assert (current.draws, current.elapsed) == (7, 3)  # Perioden 7, 8, 9 sind schon möglich
    assert previous.elapsed == 7
    assert previous.end == current.start - DAY


def test_counts_drawn_and_done_per_run():
    rounds = [drawn(p) for p in (1, 8)] + [drawn(9, status=S.OPEN), drawn(2, "b")]
    goal = next(g for g in schedule_goals(PLAN, rounds, NOW) if g.task_id == "a")
    current, previous = goal.windows[:2]
    assert (current.assigned, current.done) == (2, 1)  # die offene zählt als verlost
    assert (previous.assigned, previous.done) == (1, 1)


def test_only_rounds_of_the_schedule_count():
    other = f.finished_round(
        id="r1",
        schedule_id="s2",
        period_index=8,
        assignments=(f.assignment(task_id="a", schedule_id="s2"),),
    )
    goal = next(g for g in schedule_goals(PLAN, [other], NOW) if g.task_id == "a")
    assert goal.windows[0].assigned == 0


def test_no_goals_before_start_or_when_archived():
    assert schedule_goals(PLAN, [], f.NOW - DAY) == ()
    archived = f.schedule(enabled=False, archived=True)
    assert schedule_goals(archived, [], NOW) == ()


def test_windows_do_not_reach_before_the_first_run():
    goal = schedule_goals(PLAN, [], f.NOW + 2 * DAY)[0]
    assert len(goal.windows) == 1


def test_build_goals_covers_every_schedule():
    second = f.schedule(id="s2", slug="zwei", entries=f.entries("a"))
    found = build_goals([PLAN, second], [], NOW)
    assert {(g.schedule_id, g.task_id) for g in found} == {("s1", "a"), ("s1", "b"), ("s2", "a")}
