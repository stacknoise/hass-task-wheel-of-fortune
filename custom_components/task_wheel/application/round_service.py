"""Auslosungen löschen: Runde samt Zuteilungen entfernen, Punkte und Statistik zurückrechnen."""

from ..domain.errors import NotFoundError, RoundHasDoneError
from ..domain.models import Round
from ..domain.status import DONE_STATUSES
from ..domain.types import RoundId
from .protocols import AssignmentRecorder, HistoryRepository, NoEvents, RoundEvents

RESOURCE_ROUND = "round"


class RoundService:
    """Löscht eine Runde mit allen Zuteilungen, solange keine davon erledigt ist (KONZEPT §5.4)."""

    def __init__(
        self,
        history: HistoryRepository,
        recorder: AssignmentRecorder,
        events: RoundEvents | None = None,
    ) -> None:
        """Hält Verlauf, Statistik-Empfänger und Events."""
        self._history = history
        self._recorder = recorder
        self._events = events or NoEvents()

    def delete(self, round_id: RoundId) -> Round:
        """Entfernt die Runde; die Aggregate (Anzahl und Punkte) verlieren ihre Zuteilungen.

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
        self._events.round_deleted(round_)
        return round_
