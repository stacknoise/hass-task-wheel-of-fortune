"""Berechtigung der neuen Person und Jokerzähler."""

import datetime as dt

import pytest

from custom_components.task_wheel.const import keys
from custom_components.task_wheel.domain import status
from custom_components.task_wheel.domain.enums import Load
from custom_components.task_wheel.domain.errors import SwapRejectedError
from custom_components.task_wheel.domain.models import Assignment, OnceAbsence, Swap
from custom_components.task_wheel.domain.swap import (
    SwapContext,
    ensure_swap_possible,
    jokers_left,
    jokers_used_by_person,
)

from . import factories as f

DAY = dt.timedelta(days=1)


def _context(**overrides: object) -> SwapContext:
    values: dict[str, object] = {
        "assignment": f.assignment(),
        "task": f.task(),
        "receiver": f.person(id="p2", slug="ben", name="Ben", absences=(), load=Load.FULL),
        "jokers_left": 1,
        "now": f.NOW,
        "round_persons": frozenset({"p1", "p2"}),
    }
    return SwapContext(**{**values, **overrides})


def test_valid_swap_passes() -> None:
    ensure_swap_possible(_context())


@pytest.mark.parametrize(
    ("overrides", "key"),
    [
        ({"task": f.task(swap_allowed=False)}, keys.ERR_SWAP_DISABLED),
        ({"receiver": f.person(id="p1", absences=())}, keys.ERR_SWAP_SAME_PERSON),
        ({"round_persons": frozenset({"p1"})}, keys.ERR_SWAP_NOT_IN_ROUND),
        ({"jokers_left": 0}, keys.ERR_NO_JOKERS),
        ({"task": f.task(allowed=frozenset({"p1"}))}, keys.ERR_SWAP_NOT_ALLOWED),
        (
            {"receiver": f.person(id="p2", absences=(), load=Load.PAUSED)},
            keys.ERR_SWAP_PAUSED,
        ),
        (
            {
                "task": f.task(min_load=Load.FULL),
                "receiver": f.person(id="p2", absences=(), load=Load.HALF),
            },
            keys.ERR_SWAP_LOAD,
        ),
        (
            {
                "receiver": f.person(
                    id="p2",
                    absences=(OnceAbsence(start=f.TODAY, end=f.TODAY + 30 * DAY),),
                    load=Load.FULL,
                )
            },
            keys.ERR_SWAP_ABSENT,
        ),
    ],
)
def test_swap_is_rejected_with_reason(overrides: dict[str, object], key: str) -> None:
    with pytest.raises(SwapRejectedError) as caught:
        ensure_swap_possible(_context(**overrides))
    assert caught.value.key == key


def test_absence_is_ignored_when_task_disregards_it() -> None:
    absent = f.person(
        id="p2", absences=(OnceAbsence(start=f.TODAY, end=f.TODAY + 30 * DAY),), load=Load.FULL
    )
    ensure_swap_possible(_context(receiver=absent, task=f.task(respect_absence=False)))


def test_absence_only_counts_inside_deadline_window() -> None:
    away_today = f.person(
        id="p2", absences=(OnceAbsence(start=f.TODAY, end=f.TODAY),), load=Load.FULL
    )
    ensure_swap_possible(_context(receiver=away_today))


def test_overdue_assignment_checks_only_today() -> None:
    overdue = f.assignment(due_at=f.NOW - 3 * DAY)
    ensure_swap_possible(_context(assignment=overdue))


def _swapped_at(moment: dt.datetime, giver: str = "p1") -> Assignment:
    return status.swap(f.assignment(person_id=giver), "p2", moment)


def test_jokers_are_counted_per_giver_and_calendar_month() -> None:
    month_start = dt.datetime(2026, 11, 1, 0, 0, tzinfo=f.TZ)
    assignments = [
        _swapped_at(month_start),
        _swapped_at(f.NOW),
        _swapped_at(f.NOW, giver="p3"),
        _swapped_at(month_start - dt.timedelta(seconds=1)),
        f.assignment(),
    ]
    assert jokers_used_by_person(assignments, f.NOW)["p1"] == 2
    assert jokers_used_by_person(assignments, f.NOW)["p3"] == 1


def test_jokers_reset_at_month_change() -> None:
    swapped = [_swapped_at(dt.datetime(2026, 11, 30, 23, 59, tzinfo=f.TZ))]
    december = dt.datetime(2026, 12, 1, 0, 1, tzinfo=f.TZ)
    assert jokers_used_by_person(swapped, f.NOW.replace(day=30))["p1"] == 1
    assert jokers_used_by_person(swapped, december)["p1"] == 0


def test_jokers_left_never_negative() -> None:
    settings = f.settings(jokers_per_month=2)
    assert jokers_left(settings, 1) == 1
    assert jokers_left(settings, 5) == 0


def test_jokers_used_by_person_counts_all_people_in_one_pass() -> None:
    now = f.NOW
    swapped = [
        f.assignment(id="a1", swap=Swap(from_person_id="p1", to_person_id="p2", at=now)),
        f.assignment(id="a2", swap=Swap(from_person_id="p1", to_person_id="p2", at=now)),
        f.assignment(id="a3", swap=Swap(from_person_id="p2", to_person_id="p1", at=now)),
        f.assignment(id="a4"),
    ]
    used = jokers_used_by_person(swapped, now)
    assert (used["p1"], used["p2"], used["p3"]) == (2, 1, 0)
