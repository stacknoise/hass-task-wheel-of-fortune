"""Kalendergrenzen der Perioden (Tag, Woche ab Montag, Monat) in der Zeitzone der Auslosung."""

from collections.abc import Callable, Iterable, Mapping
from datetime import date, datetime
from types import MappingProxyType

from ...const.limits import MONTHS_PER_YEAR, WEEKDAY_COUNT
from ..enums import Period
from ..validation import ensure_aware

type PeriodStart = Callable[[date], date]


def week_start(day: date) -> date:
    """Montag der Woche von `day`."""
    return date.fromordinal(day.toordinal() - day.weekday())


_PERIOD_STARTS: Mapping[Period, PeriodStart] = MappingProxyType(
    {
        Period.DAY: lambda day: day,
        Period.WEEK: week_start,
        Period.MONTH: lambda day: day.replace(day=1),
    }
)


_PERIOD_DAYS: Mapping[Period, int] = MappingProxyType({Period.DAY: 1, Period.WEEK: WEEKDAY_COUNT})


def local_date(moment: datetime, reference: datetime) -> date:
    """Kalendertag von `moment` in der Zeitzone von `reference` (Sommerzeit-fest)."""
    ensure_aware("assigned", moment)
    return moment.astimezone(reference.tzinfo).date()


def period_start(period: Period, now: datetime) -> date:
    """Erster Kalendertag der Periode, in der `now` liegt."""
    ensure_aware("now", now)
    return _PERIOD_STARTS[period](now.date())


def shift_periods(period: Period, start: date, count: int) -> date:
    """Beginn der Periode, die `count` Perioden nach (oder bei negativem `count` vor) `start` liegt.

    `start` muss ein Periodenbeginn sein (Tag, Montag oder Monatserster).
    """
    if period is Period.MONTH:
        months = start.year * MONTHS_PER_YEAR + start.month - 1 + count
        return date(months // MONTHS_PER_YEAR, months % MONTHS_PER_YEAR + 1, 1)
    return date.fromordinal(start.toordinal() + count * _PERIOD_DAYS[period])


def window_start(period: Period, every: int, now: datetime) -> date:
    """Erster Kalendertag des Fensters aus `every` Perioden, das mit der laufenden endet."""
    return shift_periods(period, period_start(period, now), -(every - 1))


def count_since(start: date, assigned: Iterable[datetime], now: datetime) -> int:
    """Anzahl der Zuteilungen ab `start` (Kalendertag) bis `now`."""
    today = now.date()
    return sum(start <= local_date(moment, now) <= today for moment in assigned)
