"""Perioden im Raster eines Zeitplans: Zeitfenster einer Auslosung und ihre Nummer."""

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass

from ...const.keys import ERR_ORDER
from ...const.limits import HOURS_PER_DAY
from ..enums import INTERVAL_UNIT_HOURS, IntervalUnit
from ..models import Round, Schedule
from ..types import ScheduleId
from ..validation import ensure, ensure_aware

_ONE_MICROSECOND = dt.timedelta(microseconds=1)


@dataclass(slots=True, frozen=True)
class PeriodWindow:
    """Zeitraum einer Auslosung: ab `start`, gültig bis zur nächsten Auslosung `end`."""

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
        """Letzter Kalendertag des Fensters (in der Zeitzone des Beginns; das Ende zählt nicht)."""
        return (self.end.astimezone(self.start.tzinfo) - _ONE_MICROSECOND).date()


def _shift(moment: dt.datetime, amount: int, unit: IntervalUnit) -> dt.datetime:
    """Verschiebt den Zeitpunkt um `amount` Einheiten.

    Stunden zählen in echter Zeit, Tage und Wochen in Kalenderzeit: die Uhrzeit bleibt über eine
    Sommerzeitumstellung gleich.
    """
    if unit is IntervalUnit.HOUR:
        shifted = moment.astimezone(dt.UTC) + dt.timedelta(hours=amount)
        return shifted.astimezone(moment.tzinfo)
    days = amount * INTERVAL_UNIT_HOURS[unit] // HOURS_PER_DAY
    return moment + dt.timedelta(days=days)


def period_start(schedule: Schedule, index: int) -> dt.datetime:
    """Beginn der Periode `index` (0 = `schedule.start`)."""
    interval = schedule.interval
    return _shift(schedule.start, index * interval.every, interval.unit)


def period_window(schedule: Schedule, index: int) -> PeriodWindow:
    """Das Fenster der Periode `index`: von ihrem Beginn bis zum Beginn der nächsten."""
    return PeriodWindow(period_start(schedule, index), period_start(schedule, index + 1))


def effective_window(schedule: Schedule, index: int, now: dt.datetime) -> PeriodWindow:
    """Das Fenster der Zuteilungen einer Auslosung der Periode `index` zum Zeitpunkt `now`.

    Wird eine Periode erst nach ihrem Beginn ausgelost (von Hand oder verspätet), gilt die
    Zuteilung ab jetzt für die Länge der Periode, damit sie nicht schon abgelaufen ist.
    """
    window = period_window(schedule, index)
    if now <= window.start:
        return window
    return PeriodWindow(now, now + (window.end - window.start))


def period_index_at(schedule: Schedule, moment: dt.datetime) -> int | None:
    """Nummer der Periode, in der `moment` liegt; `None` vor dem Beginn des Zeitplans."""
    ensure_aware("moment", moment)
    if moment < schedule.start:
        return None
    elapsed_hours = (moment - schedule.start) / dt.timedelta(hours=1)
    index = int(elapsed_hours // schedule.interval.hours)
    while period_start(schedule, index + 1) <= moment:
        index += 1
    while index > 0 and period_start(schedule, index) > moment:
        index -= 1
    return index


def next_period_start(schedule: Schedule, after: dt.datetime) -> dt.datetime:
    """Beginn der ersten Periode **nach** `after` (vor dem Beginn des Zeitplans: dieser)."""
    index = period_index_at(schedule, after)
    return schedule.start if index is None else period_start(schedule, index + 1)


def next_open_period(rounds: Iterable[Round], schedule_id: ScheduleId) -> int:
    """Nummer der nächsten offenen Periode: die jüngste Auslosung plus eins, sonst die erste."""
    newest = newest_period(rounds, schedule_id)
    return 0 if newest is None else newest + 1


def newest_period(rounds: Iterable[Round], schedule_id: ScheduleId) -> int | None:
    """Nummer der jüngsten Periode, die der Zeitplan ausgelost hat (`None`: noch keine)."""
    return max((r.period_index for r in rounds if r.schedule_id == schedule_id), default=None)
