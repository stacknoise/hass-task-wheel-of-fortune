"""Kalendergrenzen der Perioden (Tag, Woche ab Montag, Monat) in der Zeitzone der Auslosung."""

from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime
from types import MappingProxyType

from ..enums import Period
from ..validation import ensure_aware

type PeriodStart = Callable[[date], date]

_PERIOD_STARTS: Mapping[Period, PeriodStart] = MappingProxyType(
    {
        Period.DAY: lambda day: day,
        Period.WEEK: lambda day: date.fromordinal(day.toordinal() - day.weekday()),
        Period.MONTH: lambda day: day.replace(day=1),
    }
)


def local_date(moment: datetime, reference: datetime) -> date:
    """Kalendertag von `moment` in der Zeitzone von `reference` (Sommerzeit-fest)."""
    ensure_aware("assigned", moment)
    return moment.astimezone(reference.tzinfo).date()


def period_start(period: Period, now: datetime) -> date:
    """Erster Kalendertag der Periode, in der `now` liegt."""
    ensure_aware("now", now)
    return _PERIOD_STARTS[period](now.date())


def count_since(start: date, assigned: Iterable[datetime], now: datetime) -> int:
    """Anzahl der Zuteilungen ab `start` (Kalendertag) bis `now`."""
    today = now.date()
    return sum(start <= local_date(moment, now) <= today for moment in assigned)
