"""Frist am Zeitplan: wann die Zeit für die Aufgaben beginnt und wie lange sie läuft."""

import calendar
import datetime as dt
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ..const import defaults, limits
from ..const.keys import ERR_ORDER, ERR_RANGE
from .enums import DeadlineStart, DeadlineUnit
from .serialization import Model, enum_of, spec, to_int, to_time
from .types import Weekday
from .validation import ensure, ensure_aware, ensure_range

_FIELD_DURATION = "duration"
_HOURS_PER_DAY = limits.HOURS_PER_DAY
_WEEK_DAYS = limits.WEEKDAY_COUNT

# --- Rechnen mit Einheiten ----------------------------------------------------------------------


def _add_months(moment: dt.datetime, months: int) -> dt.datetime:
    """Addiert Kalendermonate; ein zu kurzer Zielmonat kürzt den Tag (31.1. + 1 Monat = 28.2.)."""
    year, month = divmod(
        moment.year * limits.MONTHS_PER_YEAR + moment.month - 1 + months, limits.MONTHS_PER_YEAR
    )
    last_day = calendar.monthrange(year, month + 1)[1]
    return moment.replace(year=year, month=month + 1, day=min(moment.day, last_day))


def _add_hours(moment: dt.datetime, hours: int) -> dt.datetime:
    """Addiert Stunden in echter Zeit (über eine Sommerzeitumstellung hinweg stimmt die Dauer)."""
    utc = moment.astimezone(dt.UTC) + dt.timedelta(hours=hours)
    return utc.astimezone(moment.tzinfo)


# Je Einheit: wie ein Zeitpunkt um `amount` Einheiten verschoben wird (Tage, Wochen und Monate
# in Kalenderzeit, damit die Uhrzeit über eine Sommerzeitumstellung gleich bleibt) und wie viele
# Tage die Einheit höchstens umfasst (für die Obergrenze des Fensters)
_SHIFT: Mapping[DeadlineUnit, Callable[[dt.datetime, int], dt.datetime]] = MappingProxyType(
    {
        DeadlineUnit.HOUR: _add_hours,
        DeadlineUnit.DAY: lambda moment, n: moment + dt.timedelta(days=n),
        DeadlineUnit.WEEK: lambda moment, n: moment + dt.timedelta(weeks=n),
        DeadlineUnit.MONTH: _add_months,
    }
)
_UNIT_MAX_DAYS: Mapping[DeadlineUnit, float] = MappingProxyType(
    {
        DeadlineUnit.HOUR: 1 / _HOURS_PER_DAY,
        DeadlineUnit.DAY: 1,
        DeadlineUnit.WEEK: _WEEK_DAYS,
        DeadlineUnit.MONTH: limits.DAYS_PER_MONTH_MAX,
    }
)


def shift(moment: dt.datetime, amount: int, unit: DeadlineUnit) -> dt.datetime:
    """Verschiebt den Zeitpunkt um `amount` Einheiten."""
    return _SHIFT[unit](moment, amount)


# --- Fenster ------------------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class DeadlineWindow:
    """Zeitraum, in dem die Aufgaben einer Auslosung gelten: ab `start` bis zur Frist `end`."""

    start: dt.datetime
    end: dt.datetime

    def __post_init__(self) -> None:
        """Prüft Zeitzonen und Reihenfolge (`end` nicht vor `start`)."""
        ensure_aware("start", self.start)
        ensure_aware("end", self.end)
        ensure(self.start <= self.end, "end", ERR_ORDER)

    @property
    def first_day(self) -> dt.date:
        """Erster Kalendertag des Fensters."""
        return self.start.date()

    @property
    def last_day(self) -> dt.date:
        """Letzter Kalendertag des Fensters (in der Zeitzone der Frist)."""
        return self.end.astimezone(self.start.tzinfo).date()

    @classmethod
    def after(cls, start: dt.datetime, amount: int, unit: DeadlineUnit) -> "DeadlineWindow":
        """Fenster ab `start`, `amount` Einheiten lang (Eingabe bei einer manuellen Auslosung).

        Raises:
            ValidationError: Die Dauer liegt außerhalb der Grenzen.
        """
        ensure_range(
            _FIELD_DURATION, amount, limits.DEADLINE_DURATION_MIN, limits.DEADLINE_AMOUNT_MAX
        )
        ensure(
            amount * _UNIT_MAX_DAYS[unit] <= limits.DEADLINE_MAX_DAYS, _FIELD_DURATION, ERR_RANGE
        )
        return cls(start, shift(start, amount, unit))


