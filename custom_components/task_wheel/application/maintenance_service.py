"""Täglicher Wartungslauf: Verpasstes markieren, alte Runden löschen (KONZEPT §5.4, §8)."""

import datetime as dt
import logging
from collections.abc import Callable, Coroutine
from typing import Any, Final

from ..const.defaults import MAINTENANCE_HOUR
from .assignment_service import AssignmentService
from .daily import next_daily
from .protocols import ConfigRepository, HistoryRepository, TimerPort

_LOGGER = logging.getLogger(__name__)

TIMER_MAINTENANCE: Final = "maintenance"

type Spawn = Callable[[Coroutine[Any, Any, None]], object]


class MaintenanceService:
    """Läuft beim Start und danach jede Nacht; Aufräumen läuft im Hintergrund (Speicher-I/O)."""

    def __init__(
        self,
        config: ConfigRepository,
        history: HistoryRepository,
        assignments: AssignmentService,
        timers: TimerPort,
        spawn: Spawn,
    ) -> None:
        """Hält Repositories, Zuteilungsdienst, Zeitgeber und die Quelle für Hintergrundaufgaben."""
        self._config = config
        self._history = history
        self._assignments = assignments
        self._timers = timers
        self._spawn = spawn

    def start(self, now: dt.datetime) -> None:
        """Holt den Lauf einmal nach (z. B. nach einem Neustart) und plant den nächsten."""
        self.run(now)

    def run(self, now: dt.datetime) -> None:
        """Markiert Verpasstes, stößt das Aufräumen an und plant den nächsten Lauf."""
        self._assignments.mark_missed(now)
        self._spawn(self._purge(now))
        at = next_daily(MAINTENANCE_HOUR, now)
        if at is not None:
            self._timers.schedule(TIMER_MAINTENANCE, at, self.run)

    async def _purge(self, now: dt.datetime) -> None:
        """Löscht Runden außerhalb der Aufbewahrungsfrist (die Aggregate bleiben erhalten)."""
        retention = dt.timedelta(days=self._config.settings.history_retention_days)
        removed = await self._history.async_purge(now - retention)
        if removed:
            _LOGGER.debug("Alte Runden gelöscht: %d", removed)
