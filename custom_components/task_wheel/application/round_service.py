"""Auslosungen löschen: Runde samt Zuteilungen entfernen, Punkte und Statistik zurückrechnen."""

from ..domain.errors import NotFoundError
from ..domain.models import Round
from ..domain.types import RoundId
from .protocols import AssignmentRecorder, HistoryRepository, NoEvents, RoundEvents

RESOURCE_ROUND = "round"


class RoundService:
    """Löscht eine Runde mit allen Zuteilungen (auch erledigten, KONZEPT §5.5)."""

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
        """
        removed = self._history.remove_round(round_id)
        if removed is None:
            raise NotFoundError(RESOURCE_ROUND, round_id)
        self._recorder.forget_round(removed)
        self._events.round_deleted(removed)
        return removed
