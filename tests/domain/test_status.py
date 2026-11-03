"""Statusübergänge, Fristen und Punkte der Zuteilungen."""

import datetime as dt
from itertools import product

import pytest

from custom_components.task_wheel.const.keys import ERR_INVALID_TRANSITION
from custom_components.task_wheel.domain import status
from custom_components.task_wheel.domain.enums import AssignmentAction, AssignmentStatus
from custom_components.task_wheel.domain.errors import InvalidTransitionError

from . import factories as f

S = AssignmentStatus
A = AssignmentAction
HOUR = dt.timedelta(hours=1)
DUE = f.NOW + dt.timedelta(days=7)


@pytest.mark.parametrize(("current", "action"), list(product(S, A)))
def test_every_combination_is_allowed_or_rejected(current: S, action: A) -> None:
    if (current, action) in status.TRANSITIONS:
        assert status.next_status(current, action) is status.TRANSITIONS[(current, action)]
    else:
        with pytest.raises(InvalidTransitionError) as caught:
            status.next_status(current, action)
        assert caught.value.key == ERR_INVALID_TRANSITION
        assert caught.value.placeholders == {"status": current, "action": action}


@pytest.mark.parametrize("final", [S.ON_TIME, S.LATE, S.MISSED])
def test_final_states_have_no_exit(final: S) -> None:
    assert not [key for key in status.TRANSITIONS if key[0] is final]


def test_complete_on_time_until_due_inclusive() -> None:
    open_ = f.assignment(due_at=DUE)
    assert status.complete(open_, DUE).status is S.ON_TIME
    assert status.complete(open_, DUE).done_at == DUE


def test_complete_late_after_due() -> None:
    late = status.complete(f.assignment(due_at=DUE), DUE + HOUR)
    assert (late.status, late.done_at) == (S.LATE, DUE + HOUR)


def test_complete_swapped_assignment_keeps_swap_record() -> None:
    swapped = status.swap(f.assignment(), "p2", f.NOW)
    done = status.complete(swapped, f.NOW)
    assert (done.status, done.person_id, done.swap) == (S.ON_TIME, "p2", swapped.swap)


@pytest.mark.parametrize("final", [S.ON_TIME, S.LATE, S.MISSED])
def test_complete_final_assignment_is_rejected(final: S) -> None:
    done_at = None if final is S.MISSED else f.NOW
    with pytest.raises(InvalidTransitionError):
        status.complete(f.assignment(status=final, done_at=done_at), f.NOW)


def test_swap_moves_assignment_and_records_it() -> None:
    swapped = status.swap(f.assignment(), "p2", f.NOW)
    assert (swapped.status, swapped.person_id) == (S.SWAPPED, "p2")
    assert swapped.swap is not None
    assert (swapped.swap.from_person_id, swapped.swap.to_person_id) == ("p1", "p2")


def test_swapped_assignment_cannot_be_swapped_again() -> None:
    with pytest.raises(InvalidTransitionError):
        status.swap(status.swap(f.assignment(), "p2", f.NOW), "p1", f.NOW)


def test_miss_only_from_open_or_swapped() -> None:
    assert status.miss(f.assignment()).status is S.MISSED
    assert status.miss(status.swap(f.assignment(), "p2", f.NOW)).status is S.MISSED
    with pytest.raises(InvalidTransitionError):
        status.miss(f.assignment(status=S.ON_TIME, done_at=f.NOW))


def test_missable_only_after_grace_period() -> None:
    settings = f.settings(missed_grace_hours=24)
    open_ = f.assignment(due_at=DUE)
    deadline = status.missed_deadline(open_, settings)
    assert deadline == DUE + dt.timedelta(hours=24)
    assert not status.is_missable(open_, settings, deadline)
    assert status.is_missable(open_, settings, deadline + HOUR)


def test_done_assignment_is_never_missable() -> None:
    done = f.assignment(status=S.LATE, done_at=f.NOW)
    assert not status.is_missable(done, f.settings(), DUE + dt.timedelta(days=99))


@pytest.mark.parametrize(
    ("current", "expected"),
    [(S.OPEN, 0), (S.SWAPPED, 0), (S.ON_TIME, 3), (S.LATE, 2), (S.MISSED, -1)],
)
def test_points_follow_status_and_factors(current: S, expected: int) -> None:
    settings = f.settings(late_points_factor=0.75, missed_points_factor=-0.4)
    done_at = None if current in {S.OPEN, S.SWAPPED, S.MISSED} else f.NOW
    assignment = f.assignment(status=current, done_at=done_at, points=3)
    assert status.awarded_points(assignment, settings) == expected


def test_default_factors_give_full_late_and_no_missed_points() -> None:
    settings = f.settings()
    late = f.assignment(status=S.LATE, done_at=f.NOW, points=5)
    missed = f.assignment(status=S.MISSED, points=5)
    assert status.awarded_points(late, settings) == 5
    assert status.awarded_points(missed, settings) == 0
