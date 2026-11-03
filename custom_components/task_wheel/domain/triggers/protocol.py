"""Schnittstelle aller Auslöser-Strategien."""

from datetime import datetime
from typing import Protocol


class TriggerStrategy(Protocol):
    """Berechnet, wann ein Zeitplan als Nächstes ausgelöst wird."""

    def next_fire(self, after: datetime) -> datetime | None:
        """Liefert den ersten Zeitpunkt **nach** `after`, oder `None`, wenn nichts mehr ansteht.

        Die Zeitzone von `after` bestimmt Wochentag und Uhrzeit (in Home Assistant die lokale).
        """
        ...
