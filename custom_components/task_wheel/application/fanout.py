"""Verteilt die Meldungen einer Runde an mehrere Empfänger (`RoundEvents`)."""

import logging
from collections.abc import Callable

from ..domain.models import Assignment, Round, Schedule
from .protocols import RoundEvents

_LOGGER = logging.getLogger(__name__)


class FanOutRoundEvents:
    """Gibt jede Meldung an alle Empfänger weiter; ein fehlerhafter stört die anderen nicht."""

    def __init__(self, *sinks: RoundEvents) -> None:
        """Merkt sich die Empfänger in der Reihenfolge, in der sie gerufen werden."""
        self._sinks = sinks

    def _each(self, notify: Callable[[RoundEvents], None]) -> None:
        """Ruft `notify` für jeden Empfänger und protokolliert Fehler."""
        for sink in self._sinks:
            try:
                notify(sink)
            except Exception:
                _LOGGER.exception("Empfänger %s hat eine Meldung nicht verarbeitet", type(sink))

    def round_drawn(self, round_: Round) -> None:
        """Eine Runde wurde ausgelost."""
        self._each(lambda sink: sink.round_drawn(round_))

    def reminder_due(self, schedule: Schedule, days_since: int) -> None:
        """Ein Zeitplan wurde seit `days_since` Tagen nicht ausgelost."""
        self._each(lambda sink: sink.reminder_due(schedule, days_since))

    def assignment_completed(self, assignment: Assignment) -> None:
        """Eine Zuteilung wurde erledigt."""
        self._each(lambda sink: sink.assignment_completed(assignment))

    def assignment_swapped(self, assignment: Assignment) -> None:
        """Eine Zuteilung wurde getauscht."""
        self._each(lambda sink: sink.assignment_swapped(assignment))

    def assignment_missed(self, assignment: Assignment) -> None:
        """Eine Zuteilung wurde als verpasst markiert."""
        self._each(lambda sink: sink.assignment_missed(assignment))

    def assignment_skipped(self, assignment: Assignment) -> None:
        """Eine Zuteilung bleibt unerledigt."""
        self._each(lambda sink: sink.assignment_skipped(assignment))

    def round_deleted(self, round_: Round) -> None:
        """Eine Runde wurde gelöscht."""
        self._each(lambda sink: sink.round_deleted(round_))

    def animation_requested(self, round_: Round, target: str) -> None:
        """Eine Anzeige soll die Auslosung zeigen."""
        self._each(lambda sink: sink.animation_requested(round_, target))
