"""Zeitpläne: Termine im Raster berechnen, Zeitgeber gezielt setzen, automatisch auslosen."""

import datetime as dt
import logging
from typing import Final

from ..const.keys import ERR_NOTHING_DUE, ERR_PERIOD_DRAWN
from ..domain.enums import RoundOrigin
from ..domain.errors import TaskWheelError
from ..domain.models import Schedule
from ..domain.plan.window import next_period_start, period_index_at, period_start
from ..domain.types import ScheduleId
from .draw_service import DrawService
from .protocols import ConfigRepository, HistoryRepository, NoEvents, RoundEvents, TimerPort

_LOGGER = logging.getLogger(__name__)

TIMER_PREFIX: Final = "schedule:"


def timer_key(schedule_id: ScheduleId) -> str:
    """Schlüssel des Zeitgebers eines Zeitplans."""
    return f"{TIMER_PREFIX}{schedule_id}"


class ScheduleService:
    """Setzt für jeden aktiven Zeitplan genau einen Zeitgeber auf seine nächste Auslösung."""

    def __init__(
        self,
        config: ConfigRepository,
        history: HistoryRepository,
        draws: DrawService,
        timers: TimerPort,
        events: RoundEvents | None = None,
    ) -> None:
        """Hält Repositories, Auslosung, Zeitgeber und Ereignisempfänger."""
        self._config = config
        self._history = history
        self._draws = draws
        self._timers = timers
        self._events = events or NoEvents()

    def next_run(self, schedule: Schedule, after: dt.datetime) -> dt.datetime | None:
        """Nächste Auslosung zur Anzeige; `None` bei pausiert oder archiviert.

        Automatisch: der nächste Termin im Raster. Manuell: der Termin der nächsten offenen
        Periode (liegt er in der Vergangenheit, ist die Auslosung fällig).
        """
        if not schedule.enabled or schedule.archived:
            return None
        if schedule.automatic:
            return next_period_start(schedule, after)
        return period_start(schedule, self._draws.next_period(schedule.id))

    def arm(self, schedule_id: ScheduleId, now: dt.datetime) -> dt.datetime | None:
        """Setzt den Zeitgeber dieses Zeitplans neu (nur dieser) und liefert den Zeitpunkt.

        Der Zeitgeber läuft zu jedem Termin im Raster: automatische Zeitpläne losen dann aus,
        manuelle erinnern. Gibt es den Zeitplan nicht mehr oder ist er pausiert oder archiviert,
        wird der Zeitgeber abgemeldet.
        """
        schedule = self._config.schedules.get(schedule_id)
        active = schedule is not None and schedule.enabled and not schedule.archived
        if schedule is None or not active:
            self._timers.cancel(timer_key(schedule_id))
            return None
        at = next_period_start(schedule, now)
        self._timers.schedule(
            timer_key(schedule_id), at, lambda fired: self._on_fire(schedule_id, at, fired)
        )
        return at

    def arm_all(self, now: dt.datetime) -> None:
        """Setzt die Zeitgeber aller Zeitpläne (verpasste Termine werden nicht nachgeholt)."""
        for schedule_id in self._config.schedules:
            self.arm(schedule_id, now)

    def save(self, schedule: Schedule, now: dt.datetime) -> None:
        """Legt den Zeitplan an oder ersetzt ihn und setzt seinen Zeitgeber neu."""
        self._config.put_schedule(schedule)
        self.arm(schedule.id, now)

    def delete(self, schedule_id: ScheduleId) -> None:
        """Entfernt den Zeitplan und meldet seinen Zeitgeber ab."""
        self._config.remove_schedule(schedule_id)
        self.disarm(schedule_id)

    def disarm(self, schedule_id: ScheduleId) -> None:
        """Meldet den Zeitgeber eines Zeitplans ab (z. B. nach dem Löschen)."""
        self._timers.cancel(timer_key(schedule_id))

    def disarm_all(self) -> None:
        """Meldet alle Zeitgeber ab (Entladen der Integration)."""
        self._timers.cancel_all()

    def _last_drawn(self, schedule_id: ScheduleId) -> dt.datetime | None:
        """Beginn der jüngsten Runde des Zeitplans (jeder Herkunft)."""
        starts = [
            r.started_at for r in self._history.rounds.values() if r.schedule_id == schedule_id
        ]
        return max(starts, default=None)

    def _on_fire(self, schedule_id: ScheduleId, planned: dt.datetime, fired: dt.datetime) -> None:
        """Zeitgeber ausgelöst: automatisch auslosen oder (manuell) erinnern; immer neu setzen."""
        now = max(fired, planned)
        schedule = self._config.schedules.get(schedule_id)
        if schedule is None:
            return
        try:
            if schedule.automatic:
                self._draw(schedule, now)
            else:
                self._remind(schedule, now)
        finally:
            self.arm(schedule_id, now)

    def _draw(self, schedule: Schedule, now: dt.datetime) -> None:
        """Löst die Periode dieses Termins aus; eine schon ausgloste oder gelöschte entfällt."""
        index = period_index_at(schedule, now)
        if index is None:
            return
        try:
            self._draws.draw(schedule.id, RoundOrigin.AUTO, now, index)
        except TaskWheelError as err:
            if err.key in {ERR_NOTHING_DUE, ERR_PERIOD_DRAWN}:
                _LOGGER.info("Auslosung übersprungen (%s): %s", err.key, schedule.slug)
                return
            _LOGGER.warning(
                "Automatische Auslosung fehlgeschlagen: %s", schedule.slug, exc_info=True
            )

    def _remind(self, schedule: Schedule, now: dt.datetime) -> None:
        """Erinnert an die fällige Auslosung eines manuellen Zeitplans (Tage seit der letzten)."""
        if period_start(schedule, self._draws.next_period(schedule.id)) > now:
            return
        last = self._last_drawn(schedule.id)
        self._events.reminder_due(schedule, 0 if last is None else (now.date() - last.date()).days)
