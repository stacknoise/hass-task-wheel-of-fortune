"""Monatsaggregate: Schlüssel, inkrementelle Änderung, Neuberechnung, Lesen."""

import datetime as dt

import pytest

from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.errors import ValidationError
from custom_components.task_wheel.domain.statistics import aggregate as agg

from .. import factories as f


def test_month_keys_cross_year_boundary() -> None:
    today = dt.date(2026, 2, 15)
    assert agg.month_keys(today, 4) == ("2025-11", "2025-12", "2026-01", "2026-02")
    assert agg.month_starts(today, 1) == (dt.date(2026, 2, 1),)


def test_month_key_uses_timezone_of_moment() -> None:
    late = dt.datetime(2026, 11, 30, 23, 30, tzinfo=dt.timezone(dt.timedelta(hours=-5)))
    assert agg.month_key(late) == "2026-11"


def test_change_moves_contribution_between_statuses_and_people() -> None:
    before = f.assignment(points=3)
    after = f.assignment(points=3, status=S.SWAPPED, person_id="p2", swap=f.swap())
    start = agg.updated_month({}, "2026-11", [agg.AssignmentChange(None, before)])
    assert start == {"p1": {"t1": {"open": [1, 3]}}}
    month = agg.updated_month({"2026-11": start}, "2026-11", [agg.AssignmentChange(before, after)])
    assert month == {"p2": {"t1": {"swapped": [1, 3]}}}
    assert start == {"p1": {"t1": {"open": [1, 3]}}}  # Eingabe bleibt unverändert


def test_rows_read_only_requested_months() -> None:
    data = {
        "2026-10": {"p1": {"t1": {"on_time": [2, 6]}}},
        "2026-11": {"p2": {"t2": {"late": [1, 4]}}},
    }
    found = list(agg.rows(data, ["2026-11", "2026-09"]))
    assert found == [agg.StatRow("p2", "t2", S.LATE, 1, 4)]


@pytest.mark.parametrize(
    "broken",
    [
        {"2026-11": {"p1": {"t1": {"open": [1]}}}},
        {"2026-11": {"p1": {"t1": {"nope": [1, 2]}}}},
        {"2026-11": {"p1": {"t1": {"open": [1, "x"]}}}},
        {"2026-11": {"p1": 5}},
    ],
)
def test_corrupt_month_is_rejected(broken: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        list(agg.rows(broken, ["2026-11"]))


def test_recompute_matches_sum_of_rounds_and_drops_empty_rounds() -> None:
    first = f.finished_round()
    empty = f.finished_round(id="r2", assignments=())
    result = agg.recompute([first, empty])
    assert list(result) == ["2026-11"]
    assert result["2026-11"]["p1"]["t1"] == {"open": [1, 3], "late": [1, 3]}
    assert result["2026-11"]["p2"]["t1"] == {"swapped": [1, 3]}
