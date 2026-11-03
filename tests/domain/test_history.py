"""Historienfilter: Runde, Aufgabe, Status, Person (auch abgebende), Zeitraum."""

import datetime as dt

import pytest

from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.errors import ValidationError
from custom_components.task_wheel.domain.history import HistoryFilter

from . import factories as f

DAY = dt.timedelta(days=1)


def _ids(flt: HistoryFilter) -> list[str]:
    return [item.id for item in flt.matching(f.finished_round())]


def test_empty_filter_matches_everything() -> None:
    assert _ids(HistoryFilter()) == ["a1", "a2", "a3"]


@pytest.mark.parametrize(
    ("flt", "expected"),
    [
        (HistoryFilter(status=S.LATE), ["a3"]),
        (HistoryFilter(task_id="t9"), []),
        (HistoryFilter(schedule_id="other"), []),
        (HistoryFilter(person_id="p2"), ["a2"]),  # a2: nun p2
        (HistoryFilter(person_id="p1"), ["a1", "a2", "a3"]),  # a2: von p1 abgegeben
    ],
)
def test_filters(flt: HistoryFilter, expected: list[str]) -> None:
    assert _ids(flt) == expected


def test_period_is_half_open_on_round_start() -> None:
    assert _ids(HistoryFilter(since=f.NOW, until=f.NOW + DAY)) == ["a1", "a2", "a3"]
    assert _ids(HistoryFilter(since=f.NOW + DAY)) == []
    assert _ids(HistoryFilter(until=f.NOW)) == []


def test_period_must_be_aware_and_ordered() -> None:
    with pytest.raises(ValidationError):
        HistoryFilter(since=dt.datetime(2026, 1, 1))
    with pytest.raises(ValidationError):
        HistoryFilter(until=dt.datetime(2026, 1, 1))
    with pytest.raises(ValidationError):
        HistoryFilter(since=f.NOW, until=f.NOW)
