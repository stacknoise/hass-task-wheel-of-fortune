"""Perioden, Fälligkeit und Vorschau eines Zeitplans (reine Funktionen)."""

import datetime as dt
from dataclasses import replace

from custom_components.task_wheel.domain.enums import IntervalUnit, RoundOrigin
from custom_components.task_wheel.domain.models import Interval, Round
from custom_components.task_wheel.domain.plan.due import rank_tasks, timing_of
from custom_components.task_wheel.domain.plan.preview import (
    ISSUE_GAPS,
    ISSUE_INTERVAL_TOO_LONG,
    ISSUE_NO_PERSON,
    ISSUE_NO_TASKS,
    ISSUE_OVERLOAD,
    evaluate_plan,
)
from custom_components.task_wheel.domain.plan.window import (
    effective_window,
    grid_period,
    newest_period,
    next_open_period,
    next_period_start,
    period_index_at,
    period_start,
    period_window,
)

from .. import factories as f
from ..draw.helpers import FixedRandom

HOUR = dt.timedelta(hours=1)
SIX = Interval(unit=IntervalUnit.HOUR, every=6)


def _plan(**overrides: object):
    return f.schedule(start=f.NOW, interval=SIX, run_days=2, **overrides)


def test_periods_follow_the_grid_from_the_start() -> None:
    schedule = _plan()
    assert period_start(schedule, 2) == f.NOW + 12 * HOUR
    assert period_window(schedule, 1).start == f.NOW + 6 * HOUR
    assert next_period_start(schedule, f.NOW + HOUR) == f.NOW + 6 * HOUR
    assert next_period_start(schedule, f.NOW - HOUR) == f.NOW


def test_period_index_at_handles_edges_and_the_time_before_the_start() -> None:
    schedule = _plan()
    assert period_index_at(schedule, f.NOW - HOUR) is None
    assert period_index_at(schedule, f.NOW) == 0
    assert period_index_at(schedule, f.NOW + 6 * HOUR) == 1
    assert period_index_at(schedule, f.NOW + 6 * HOUR - dt.timedelta(seconds=1)) == 0


def test_a_late_draw_starts_now_but_keeps_the_length() -> None:
    schedule = _plan()
    window = effective_window(schedule, 1, f.NOW + 24 * HOUR)
    assert window.start == f.NOW + 24 * HOUR
    assert window.end == f.NOW + 30 * HOUR
    assert effective_window(schedule, 1, f.NOW).start == f.NOW + 6 * HOUR


def test_a_draw_ahead_of_its_period_still_starts_now() -> None:
    schedule = _plan()
    window = effective_window(schedule, 5, f.NOW + HOUR)
    assert (window.start, window.end) == (f.NOW + HOUR, f.NOW + 7 * HOUR)


def test_rounds_from_before_the_start_belong_to_the_first_period() -> None:
    schedule = _plan()
    old = Round(
        id="r1",
        schedule_id="s1",
        origin=RoundOrigin.MANUAL,
        started_at=f.NOW - HOUR,
        period_index=8,
    )
    assert grid_period(schedule, old) == 0
    assert grid_period(schedule, replace(old, started_at=f.NOW)) == 8


def test_open_and_newest_period_come_from_the_rounds_of_one_schedule() -> None:
    assert next_open_period([], "s1") == 0
    assert newest_period([], "s1") is None
    rounds = [f.finished_round(id="r1", schedule_id="s1", period_index=2)]
    assert next_open_period(rounds, "s1") == 3
    assert newest_period(rounds, "s1") == 2
    assert next_open_period(rounds, "other") == 0


def test_timing_spreads_the_draws_of_a_run_evenly() -> None:
    schedule = _plan(entries=f.entries("t1", every_draw=False, min_count=2))
    (entry,) = schedule.entries
    assert schedule.draws_per_run == 8
    first = timing_of(schedule, entry, {}, 3)
    assert first.elapsed is None and first.arrears == 0 and first.progress is None
    later = timing_of(schedule, entry, {"t1": 0}, 6)
    assert (later.spacing, later.elapsed, later.minimum_gap) == (4.0, 6, 4)
    assert later.arrears == 2 and later.progress == 1.5


def test_ranking_puts_every_draw_first_then_due_then_spare() -> None:
    schedule = _plan(
        entries=(
            *f.entries("t1"),
            *f.entries("t2", every_draw=False, min_count=2),
            *f.entries("t3", every_draw=False, min_count=2),
        )
    )
    tasks = [f.task(id=i, name=i) for i in ("t1", "t2", "t3", "gone")]
    ranking = rank_tasks(schedule, tasks, {"t2": 0, "t3": 6}, 5, FixedRandom(0.5))
    assert [t.id for t in ranking.required] == ["t1"]
    assert [t.id for t in ranking.due] == ["t2"]
    assert [t.id for t in ranking.spare] == ["t3"]
    assert [t.id for t in ranking.priority] == ["t1", "t2"]


def test_without_history_chance_decides_whether_a_task_is_due() -> None:
    schedule = _plan(entries=f.entries("t1", every_draw=False, min_count=2))
    tasks = [f.task(id="t1")]
    assert rank_tasks(schedule, tasks, {}, 0, FixedRandom(0.1)).due
    assert not rank_tasks(schedule, tasks, {}, 0, FixedRandom(0.9)).due


def test_preview_places_tasks_evenly() -> None:
    entries = f.entries("t1", every_draw=False, min_count=2)
    preview = evaluate_plan(entries, 8, 6, {"t1": frozenset({"p1"})})
    (track,) = preview.tracks
    assert len(track.positions) == 2
    assert track.gap_min == track.gap_max == 4
    assert preview.planned == 2 and preview.capacity == 8
    assert {issue.code for issue in preview.issues} == {ISSUE_GAPS}


def test_preview_warns_about_overload() -> None:
    entries = f.entries("t1", "t2", "t3")
    reach = {i: frozenset({"p1"}) for i in ("t1", "t2", "t3")}
    codes = {issue.code for issue in evaluate_plan(entries, 4, 6, reach).issues}
    assert ISSUE_OVERLOAD in codes


def test_preview_blocks_plans_that_cannot_work() -> None:
    reach = {"t1": frozenset({"p1"})}
    assert {i.code for i in evaluate_plan((), 4, 6, reach).issues} == {ISSUE_NO_TASKS}
    entries = f.entries("t1")
    assert {i.code for i in evaluate_plan(entries, 0, 6, reach).issues} == {ISSUE_INTERVAL_TOO_LONG}
    assert ISSUE_NO_PERSON in {i.code for i in evaluate_plan(entries, 4, 6, {}).issues}
