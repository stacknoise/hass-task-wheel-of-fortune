"""Konkrete Anwesenheitsregeln, je eine Klasse pro Art von `AbsenceConfig`."""

import datetime as dt
from dataclasses import dataclass

from ...const.limits import WEEKDAY_COUNT
from ..models import OnceAbsence, RecurringAbsence, WeeklyDaysAbsence, WeekRhythmAbsence


@dataclass(slots=True, frozen=True)
class OnceRule:
    """Abwesend von `start` bis `end` (einschließlich), sonst anwesend."""

    config: OnceAbsence

    def is_present(self, day: dt.date) -> bool:
        """Anwesend, wenn `day` außerhalb des Zeitraums liegt."""
        return not self.config.start <= day <= self.config.end


@dataclass(slots=True, frozen=True)
class WeeklyDaysRule:
    """Abwesend an den konfigurierten Wochentagen."""

    config: WeeklyDaysAbsence

    def is_present(self, day: dt.date) -> bool:
        """Anwesend, wenn der Wochentag von `day` nicht zu den Abwesenheitstagen gehört."""
        return day.weekday() not in self.config.weekdays


@dataclass(slots=True, frozen=True)
class WeekRhythmRule:
    """Anwesend in bestimmten Wochen eines Zyklus; die Woche wechselt am `change_weekday`."""

    config: WeekRhythmAbsence

    def week_index(self, day: dt.date) -> int:
        """Liefert die Position der Woche von `day` im Zyklus (0 ist die Woche des Ankers).

        Eine Woche beginnt am Wechseltag. Die Rechnung nutzt Fußboden-Division und Modulo
        und ist daher auch vor dem Ankerdatum und über Jahreswechsel korrekt.
        """
        offset = (self.config.anchor.weekday() - self.config.change_weekday) % WEEKDAY_COUNT
        week_start = self.config.anchor - dt.timedelta(days=offset)
        return ((day - week_start).days // WEEKDAY_COUNT) % self.config.cycle_weeks

    def is_present(self, day: dt.date) -> bool:
        """Anwesend, wenn die Woche von `day` zu den Anwesenheitswochen gehört."""
        return self.week_index(day) in self.config.present_weeks


@dataclass(slots=True, frozen=True)
class RecurringRule:
    """Abwesend an den Wochentagen jeder n-ten Woche zwischen `start` und `end`."""

    config: RecurringAbsence

    def is_present(self, day: dt.date) -> bool:
        """Anwesend, wenn `day` nicht auf einen Abwesenheitstag im Zeitraum und Rhythmus fällt."""
        config = self.config
        if day < config.start or (config.end is not None and day > config.end):
            return True
        if day.weekday() not in config.weekdays:
            return True
        weeks_since_start = (_monday(day) - _monday(config.start)).days // WEEKDAY_COUNT
        return weeks_since_start % config.interval_weeks != 0


def _monday(day: dt.date) -> dt.date:
    """Montag der Woche von `day`."""
    return day - dt.timedelta(days=day.weekday())
