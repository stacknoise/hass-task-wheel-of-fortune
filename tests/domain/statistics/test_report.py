"""Auswertung: KPIs, Punkte gegen fairen Anteil, Matrix, Hervorhebungen, Wochenquote."""

import datetime as dt

import pytest

from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.statistics.aggregate import StatRow
from custom_components.task_wheel.domain.statistics.report import (
    WeekRate,
    build_report,
    completion_rate,
    weekly_rates,
)

from .. import factories as f

MONTHS = ("2026-11",)


def _row(person: str, task: str, status: S, count: int, points: int) -> StatRow:
    return StatRow(person, task, status, count, points)


def _report(rows: list[StatRow], capacities: dict[str, float], **settings: object):
    return build_report(MONTHS, rows, capacities, f.settings(**settings), ())


def test_completion_rate_needs_closed_assignments() -> None:
    assert completion_rate(0, 0) is None
    assert completion_rate(3, 1) == 0.75


def test_kpis_count_every_status() -> None:
    rows = [
        _row("a", "t", S.ON_TIME, 4, 8),
        _row("a", "t", S.LATE, 1, 2),
        _row("b", "t", S.MISSED, 1, 2),
        _row("b", "u", S.OPEN, 2, 4),
        _row("b", "u", S.SWAPPED, 1, 2),
    ]
    kpis = _report(rows, {"a": 1.0, "b": 1.0}).kpis
    assert (kpis.assigned, kpis.on_time, kpis.late, kpis.missed, kpis.pending) == (9, 4, 1, 1, 3)
    assert kpis.completion_rate == pytest.approx(5 / 6)


def test_points_use_factors_and_fair_share_follows_capacity() -> None:
    rows = [
        _row("a", "t", S.ON_TIME, 3, 9),
        _row("b", "t", S.LATE, 1, 3),
        _row("b", "t", S.MISSED, 1, 3),
    ]
    report = _report(
        rows, {"a": 1.0, "b": 0.5, "c": 0.0}, late_points_factor=0.5, missed_points_factor=-1.0
    )
    points = {s.person_id: s.points for s in report.standings}
    assert points == {"a": 9, "b": 2 - 3, "c": 0}  # b: round(3*0.5)=2, verpasst -3
    fair = {s.person_id: s.fair_points for s in report.standings}
    assert fair["a"] == pytest.approx(8 * 2 / 3)
    assert fair["b"] == pytest.approx(8 / 3)
    assert fair["c"] == 0.0


def test_fairness_index_is_one_when_exactly_fair_and_lower_otherwise() -> None:
    fair = _report(
        [_row("a", "t", S.ON_TIME, 1, 5), _row("b", "t", S.ON_TIME, 1, 5)], {"a": 1.0, "b": 1.0}
    )
    unfair = _report([_row("a", "t", S.ON_TIME, 1, 10)], {"a": 1.0, "b": 1.0})
    assert fair.fairness_index == 1.0
    assert unfair.fairness_index == pytest.approx(0.5)
    assert _report([], {"a": 1.0}).fairness_index == 1.0


def test_matrix_counts_assignments_per_task_and_person() -> None:
    rows = [
        _row("a", "t", S.ON_TIME, 2, 4),
        _row("a", "t", S.OPEN, 1, 2),
        _row("b", "u", S.LATE, 1, 1),
    ]
    assert _report(rows, {}).matrix == {"t": {"a": 3}, "u": {"b": 1}}


def test_highlights_lucky_unlucky_and_reliable() -> None:
    rows = [
        _row("a", "t", S.ON_TIME, 5, 20),
        _row("b", "t", S.ON_TIME, 1, 2),
        _row("b", "t", S.LATE, 2, 4),
        _row("c", "t", S.ON_TIME, 2, 4),
    ]
    highlights = _report(rows, {"a": 1.0, "b": 1.0, "c": 1.0}).highlights
    assert (highlights.unlucky, highlights.lucky) == ("a", "c")
    assert highlights.reliable is not None
    assert (highlights.reliable.person_id, highlights.reliable.on_time_rate) == ("a", 1.0)


def test_highlights_stay_empty_without_comparison_or_sample() -> None:
    single = _report([_row("a", "t", S.ON_TIME, 2, 4)], {"a": 1.0}).highlights
    assert (single.lucky, single.unlucky, single.reliable) == (None, None, None)
    even = _report(
        [_row("a", "t", S.ON_TIME, 1, 4), _row("b", "t", S.ON_TIME, 1, 4)], {"a": 1.0, "b": 1.0}
    )
    assert (even.highlights.lucky, even.highlights.unlucky) == (None, None)


def test_weekly_rates_bucket_rounds_by_week_start() -> None:
    monday = dt.date(2026, 11, 2)
    this_week = f.finished_round()  # NOW = Dienstag 2026-11-03: erledigt (spät), getauscht, offen
    last_week = f.finished_round(
        id="r0", started_at=f.NOW - dt.timedelta(days=7), finished_at=None, assignments=()
    )
    outside = f.finished_round(
        id="r9", started_at=f.NOW - dt.timedelta(days=30), finished_at=None, assignments=()
    )
    starts = (monday - dt.timedelta(days=7), monday)
    weeks = weekly_rates([this_week, last_week, outside], starts)
    assert weeks == (WeekRate(starts[0], 0, 0), WeekRate(monday, 1, 0))
    assert weeks[0].rate is None
    assert weeks[1].rate == 1.0
