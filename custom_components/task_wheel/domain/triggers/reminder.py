"""Erinnerung für Zeitpläne „nur manuell“: wann ist sie fällig (stateless)."""

import datetime as dt

from ..models import ManualTrigger, Schedule
from ..rules.periods import local_date


def days_since(last: dt.datetime, now: dt.datetime) -> int:
    """Kalendertage seit `last` in der Zeitzone von `now`."""
    return (now.date() - local_date(last, now)).days


def reminder_age(
    schedule: Schedule, last_drawn: dt.datetime | None, now: dt.datetime
) -> int | None:
    """Tage seit der letzten Auslosung, wenn heute eine Erinnerung fällig ist, sonst `None`.

    Erinnert wird nach `remind_after_days` Tagen und danach alle weiteren `remind_after_days` Tage
    (Vielfache), solange nicht ausgelost wurde. Wurde noch nie ausgelost, gibt es keinen
    Bezugspunkt und damit keine Erinnerung.
    """
    trigger = schedule.trigger
    active = schedule.enabled and not schedule.archived
    if not (active and isinstance(trigger, ManualTrigger)) or trigger.remind_after_days is None:
        return None
    if last_drawn is None:
        return None
    age = days_since(last_drawn, now)
    due = age > 0 and age % trigger.remind_after_days == 0
    return age if due else None
