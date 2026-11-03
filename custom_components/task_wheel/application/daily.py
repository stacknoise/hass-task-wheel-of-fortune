"""Tägliche Zeitpunkte: derselbe Mechanismus wie bei wiederkehrenden Zeitplänen."""

import datetime as dt

from ..const.limits import WEEKDAY_MAX, WEEKDAY_MIN
from ..domain.models import Recurring
from ..domain.triggers.factory import TriggerFactory

_EVERY_WEEKDAY = frozenset(range(WEEKDAY_MIN, WEEKDAY_MAX + 1))


def next_daily(hour: int, after: dt.datetime) -> dt.datetime | None:
    """Nächster Zeitpunkt nach `after`, an dem es `hour`:00 Uhr (Ortszeit von `after`) ist."""
    trigger = Recurring(weekdays=_EVERY_WEEKDAY, time=dt.time(hour))
    return TriggerFactory.create(trigger).next_fire(after)
