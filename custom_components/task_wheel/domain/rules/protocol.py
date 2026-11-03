"""Schnittstelle aller Häufigkeitsregeln."""

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol


class FrequencyRule(Protocol):
    """Entscheidet, ob eine Aufgabe in der laufenden Runde wieder fällig ist."""

    def is_due(self, assigned: Iterable[datetime], now: datetime) -> bool:
        """Prüft die Fälligkeit.

        `assigned` sind die bisherigen Zuteilungszeitpunkte der Aufgabe (zeitzonenbehaftet, in
        beliebiger Reihenfolge). `now` ist der Zeitpunkt der Auslosung; seine Zeitzone bestimmt
        die Kalendergrenzen von Tag, Woche und Monat.
        """
        ...
