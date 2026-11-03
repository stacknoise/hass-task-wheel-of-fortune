"""Zeitpläne: nächste Auslosung berechnen, Zeitgeber gezielt setzen, Erinnerungen (KONZEPT §5.5)."""

import datetime as dt
import logging
from typing import Final

from ..const.defaults import REMINDER_HOUR
from ..const.limits import WEEKDAY_MAX, WEEKDAY_MIN
from ..domain.enums import RoundOrigin
from ..domain.errors import TaskWheelError
from ..domain.models import Recurring, Schedule
from ..domain.triggers.factory import TriggerFactory
from ..domain.triggers.lifecycle import after_fired
from ..domain.triggers.reminder import reminder_age
from ..domain.types import ScheduleId
from .draw_service import DrawService
from .protocols import ConfigRepository, HistoryRepository, NoEvents, RoundEvents, TimerPort

_LOGGER = logging.getLogger(__name__)

TIMER_PREFIX: Final = "schedule:"
TIMER_REMINDERS: Final = "reminders"

# Täglich zur vollen Stunde `REMINDER_HOUR`: derselbe Mechanismus wie bei wiederkehrenden Plänen
_DAILY_REMINDER: Final = Recurring(
    weekdays=frozenset(range(WEEKDAY_MIN, WEEKDAY_MAX + 1)), time=dt.time(REMINDER_HOUR)
)


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
        """Nächste automatische Auslosung nach `after`; `None` bei pausiert, archiviert, manuell."""
        if not schedule.enabled or schedule.archived:
            return None
        return TriggerFactory.create(schedule.trigger).next_fire(after)

    def arm(self, schedule_id: ScheduleId, now: dt.datetime) -> dt.datetime | None:
        """Setzt den Zeitgeber dieses Zeitplans neu (nur dieser) und liefert den Zeitpunkt.

        Gibt es den Zeitplan nicht mehr oder steht nichts an, wird der Zeitgeber abgemeldet.
        """
        schedule = self._config.schedules.get(schedule_id)
        at = self.next_run(schedule, now) if schedule is not None else None
        if at is None:
            self._timers.cancel(timer_key(schedule_id))
            return None
        self._timers.schedule(
            timer_key(schedule_id), at, lambda fired: self._on_fire(schedule_id, at, fired)
        )
        return at

    def arm_all(self, now: dt.datetime) -> None:
        """Setzt alle Zeitgeber (beim Start) und die tägliche Erinnerungsprüfung."""
        for schedule_id in self._config.schedules:
            self.arm(schedule_id, now)
        self.arm_reminders(now)

    def disarm(self, schedule_id: ScheduleId) -> None:
        """Meldet den Zeitgeber eines Zeitplans ab (z. B. nach dem Löschen)."""
        self._timers.cancel(timer_key(schedule_id))

    def disarm_all(self) -> None:
        """Meldet alle Zeitgeber ab (Entladen der Integration)."""
        self._timers.cancel_all()

    def arm_reminders(self, now: dt.datetime) -> None:
        """Setzt die tägliche Erinnerungsprüfung auf das nächste Mal."""
        at = TriggerFactory.create(_DAILY_REMINDER).next_fire(now)
        if at is not None:
            self._timers.schedule(TIMER_REMINDERS, at, self.check_reminders)

    def check_reminders(self, now: dt.datetime) -> None:
        """Meldet alle fälligen Erinnerungen und plant die nächste Prüfung."""
        for schedule in self._config.schedules.values():
            age = reminder_age(schedule, self._last_drawn(schedule.id), now)
            if age is not None:
                self._events.reminder_due(schedule, age)
        self.arm_reminders(now)

    def _last_drawn(self, schedule_id: ScheduleId) -> dt.datetime | None:
        """Beginn der jüngsten Runde des Zeitplans (jeder Herkunft)."""
        starts = [
            r.started_at for r in self._history.rounds.values() if r.schedule_id == schedule_id
        ]
        return max(starts, default=None)

    def _on_fire(self, schedule_id: ScheduleId, planned: dt.datetime, fired: dt.datetime) -> None:
        """Zeitgeber ausgelöst: auslosen, einmalige Pläne abschließen, nächsten Zeitgeber setzen."""
        now = max(fired, planned)
        schedule = self._config.schedules.get(schedule_id)
        if schedule is None:
            return
        try:
            self._draws.draw(schedule_id, RoundOrigin.AUTO, now)
        except TaskWheelError:
            _LOGGER.warning(
                "Automatische Auslosung fehlgeschlagen: %s", schedule.slug, exc_info=True
            )
        self._finish_once(schedule)
        self.arm(schedule_id, now)

    def _finish_once(self, schedule: Schedule) -> None:
        """Wendet an, was nach einem einmaligen Zeitplan gilt (behalten, archivieren, löschen)."""
        updated = after_fired(schedule)
        if updated is None:
            self._config.remove_schedule(schedule.id)
        elif updated != schedule:
            self._config.put_schedule(updated)
