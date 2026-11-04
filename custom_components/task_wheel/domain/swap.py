"""Regeln für den echten Tausch zweier Zuteilungen einer Runde (KONZEPT §5.4)."""

import datetime as dt
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final

from ..const.keys import (
    ERR_SWAP_ABSENT,
    ERR_SWAP_DISABLED,
    ERR_SWAP_LOAD,
    ERR_SWAP_NO_OPEN_ASSIGNMENT,
    ERR_SWAP_NOT_ALLOWED,
    ERR_SWAP_PAUSED,
    ERR_SWAP_SAME_PERSON,
)
from .availability.calendar import PersonAvailability
from .enums import AssignmentStatus, Load
from .errors import SwapRejectedError
from .models import Assignment, Person, Task
from .rules.periods import local_date
from .types import PersonId


@dataclass(slots=True, frozen=True)
class SwapSide:
    """Eine Seite des Tausches: die Zuteilung samt Aufgabe und der Person, die sie heute hat."""

    assignment: Assignment
    task: Task
    person: Person


@dataclass(slots=True, frozen=True)
class SwapContext:
    """Eine Richtung des Tausches: `assignment` geht an `receiver`."""

    assignment: Assignment
    task: Task
    receiver: Person
    now: dt.datetime


def find_counterpart(
    assignments: Iterable[Assignment], assignment: Assignment, to_person_id: PersonId
) -> Assignment:
    """Die Gegenzuteilung: offene Zuteilung von `to_person_id` in der Runde (früheste Frist).

    Raises:
        SwapRejectedError: Es ist dieselbe Person oder sie hat keine offene Zuteilung.
    """
    if to_person_id == assignment.person_id:
        raise SwapRejectedError(ERR_SWAP_SAME_PERSON)
    candidates = [
        item
        for item in assignments
        if item.person_id == to_person_id and item.status is AssignmentStatus.OPEN
    ]
    if not candidates:
        raise SwapRejectedError(ERR_SWAP_NO_OPEN_ASSIGNMENT)
    return min(candidates, key=lambda item: item.due_at)


def _present_until_due(context: SwapContext) -> bool:
    """Die neue Person ist (falls die Aufgabe Abwesenheit beachtet) im Fristfenster anwesend."""
    if not context.task.respect_absence:
        return True
    today = context.now.date()
    starts_at = context.assignment.starts_at
    begin = today if starts_at is None else max(today, local_date(starts_at, context.now))
    due = max(begin, local_date(context.assignment.due_at, context.now))
    return PersonAvailability.of(context.receiver).present_in_window(begin, due)


# Reihenfolge = Reihenfolge der Prüfung; die erste verletzte Regel nennt den Grund.
_CHECKS: Final[tuple[tuple[Callable[[SwapContext], bool], str], ...]] = (
    (lambda c: c.task.swap_allowed, ERR_SWAP_DISABLED),
    (lambda c: c.task.allows(c.receiver.id), ERR_SWAP_NOT_ALLOWED),
    (lambda c: c.receiver.load is not Load.PAUSED, ERR_SWAP_PAUSED),
    (lambda c: c.task.accepts_load(c.receiver.load), ERR_SWAP_LOAD),
    (_present_until_due, ERR_SWAP_ABSENT),
)


def ensure_direction_possible(context: SwapContext) -> None:
    """Prüft alle Regeln für eine Richtung.

    Raises:
        SwapRejectedError: Mindestens eine Regel ist verletzt (Schlüssel nennt die erste).
    """
    for check, key in _CHECKS:
        if not check(context):
            raise SwapRejectedError(key)


def ensure_swap_possible(first: SwapSide, second: SwapSide, now: dt.datetime) -> None:
    """Prüft beide Richtungen: jede Person muss die neue Aufgabe annehmen dürfen.

    Raises:
        SwapRejectedError: Eine Regel ist in einer der beiden Richtungen verletzt.
    """
    for giver, taker in ((first, second), (second, first)):
        ensure_direction_possible(SwapContext(giver.assignment, giver.task, taker.person, now))
