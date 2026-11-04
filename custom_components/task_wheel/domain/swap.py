"""Regeln für den Tausch mit Joker (KONZEPT §5.4): Berechtigung der neuen Person und Jokerzähler."""

import datetime as dt
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final

from ..const.keys import (
    ERR_NO_JOKERS,
    ERR_SWAP_ABSENT,
    ERR_SWAP_DISABLED,
    ERR_SWAP_LOAD,
    ERR_SWAP_NOT_ALLOWED,
    ERR_SWAP_NOT_IN_ROUND,
    ERR_SWAP_PAUSED,
    ERR_SWAP_SAME_PERSON,
)
from .availability.calendar import PersonAvailability
from .enums import Load, Period
from .errors import SwapRejectedError
from .models import Assignment, Person, Settings, Task
from .rules.periods import local_date, period_start


@dataclass(slots=True, frozen=True)
class SwapContext:
    """Alles, was die Prüfregeln über einen geplanten Tausch wissen müssen."""

    assignment: Assignment
    task: Task
    receiver: Person
    jokers_left: int
    now: dt.datetime
    #: Personen, die in derselben Auslosung eine Zuteilung haben (Tausch nur untereinander).
    round_persons: frozenset[str]


def _present_until_due(context: SwapContext) -> bool:
    """Die neue Person ist (falls die Aufgabe Abwesenheit beachtet) im Fristfenster anwesend."""
    if not context.task.respect_absence:
        return True
    today = context.now.date()
    due = max(today, local_date(context.assignment.due_at, context.now))
    return PersonAvailability.of(context.receiver).present_in_window(today, due)


# Reihenfolge = Reihenfolge der Prüfung; die erste verletzte Regel nennt den Grund.
_CHECKS: Final[tuple[tuple[Callable[[SwapContext], bool], str], ...]] = (
    (lambda c: c.task.swap_allowed, ERR_SWAP_DISABLED),
    (lambda c: c.receiver.id != c.assignment.person_id, ERR_SWAP_SAME_PERSON),
    (lambda c: c.receiver.id in c.round_persons, ERR_SWAP_NOT_IN_ROUND),
    (lambda c: c.jokers_left > 0, ERR_NO_JOKERS),
    (lambda c: c.task.allows(c.receiver.id), ERR_SWAP_NOT_ALLOWED),
    (lambda c: c.receiver.load is not Load.PAUSED, ERR_SWAP_PAUSED),
    (lambda c: c.task.accepts_load(c.receiver.load), ERR_SWAP_LOAD),
    (_present_until_due, ERR_SWAP_ABSENT),
)


def ensure_swap_possible(context: SwapContext) -> None:
    """Prüft alle Regeln.

    Raises:
        SwapRejectedError: Mindestens eine Regel ist verletzt (Schlüssel nennt die erste).
    """
    for check, key in _CHECKS:
        if not check(context):
            raise SwapRejectedError(key)


def jokers_used_by_person(assignments: Iterable[Assignment], now: dt.datetime) -> Counter[str]:
    """Eingesetzte Joker je Person im Kalendermonat von `now` (ein Durchlauf für alle Personen)."""
    start = period_start(Period.MONTH, now)
    return Counter(
        item.swap.from_person_id
        for item in assignments
        if item.swap is not None and start <= local_date(item.swap.at, now) <= now.date()
    )


def jokers_left(settings: Settings, used: int) -> int:
    """Verbleibende Joker im Monat (nie negativ; der Zähler beginnt jeden Monat bei null)."""
    return max(0, settings.jokers_per_month - used)
