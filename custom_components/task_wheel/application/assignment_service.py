"""Erledigen und „verpasst“ (KONZEPT §5.4); Uhrzeit kommt als Parameter."""

import datetime as dt

from ..const.limits import OPEN_ASSIGNMENT_MAX_AGE_DAYS
from ..domain import status
from ..domain.models import Assignment
from ..domain.types import AssignmentId
from .protocols import AssignmentRecorder, ConfigRepository, HistoryRepository
from .round_updates import require_assignment, store_assignment

_MAX_AGE = dt.timedelta(days=OPEN_ASSIGNMENT_MAX_AGE_DAYS)


class AssignmentService:
    """Statuswechsel einer Zuteilung und deren Punkte."""

    def __init__(
        self, config: ConfigRepository, history: HistoryRepository, recorder: AssignmentRecorder
    ) -> None:
        """Hält die Repositories und den Empfänger der Statusänderungen (Statistik)."""
        self._config = config
        self._history = history
        self._recorder = recorder

    def complete(self, assignment_id: AssignmentId, now: dt.datetime) -> Assignment:
        """Erledigt die Zuteilung (pünktlich bis `due_at`, danach verspätet).

        Raises:
            NotFoundError: Die Zuteilung gibt es nicht.
            InvalidTransitionError: Die Zuteilung ist nicht mehr offen.
        """
        assignment = require_assignment(self._history, assignment_id)
        return store_assignment(self._history, self._recorder, status.complete(assignment, now))

    def mark_missed(self, now: dt.datetime) -> tuple[Assignment, ...]:
        """Täglicher Lauf: markiert Zuteilungen als verpasst, deren Kulanzzeit abgelaufen ist."""
        settings = self._config.settings
        due = [
            item
            for item in self._history.assignments_since(now - _MAX_AGE)
            if status.is_missable(item, settings, now)
        ]
        return tuple(
            store_assignment(self._history, self._recorder, status.miss(item)) for item in due
        )

    def points(self, assignment: Assignment) -> int:
        """Punkte, die die Zuteilung im aktuellen Status zählt (Faktoren aus den Einstellungen)."""
        return status.awarded_points(assignment, self._config.settings)
