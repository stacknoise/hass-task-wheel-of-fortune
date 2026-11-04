"""Benachrichtigungen nach Runde, Tausch und Erinnerung (KONZEPT §3.2, §6)."""

import asyncio
import logging
from collections.abc import Iterable

from ..domain.errors import TaskWheelError
from ..domain.models import Assignment, Round, Schedule
from .maintenance_service import Spawn
from .notification_messages import (
    Message,
    drawn_message,
    reminder_message,
    swapped_message,
)
from .protocols import ConfigRepository, NoEvents, Notifier, Texts

_LOGGER = logging.getLogger(__name__)


class NotificationService(NoEvents):
    """Empfänger von `RoundEvents`, der Personen mit Benachrichtigungsziel informiert.

    Ein Ziel, das mehrere Personen teilen, bekommt jede Meldung nur einmal. Das Senden läuft im
    Hintergrund; ein Fehler bei einem Ziel betrifft weder Auslosung noch andere Ziele.
    """

    def __init__(
        self, config: ConfigRepository, notifier: Notifier, texts: Texts, spawn: Spawn
    ) -> None:
        """Hält Konfiguration, Versand, Texte und den Starter für Hintergrundaufgaben."""
        self._config = config
        self._notifier = notifier
        self._texts = texts
        self._spawn = spawn

    def check_target(self, target: str | None) -> None:
        """Prüft das Ziel beim Speichern einer Person; kein Ziel ist erlaubt.

        Raises:
            InvalidNotifyTargetError: Es gibt keine solche `notify`-Entität oder -Dienst.
        """
        if target is not None:
            self._notifier.check(target)

    def round_drawn(self, round_: Round) -> None:
        """Ergebnis an alle Personen mit Ziel, wenn der Zeitplan es vorsieht."""
        schedule = self._config.schedules.get(round_.schedule_id)
        if schedule is None or not schedule.notify or not round_.assignments:
            return
        self._dispatch(
            self._all_targets(), drawn_message(self._config, self._texts, round_, schedule)
        )

    def assignment_swapped(self, assignment: Assignment) -> None:
        """Hinweis an die Person, die die Aufgabe übernommen hat."""
        self._dispatch(
            self._targets_of((assignment.person_id,)),
            swapped_message(self._config, self._texts, assignment),
        )

    def reminder_due(self, schedule: Schedule, days_since: int) -> None:
        """Erinnerung an alle Personen mit Ziel (unabhängig von `Schedule.notify`)."""
        self._dispatch(self._all_targets(), reminder_message(self._texts, schedule, days_since))

    def _all_targets(self) -> tuple[str, ...]:
        """Alle Ziele aller Personen."""
        return self._targets_of(self._config.persons)

    def _targets_of(self, person_ids: Iterable[str]) -> tuple[str, ...]:
        """Ziele der Personen ohne Doppelte, in der Reihenfolge der Personen."""
        targets = (
            person.notify_target
            for person_id in person_ids
            if (person := self._config.persons.get(person_id)) is not None
        )
        return tuple(dict.fromkeys(target for target in targets if target is not None))

    def _dispatch(self, targets: tuple[str, ...], message: Message) -> None:
        """Startet den Versand im Hintergrund, wenn es Empfänger gibt."""
        if targets:
            self._spawn(self._send_all(targets, message))

    async def _send_all(self, targets: tuple[str, ...], message: Message) -> None:
        """Sendet an alle Ziele gleichzeitig."""
        await asyncio.gather(*(self._send_one(target, message) for target in targets))

    async def _send_one(self, target: str, message: Message) -> None:
        """Sendet an ein Ziel; jeder Fehler wird protokolliert, nicht weitergegeben.

        Auch Fehler eines Benachrichtigungsdienstes, die kein Fachfehler sind (etwa ein
        abgelehntes Schema), dürfen die übrigen Ziele und den Hintergrundtask nicht stören.
        """
        try:
            await self._notifier.async_send(target, message.title, message.body)
        except TaskWheelError as err:
            _LOGGER.warning("Benachrichtigung an %s nicht gesendet: %s", target, err.key)
        except Exception:
            _LOGGER.exception("Benachrichtigung an %s fehlgeschlagen", target)
