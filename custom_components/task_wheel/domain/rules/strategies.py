"""Strategien der Häufigkeitsregeln: jede Art ist eine Klasse mit derselben Schnittstelle."""

from collections.abc import Iterable
from datetime import datetime

from ..models import Interval, MaxPerPeriod
from ..validation import ensure_aware
from .periods import count_since, local_date, window_start


class EveryRoundRule:
    """Die Aufgabe ist in jeder Runde fällig."""

    def is_due(self, assigned: Iterable[datetime], now: datetime) -> bool:  # noqa: ARG002
        """Immer fällig."""
        ensure_aware("now", now)
        return True


class MaxPerPeriodRule:
    """Höchstens `count` Zuteilungen im Fenster aus `every` Tagen, Wochen oder Monaten."""

    def __init__(self, config: MaxPerPeriod) -> None:
        """Merkt sich Anzahl, Periode und Fensterlänge."""
        self._config = config

    def is_due(self, assigned: Iterable[datetime], now: datetime) -> bool:
        """Fällig, solange die Zuteilungen im Fenster (laufende plus vorherige Perioden) < Limit."""
        start = window_start(self._config.period, self._config.every, now)
        return count_since(start, assigned, now) < self._config.count


class IntervalRule:
    """Frühestens nach `days - tolerance` Kalendertagen seit der letzten Zuteilung."""

    def __init__(self, config: Interval) -> None:
        """Merkt sich den Mindestabstand abzüglich Toleranz."""
        self._min_days = config.days - config.tolerance

    def is_due(self, assigned: Iterable[datetime], now: datetime) -> bool:
        """Fällig ohne frühere Zuteilung oder bei ausreichendem Abstand (Kalendertage)."""
        ensure_aware("now", now)
        last = max(assigned, default=None)
        return last is None or (now.date() - local_date(last, now)).days >= self._min_days
