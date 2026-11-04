"""Reguläre Läufe eines Zeitplans: der nächste, nicht ersetzte."""

import datetime as dt

from ..domain.models import Schedule
from ..domain.triggers.factory import TriggerFactory
from .protocols import HistoryRepository


def next_regular_run(
    history: HistoryRepository, schedule: Schedule, after: dt.datetime
) -> dt.datetime | None:
    """Nächste automatische Auslosung nach `after`; `None` bei pausiert, archiviert, manuell.

    Läufe, die eine manuelle Auslosung vorgezogen hat (`Round.replaces`), entfallen.
    """
    if not schedule.enabled or schedule.archived:
        return None
    strategy = TriggerFactory.create(schedule.trigger)
    replaced = {
        item.replaces
        for item in history.rounds.values()
        if item.schedule_id == schedule.id and item.replaces is not None
    }
    at = strategy.next_fire(after)
    while at is not None and at in replaced:
        at = strategy.next_fire(at)
    return at
