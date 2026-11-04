"""Statistik-Service: Monatsaggregate fortschreiben und Auswertungen liefern (KONZEPT §6)."""

import datetime as dt
from collections.abc import Iterable
from dataclasses import replace

from ..const.defaults import DEFAULT_STATISTICS_MONTHS, DEFAULT_STATISTICS_WEEKS
from ..const.limits import (
    STATISTICS_MONTHS_MAX,
    STATISTICS_MONTHS_MIN,
    STATISTICS_WEEKS_MAX,
    STATISTICS_WEEKS_MIN,
    WEEKDAY_COUNT,
)
from ..domain.availability.calendar import PersonAvailability
from ..domain.enums import Period
from ..domain.models import Round
from ..domain.rules.periods import period_start
from ..domain.statistics import aggregate
from ..domain.statistics.aggregate import AssignmentChange
from ..domain.statistics.goals import TaskGoal, build_goals, goals_start
from ..domain.statistics.report import StatisticsReport, WeekRate, build_report, weekly_rates
from ..domain.types import PersonId
from ..domain.validation import ensure_range
from .protocols import ConfigRepository, HistoryRepository

_FIELD_MONTHS = "months"
_FIELD_WEEKS = "weeks"
_WEEK = dt.timedelta(days=WEEKDAY_COUNT)


class StatisticsService:
    """Implementiert `AssignmentRecorder`; die Auswertung liest nur die Aggregate."""

    def __init__(self, config: ConfigRepository, history: HistoryRepository) -> None:
        """Hält die Repositories."""
        self._config = config
        self._history = history

    def record(self, round_: Round, changes: Iterable[AssignmentChange]) -> None:
        """Schreibt die Änderungen in den Monat des Rundenbeginns fort (ein Speichervorgang)."""
        key = aggregate.month_key(round_.started_at)
        month = aggregate.updated_month(self._history.aggregates, key, changes)
        aggregates = dict(self._history.aggregates)
        if month:
            aggregates[key] = month
        else:
            aggregates.pop(key, None)
        self._history.set_aggregates(aggregates)

    def record_round(self, round_: Round) -> None:
        """Nimmt alle Zuteilungen einer neuen Runde auf."""
        self.record(round_, (AssignmentChange(None, item) for item in round_.assignments))

    def forget_round(self, round_: Round) -> None:
        """Nimmt alle Zuteilungen einer gelöschten Runde aus den Aggregaten (inkl. Punkte)."""
        self.record(round_, (AssignmentChange(item, None) for item in round_.assignments))

    def rebuild(self) -> None:
        """Berechnet alle Aggregate aus den Rohdaten neu (Reparatur, z. B. nach Datenfehlern)."""
        self._history.set_aggregates(aggregate.recompute(self._history.rounds.values()))

    def report(
        self,
        now: dt.datetime,
        months: int = DEFAULT_STATISTICS_MONTHS,
        weeks: int = DEFAULT_STATISTICS_WEEKS,
    ) -> StatisticsReport:
        """Auswertung der letzten `months` Kalendermonate (mit dem laufenden) und `weeks` Wochen.

        Raises:
            ValidationError: Anzahl der Monate oder Wochen außerhalb des erlaubten Bereichs.
        """
        ensure_range(_FIELD_MONTHS, months, STATISTICS_MONTHS_MIN, STATISTICS_MONTHS_MAX)
        ensure_range(_FIELD_WEEKS, weeks, STATISTICS_WEEKS_MIN, STATISTICS_WEEKS_MAX)
        today = now.date()
        keys = aggregate.month_keys(today, months)
        first_day = aggregate.month_starts(today, months)[0]
        report = build_report(
            keys,
            aggregate.rows(self._history.aggregates, keys),
            self._capacities(first_day, today),
            self._config.settings,
            self._weekly(now, weeks),
        )
        return replace(report, goals=self._goals(now))

    def _goals(self, now: dt.datetime) -> tuple[TaskGoal, ...]:
        """Soll-Ist je Aufgabe mit Häufigkeitsregel (aus den Rohdaten, nicht aus den Aggregaten)."""
        tasks = self._config.tasks
        since = dt.datetime.combine(
            goals_start(tasks.values(), now), dt.time.min, tzinfo=now.tzinfo
        )
        placed = (
            (item, round_.started_at)
            for round_ in self._history.rounds_since(since)
            for item in round_.assignments
        )
        return build_goals(tasks, placed, now)

    def _capacities(self, start: dt.date, end: dt.date) -> dict[PersonId, float]:
        """Kapazität = Belastbarkeit mal anwesende Tage im Zeitraum (fairer Anteil)."""
        return {
            person.id: person.load.factor
            * PersonAvailability.of(person).present_day_count(start, end)
            for person in self._config.persons.values()
        }

    def _weekly(self, now: dt.datetime, weeks: int) -> tuple[WeekRate, ...]:
        last = period_start(Period.WEEK, now)
        starts = tuple(last - _WEEK * back for back in reversed(range(weeks)))
        since = dt.datetime.combine(starts[0], dt.time.min, tzinfo=now.tzinfo)
        return weekly_rates(self._history.rounds_since(since), starts)
