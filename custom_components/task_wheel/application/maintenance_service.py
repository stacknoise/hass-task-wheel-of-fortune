"""Täglicher Wartungslauf: Verpasstes markieren, alte Runden und Logeinträge löschen (§5.4, §8)."""

import datetime as dt
import logging
from collections.abc import Callable, Coroutine
from dataclasses import replace
from typing import Any, Final

from ..const.defaults import MAINTENANCE_HOUR
from ..domain.plan.window import grid_period
from .assignment_service import AssignmentService
from .daily import next_daily
from .decision_service import DecisionService
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
        *,
        decisions: DecisionService | None = None,
    ) -> None:
        """Hält Repositories, Zuteilungsdienst, Zeitgeber, Hintergrundquelle und das Log."""
        self._config = config
        self._history = history
        self._assignments = assignments
        self._timers = timers
        self._spawn = spawn
        self._decisions = decisions

    def start(self, now: dt.datetime) -> None:
        """Holt den Lauf einmal nach (z. B. nach einem Neustart) und plant den nächsten."""
        self._repair_periods()
        self.run(now)

    def _repair_periods(self) -> None:
        """Rückt Runden, die eine Periode im Voraus belegen, auf die Periode ihres Beginns.

        Nach der Umstellung auf Perioden bekamen alte Runden fortlaufende Nummern und liefen dem
        Raster davon; die nächste Auslosung hätte dann eine künftige Periode getroffen.
        """
        for round_ in tuple(self._history.rounds.values()):
            schedule = self._config.schedules.get(round_.schedule_id)
            period = None if schedule is None else grid_period(schedule, round_)
            if period is not None and period != round_.period_index:
                self._history.put_round(replace(round_, period_index=period))

    def run(self, now: dt.datetime) -> None:
        """Plant zuerst den nächsten Lauf (ein Fehler verliert ihn nicht), markiert und räumt."""
        self._timers.schedule(TIMER_MAINTENANCE, next_daily(MAINTENANCE_HOUR, now), self.run)
        self._assignments.mark_missed(now)
        if self._decisions is not None:
            self._decisions.purge(now)
        self._spawn(self._purge(now))

    async def _purge(self, now: dt.datetime) -> None:
        """Löscht Runden außerhalb der Aufbewahrungsfrist (die Aggregate bleiben erhalten)."""
        retention = dt.timedelta(days=self._config.settings.history_retention_days)
        removed = await self._history.async_purge(now - retention)
        if removed:
            _LOGGER.debug("Alte Runden gelöscht: %d", removed)
