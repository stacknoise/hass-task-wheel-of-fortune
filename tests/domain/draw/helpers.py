"""Hilfen für Tests der Ziehung."""

import datetime as dt
from collections.abc import Iterable, Mapping

from custom_components.task_wheel.domain.availability.calendar import PersonAvailability
from custom_components.task_wheel.domain.draw.types import DrawContext
from custom_components.task_wheel.domain.models import Person

from ..factories import NOW

WINDOW = 30


class FixedRandom:
    """Liefert vorgegebene Zufallszahlen reihum."""

    def __init__(self, *values: float) -> None:
        self._values = values
        self._index = 0

    def random(self) -> float:
        value = self._values[self._index % len(self._values)]
        self._index += 1
        return value


def make_person(pid: str, **overrides: object) -> Person:
    values: dict[str, object] = {"id": pid, "name": pid, "slug": pid, "absences": ()}
    return Person(**{**values, **overrides})  # type: ignore[arg-type]


def make_context(
    persons: Iterable[Person],
    *,
    points: Mapping[str, float] | None = None,
    last_holders: Mapping[str, str] | None = None,
    round_holders: frozenset[str] = frozenset(),
    now: dt.datetime = NOW,
) -> DrawContext:
    people = {p.id: p for p in persons}
    return DrawContext(
        now=now,
        persons=people,
        availability={pid: PersonAvailability.of(p) for pid, p in people.items()},
        points=points or {},
        last_holders=last_holders or {},
        fairness_window_days=WINDOW,
        round_holders=round_holders,
    )
