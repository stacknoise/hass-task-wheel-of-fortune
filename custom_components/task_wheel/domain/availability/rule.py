"""Schnittstelle der Anwesenheitsregeln (Strategy)."""

import datetime as dt
from typing import Protocol


class AvailabilityRule(Protocol):
    """Beantwortet für einen Kalendertag, ob eine Person laut dieser Regel anwesend ist."""

    def is_present(self, day: dt.date) -> bool:
        """Liefert `True`, wenn die Person an `day` anwesend ist."""
        ...
