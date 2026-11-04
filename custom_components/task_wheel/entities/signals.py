"""Signale der Entitäten und die Meldungen, die sie auslösen (`RoundEvents`-Empfänger)."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..application.protocols import NoEvents
from ..const.entities import SIGNAL_PERSON_TEMPLATE, SIGNAL_SCHEDULE_TEMPLATE
from ..domain.models import Assignment, Round
from ..domain.types import PersonId, ScheduleId


def signal_person(person_id: PersonId) -> str:
    """Signal, auf das die Entitäten einer Person hören."""
    return SIGNAL_PERSON_TEMPLATE.format(item_id=person_id)


def signal_schedule(schedule_id: ScheduleId) -> str:
    """Signal, auf das die Entitäten eines Zeitplans hören."""
    return SIGNAL_SCHEDULE_TEMPLATE.format(item_id=schedule_id)


class EntityEvents(NoEvents):
    """Meldet Änderungen an Zuteilungen den betroffenen Entitäten (kein Abfragen, KONZEPT §6.3)."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Merkt sich Home Assistant für den Dispatcher."""
        self._hass = hass

    def _send(self, *signals: str) -> None:
        for signal in signals:
            async_dispatcher_send(self._hass, signal)

    def round_drawn(self, round_: Round) -> None:
        """Alle Personen der Runde und der Zeitplan (nächste Auslosung) aktualisieren."""
        persons = {item.person_id for item in round_.assignments}
        self._send(signal_schedule(round_.schedule_id), *map(signal_person, persons))

    def _refresh_person(self, assignment: Assignment) -> None:
        """Offene Aufgaben und Punkte der Person aktualisieren."""
        self._send(signal_person(assignment.person_id))

    # Erledigen, Verpassen und „Bleibt unerledigt“ ändern dieselben Entitäten der Person
    assignment_completed = assignment_missed = assignment_skipped = _refresh_person

    def round_deleted(self, round_: Round) -> None:
        """Wie bei einer neuen Runde: alle Personen der Runde und der Zeitplan."""
        self.round_drawn(round_)

    def assignment_swapped(self, assignment: Assignment) -> None:
        """Abgebende und übernehmende Person aktualisieren."""
        persons = [assignment.person_id]
        if assignment.swap is not None:
            persons.append(assignment.swap.from_person_id)
        self._send(*map(signal_person, persons))
