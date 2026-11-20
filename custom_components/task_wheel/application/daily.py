"""Tägliche Zeitpunkte (Wartungslauf, Erinnerungsprüfung)."""

import datetime as dt

from ..const.limits import ONE_DAY


def next_daily(hour: int, after: dt.datetime) -> dt.datetime:
    """Nächster Zeitpunkt nach `after`, an dem es `hour`:00 Uhr (Ortszeit von `after`) ist."""
    today = dt.datetime.combine(after.date(), dt.time(hour), tzinfo=after.tzinfo)
    return today if today > after else today + ONE_DAY
