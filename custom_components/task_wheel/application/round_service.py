"""Auslosungen löschen: Runde samt Zuteilungen entfernen, Punkte und Statistik zurückrechnen."""

from ..const.keys import RESOURCE_ROUND
from ..domain.enums import DONE_STATUSES
from ..domain.errors import NotFoundError, RoundHasDoneError
from ..domain.models import Round
from ..domain.types import RoundId
from .protocols import (
    AssignmentRecorder,
    DecisionRecorder,
    HistoryRepository,
    NoDecisions,
    NoEvents,
    RoundEvents,
)


class RoundService:
    """Löscht eine Runde mit allen Zuteilungen, solange keine davon erledigt ist (KONZEPT §5.4)."""

    def __init__(
        self,
        history: HistoryRepository,
        recorder: AssignmentRecorder,
        events: RoundEvents | None = None,
        decisions: DecisionRecorder | None = None,
    ) -> None:
        """Hält Verlauf, Statistik-Empfänger, Events und das Entscheidungslog."""
        self._history = history
        self._recorder = recorder
        self._events = events or NoEvents()
        self._decisions = decisions or NoDecisions()

    def delete(self, round_id: RoundId) -> Round:
        """Entfernt die Runde; Aggregate und Entscheidungslog verlieren ihre Einträge.

        Raises:
            NotFoundError: Die Runde gibt es nicht (mehr).
            RoundHasDoneError: Mindestens eine Zuteilung der Runde ist schon erledigt.
        """
        round_ = self._history.rounds.get(round_id)
        if round_ is None:
            raise NotFoundError(RESOURCE_ROUND, round_id)
        done = sum(item.status in DONE_STATUSES for item in round_.assignments)
        if done:
            raise RoundHasDoneError(round_id, done)
        self._history.remove_round(round_id)
        self._recorder.forget_round(round_)
        self._decisions.forget_round(round_id)
        self._events.round_deleted(round_)
        return round_
