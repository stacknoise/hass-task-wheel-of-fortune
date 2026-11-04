"""Zeitpläne: nächste Auslosung berechnen, Zeitgeber gezielt setzen, Erinnerungen (KONZEPT §5.5)."""

import datetime as dt
import logging
from typing import Final

from ..const.defaults import REMINDER_HOUR
from ..domain.enums import RoundOrigin
from ..domain.errors import TaskWheelError
from ..domain.models import OnceTrigger, Round, Schedule
from ..domain.triggers.lifecycle import after_fired
from ..domain.triggers.reminder import reminder_age
from ..domain.types import ScheduleId
from .daily import next_daily
from .draw_service import DrawService
from .protocols import ConfigRepository, HistoryRepository, NoEvents, RoundEvents, TimerPort
from .runs import next_regular_run

_LOGGER = logging.getLogger(__name__)

TIMER_PREFIX: Final = "schedule:"
TIMER_REMINDERS: Final = "reminders"


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
        return next_regular_run(self._history, schedule, after)

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
        """Holt verpasste einmalige Termine nach; setzt alle Zeitgeber und die Erinnerungen."""
        for schedule in tuple(self._config.schedules.values()):
            if self._missed_once(schedule, now):
                self._draw_and_finish(schedule, now)
        for schedule_id in self._config.schedules:
            self.arm(schedule_id, now)
        self.arm_reminders(now)

    def _missed_once(self, schedule: Schedule, now: dt.datetime) -> bool:
        """Ein aktiver einmaliger Zeitplan, dessen Termin in der Ausfallzeit lag und noch fehlt."""
        trigger = schedule.trigger
        if not isinstance(trigger, OnceTrigger) or not schedule.enabled or schedule.archived:
            return False
        if trigger.at > now:
            return False
        last = self._last_drawn(schedule.id)
        return last is None or last < trigger.at

    def save(self, schedule: Schedule, now: dt.datetime) -> None:
        """Legt den Zeitplan an oder ersetzt ihn und setzt seinen Zeitgeber neu."""
        self._config.put_schedule(schedule)
        self.arm(schedule.id, now)

    def round_committed(self, round_: Round, now: dt.datetime) -> None:
        """Nach einer manuellen Auslosung: ersetzten Lauf übergehen und den Zeitgeber neu setzen.

        Ein einmaliger Zeitplan, dessen Termin die Auslosung vorgezogen hat, gilt als erledigt.
        """
        schedule = self._config.schedules.get(round_.schedule_id)
        if schedule is not None and round_.replaces is not None:
            self._finish_once(schedule)
        self.arm(round_.schedule_id, now)

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

    def arm_reminders(self, now: dt.datetime) -> None:
        """Setzt die tägliche Erinnerungsprüfung auf das nächste Mal."""
        at = next_daily(REMINDER_HOUR, now)
        if at is not None:
            self._timers.schedule(TIMER_REMINDERS, at, self.check_reminders)

    def check_reminders(self, now: dt.datetime) -> None:
        """Plant die nächste Prüfung (zuerst, damit ein Fehler sie nicht verliert) und meldet."""
        self.arm_reminders(now)
        for schedule in self._config.schedules.values():
            age = reminder_age(schedule, self._last_drawn(schedule.id), now)
            if age is not None:
                self._events.reminder_due(schedule, age)

    def _last_drawn(self, schedule_id: ScheduleId) -> dt.datetime | None:
        """Beginn der jüngsten Runde des Zeitplans (jeder Herkunft)."""
        starts = [
            r.started_at for r in self._history.rounds.values() if r.schedule_id == schedule_id
        ]
        return max(starts, default=None)

    def _on_fire(self, schedule_id: ScheduleId, planned: dt.datetime, fired: dt.datetime) -> None:
        """Zeitgeber ausgelöst: auslosen, einmalige Pläne abschließen, immer neu setzen."""
        now = max(fired, planned)
        schedule = self._config.schedules.get(schedule_id)
        if schedule is None:
            return
        try:
            self._draw_and_finish(schedule, now)
        finally:
            self.arm(schedule_id, now)

    def _draw_and_finish(self, schedule: Schedule, now: dt.datetime) -> None:
        """Löst aus; nur nach einer gelungenen Auslosung gilt ein einmaliger Plan als erledigt."""
        try:
            self._draws.draw(schedule.id, RoundOrigin.AUTO, now)
        except TaskWheelError:
            _LOGGER.warning(
                "Automatische Auslosung fehlgeschlagen: %s", schedule.slug, exc_info=True
            )
            return
        self._finish_once(schedule)

    def _finish_once(self, schedule: Schedule) -> None:
        """Wendet an, was nach einem einmaligen Zeitplan gilt (behalten, archivieren, löschen)."""
        updated = after_fired(schedule)
        if updated is None:
            self._config.remove_schedule(schedule.id)
        elif updated != schedule:
            self._config.put_schedule(updated)
