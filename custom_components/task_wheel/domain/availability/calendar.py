"""Anwesenheit einer Person: Regeln kombiniert, Fensterabfrage und Vorschau."""

import datetime as dt
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from ...const.defaults import DEFAULT_PREVIEW_WEEKS
from ...const.keys import ERR_ORDER, ERR_RANGE
from ...const.limits import (
    AVAILABILITY_WINDOW_MAX_DAYS,
    PREVIEW_WEEKS_MAX,
    PREVIEW_WEEKS_MIN,
    WEEKDAY_COUNT,
)
from ..models import AbsenceConfig, Person
from ..validation import ensure, ensure_range
from .factory import AvailabilityRuleFactory
from .rule import AvailabilityRule

_DAY = dt.timedelta(days=1)
_FIELD_WINDOW = "window"
_FIELD_WEEKS = "weeks"


@dataclass(slots=True, frozen=True)
class DayPresence:
    """Anwesenheit an einem Kalendertag (Zeile der Vorschau)."""

    day: dt.date
    present: bool


@dataclass(slots=True, frozen=True)
class PersonAvailability:
    """Eine Person ist an einem Tag anwesend, wenn **keine** ihrer Regeln sie abwesend meldet."""

    rules: Sequence[AvailabilityRule]

    @classmethod
    def of(
        cls, person: Person, factory: AvailabilityRuleFactory | None = None
    ) -> "PersonAvailability":
        """Baut die Anwesenheit aus den Regeln der Person."""
        return cls.of_rules(person.absences, factory)

    @classmethod
    def of_rules(
        cls, absences: Sequence[AbsenceConfig], factory: AvailabilityRuleFactory | None = None
    ) -> "PersonAvailability":
        """Baut die Anwesenheit aus Abwesenheitsregeln, die noch zu keiner Person gehören."""
        return cls((factory or AvailabilityRuleFactory()).create_all(absences))

    def is_present(self, day: dt.date) -> bool:
        """Anwesend am Tag `day`."""
        return all(rule.is_present(day) for rule in self.rules)

    def days(self, start: dt.date, end: dt.date) -> Iterator[DayPresence]:
        """Liefert die Anwesenheit je Tag von `start` bis `end` (einschließlich).

        Raises:
            ValidationError: Das Fenster ist verkehrt herum oder länger als erlaubt.
        """
        ensure(start <= end, _FIELD_WINDOW, ERR_ORDER)
        ensure((end - start).days < AVAILABILITY_WINDOW_MAX_DAYS, _FIELD_WINDOW, ERR_RANGE)
        day = start
        while day <= end:
            yield DayPresence(day, self.is_present(day))
            day += _DAY

    def present_in_window(self, start: dt.date, end: dt.date) -> bool:
        """Anwesend an mindestens einem Tag im Fenster (Kandidatenregel, KONZEPT §5)."""
        return any(entry.present for entry in self.days(start, end))

    def present_day_count(self, start: dt.date, end: dt.date) -> int:
        """Anzahl anwesender Tage im Fenster (Grundlage der Kapazität, KONZEPT §5.3)."""
        return sum(entry.present for entry in self.days(start, end))

    def preview(
        self, start: dt.date, weeks: int = DEFAULT_PREVIEW_WEEKS
    ) -> tuple[DayPresence, ...]:
        """Vorschau für `weeks` volle Wochen ab `start` (Personen-Ansicht)."""
        ensure_range(_FIELD_WEEKS, weeks, PREVIEW_WEEKS_MIN, PREVIEW_WEEKS_MAX)
        end = start + dt.timedelta(days=weeks * WEEKDAY_COUNT - 1)
        return tuple(self.days(start, end))

    def week_preview(
        self, today: dt.date, weeks: int = DEFAULT_PREVIEW_WEEKS
    ) -> tuple[DayPresence, ...]:
        """Vorschau für `weeks` volle Wochen, beginnend am Montag der Woche von `today`."""
        return self.preview(today - dt.timedelta(days=today.weekday()), weeks)
