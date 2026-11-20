"""Kalendertage: Wochenbeginn und Tag eines Zeitpunkts in einer Zeitzone."""

from datetime import date, datetime

from .validation import ensure_aware


def week_start(day: date) -> date:
    """Montag der Woche von `day`."""
    return date.fromordinal(day.toordinal() - day.weekday())


def local_date(moment: datetime, reference: datetime) -> date:
    """Kalendertag von `moment` in der Zeitzone von `reference` (Sommerzeit-fest)."""
    ensure_aware("assigned", moment)
    return moment.astimezone(reference.tzinfo).date()