# --- Beginn -------------------------------------------------------------------------------------


def _at_time(day: dt.datetime, time: dt.time) -> dt.datetime:
    """Der Tag von `day` zur Uhrzeit `time` in derselben Zeitzone."""
    return dt.datetime.combine(day.date(), time, tzinfo=day.tzinfo)


def _next_day(deadline: "Deadline", draw_at: dt.datetime) -> dt.datetime:
    """Am Folgetag zur Uhrzeit."""
    return _at_time(draw_at + dt.timedelta(days=1), deadline.time)


def _next_weekday(deadline: "Deadline", draw_at: dt.datetime) -> dt.datetime:
    """Am nächsten gewählten Wochentag (frühestens morgen) zur Uhrzeit."""
    ahead = (deadline.weekday - draw_at.weekday()) % _WEEK_DAYS or _WEEK_DAYS
    return _at_time(draw_at + dt.timedelta(days=ahead), deadline.time)


# Strategie je Art des Beginns; jede liefert den Zeitpunkt, ab dem die Aufgaben gelten
_STARTS: Mapping[DeadlineStart, Callable[["Deadline", dt.datetime], dt.datetime]] = (
    MappingProxyType(
        {
            DeadlineStart.NOW: lambda _deadline, draw_at: draw_at,
            DeadlineStart.OFFSET: lambda deadline, draw_at: shift(
                draw_at, deadline.offset, deadline.offset_unit
            ),
            DeadlineStart.NEXT_DAY: _next_day,
            DeadlineStart.WEEKDAY: _next_weekday,
        }
    )
)


@dataclass(slots=True, frozen=True, kw_only=True)
class Deadline(Model):
    """Frist eines Zeitplans: Beginn (sofort, Versatz, Folgetag, Wochentag) und Dauer."""

    start: DeadlineStart = spec(enum_of(DeadlineStart), default=DeadlineStart.NOW)
    offset: int = spec(to_int, default=limits.DEADLINE_OFFSET_MIN)
    offset_unit: DeadlineUnit = spec(enum_of(DeadlineUnit), default=DeadlineUnit.HOUR)
    time: dt.time = spec(to_time, default=defaults.DEFAULT_DEADLINE_TIME)
    weekday: Weekday = spec(to_int, default=limits.WEEKDAY_MIN)
    duration: int = spec(to_int, default=defaults.DEFAULT_DEADLINE_DAYS)
    duration_unit: DeadlineUnit = spec(enum_of(DeadlineUnit), default=DeadlineUnit.DAY)

    def __post_init__(self) -> None:
        """Prüft Beträge, Wochentag und dass das ganze Fenster höchstens ein Jahr lang ist."""
        ensure_range("offset", self.offset, limits.DEADLINE_OFFSET_MIN, limits.DEADLINE_AMOUNT_MAX)
        ensure_range(
            _FIELD_DURATION,
            self.duration,
            limits.DEADLINE_DURATION_MIN,
            limits.DEADLINE_AMOUNT_MAX,
        )
        ensure_range("weekday", self.weekday, limits.WEEKDAY_MIN, limits.WEEKDAY_MAX)
        ensure(self.longest_days <= limits.DEADLINE_MAX_DAYS, _FIELD_DURATION, ERR_RANGE)

    @property
    def longest_days(self) -> float:
        """Obergrenze der Fensterlänge in Tagen (Versatz, Wartezeit bis zum Wochentag, Dauer)."""
        wait = {
            DeadlineStart.NOW: 0,
            DeadlineStart.OFFSET: self.offset * _UNIT_MAX_DAYS[self.offset_unit],
            DeadlineStart.NEXT_DAY: 1,
            DeadlineStart.WEEKDAY: _WEEK_DAYS,
        }[self.start]
        return wait + self.duration * _UNIT_MAX_DAYS[self.duration_unit]

    def window(self, draw_at: dt.datetime) -> DeadlineWindow:
        """Das Fenster für eine Auslosung zum Zeitpunkt `draw_at`."""
        start = _STARTS[self.start](self, draw_at)
        return DeadlineWindow(start, shift(start, self.duration, self.duration_unit))


DEFAULT_DEADLINE = Deadline()
