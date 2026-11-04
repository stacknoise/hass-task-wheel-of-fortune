"""Regeln des echten Tauschs: Gegenzuteilung und Berechtigung in beiden Richtungen."""

import datetime as dt

import pytest

from custom_components.task_wheel.const import keys
from custom_components.task_wheel.domain.enums import AssignmentStatus, Load
from custom_components.task_wheel.domain.errors import SwapRejectedError
from custom_components.task_wheel.domain.models import OnceAbsence, Person
from custom_components.task_wheel.domain.swap import (
    SwapContext,
    SwapSide,
    ensure_direction_possible,
    ensure_swap_possible,
    find_counterpart,
)

from . import factories as f

DAY = dt.timedelta(days=1)


def _person(person_id: str) -> Person:
    return f.person(id=person_id, absences=(), load=Load.FULL)


def _side(person_id: str, task_id: str, **task_overrides: object) -> SwapSide:
    return SwapSide(
        f.assignment(id=f"a-{person_id}", person_id=person_id, task_id=task_id),
        f.task(id=task_id, **task_overrides),
        _person(person_id),
    )


def _context(**overrides: object) -> SwapContext:
    values: dict[str, object] = {
        "assignment": f.assignment(),
        "task": f.task(),
        "receiver": _person("p2"),
        "now": f.NOW,
    }
    return SwapContext(**{**values, **overrides})


def test_valid_swap_passes() -> None:
    ensure_swap_possible(_side("p1", "t1"), _side("p2", "t2"), f.NOW)


@pytest.mark.parametrize(
    ("overrides", "key"),
    [
        ({"task": f.task(swap_allowed=False)}, keys.ERR_SWAP_DISABLED),
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
def test_direction_is_rejected_with_reason(overrides: dict[str, object], key: str) -> None:
    with pytest.raises(SwapRejectedError) as caught:
        ensure_direction_possible(_context(**overrides))
    assert caught.value.key == key


def test_absence_is_ignored_when_task_disregards_it() -> None:
    absent = f.person(
        id="p2", absences=(OnceAbsence(start=f.TODAY, end=f.TODAY + 30 * DAY),), load=Load.FULL
    )
    ensure_direction_possible(_context(receiver=absent, task=f.task(respect_absence=False)))


def test_absence_only_counts_inside_deadline_window() -> None:
    away_today = f.person(
        id="p2", absences=(OnceAbsence(start=f.TODAY, end=f.TODAY),), load=Load.FULL
    )
    ensure_direction_possible(_context(receiver=away_today))


def test_overdue_assignment_checks_only_today() -> None:
    overdue = f.assignment(due_at=f.NOW - 3 * DAY)
    ensure_direction_possible(_context(assignment=overdue))


def test_both_directions_are_checked_for_the_second_task() -> None:
    first = _side("p1", "t1")
    second = _side("p2", "t2", swap_allowed=False)
    with pytest.raises(SwapRejectedError) as caught:
        ensure_swap_possible(first, second, f.NOW)
    assert caught.value.key == keys.ERR_SWAP_DISABLED


def test_first_person_must_be_allowed_for_second_task() -> None:
    second = _side("p2", "t2", allowed=frozenset({"p2"}))
    with pytest.raises(SwapRejectedError) as caught:
        ensure_swap_possible(_side("p1", "t1"), second, f.NOW)
    assert caught.value.key == keys.ERR_SWAP_NOT_ALLOWED


def test_paused_first_person_cannot_take_the_second_task() -> None:
    first = SwapSide(
        f.assignment(person_id="p1"), f.task(), f.person(id="p1", absences=(), load=Load.PAUSED)
    )
    with pytest.raises(SwapRejectedError) as caught:
        ensure_swap_possible(first, _side("p2", "t2"), f.NOW)
    assert caught.value.key == keys.ERR_SWAP_PAUSED


def test_counterpart_is_the_open_assignment_of_the_target() -> None:
    mine = f.assignment(id="a1", person_id="p1")
    theirs = f.assignment(id="a2", person_id="p2")
    others = [mine, theirs, f.assignment(id="a3", person_id="p3")]
    assert find_counterpart(others, mine, "p2") == theirs


def test_counterpart_prefers_earliest_deadline() -> None:
    mine = f.assignment(id="a1", person_id="p1")
    late = f.assignment(id="a2", person_id="p2", due_at=f.NOW + 5 * DAY)
    early = f.assignment(id="a3", person_id="p2", due_at=f.NOW + DAY)
    assert find_counterpart([mine, late, early], mine, "p2") == early


@pytest.mark.parametrize(
    ("state", "done_at"),
    [
        (AssignmentStatus.ON_TIME, f.NOW),
        (AssignmentStatus.MISSED, None),
        (AssignmentStatus.SWAPPED, None),
    ],
)
def test_only_open_assignments_count_as_counterpart(
    state: AssignmentStatus, done_at: dt.datetime | None
) -> None:
    mine = f.assignment(id="a1", person_id="p1")
    done = f.assignment(id="a2", person_id="p2", status=state, done_at=done_at)
    with pytest.raises(SwapRejectedError) as caught:
        find_counterpart([mine, done], mine, "p2")
    assert caught.value.key == keys.ERR_SWAP_NO_OPEN_ASSIGNMENT


def test_target_without_assignment_in_round_is_rejected() -> None:
    mine = f.assignment(id="a1", person_id="p1")
    with pytest.raises(SwapRejectedError) as caught:
        find_counterpart([mine], mine, "p9")
    assert caught.value.key == keys.ERR_SWAP_NO_OPEN_ASSIGNMENT


def test_swap_with_oneself_is_rejected() -> None:
    mine = f.assignment(id="a1", person_id="p1")
    with pytest.raises(SwapRejectedError) as caught:
        find_counterpart([mine], mine, "p1")
    assert caught.value.key == keys.ERR_SWAP_SAME_PERSON
