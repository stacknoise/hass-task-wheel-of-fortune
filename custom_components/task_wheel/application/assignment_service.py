"""Erledigen und „verpasst“ (KONZEPT §5.4); Uhrzeit kommt als Parameter."""

import datetime as dt

from ..const.keys import RESOURCE_ASSIGNMENT
from ..const.limits import OPEN_ASSIGNMENT_MAX_AGE
from ..domain import status
from ..domain.errors import NotFoundError
from ..domain.models import Assignment
from ..domain.types import AssignmentId, PersonId, TaskId
from .protocols import (
    AssignmentRecorder,
    ConfigRepository,
    HistoryRepository,
    NoEvents,
    RoundEvents,
)
from .round_updates import require_assignment, store_assignment, store_assignments


class AssignmentService:
    """Statuswechsel einer Zuteilung und deren Punkte."""

    def __init__(
        self,
        config: ConfigRepository,
        history: HistoryRepository,
        recorder: AssignmentRecorder,
        events: RoundEvents | None = None,
    ) -> None:
        """Hält die Repositories, den Empfänger der Statusänderungen (Statistik) und die Events."""
        self._config = config
        self._history = history
        self._recorder = recorder
        self._events = events or NoEvents()

    def find_open(self, person_id: PersonId, task_id: TaskId) -> Assignment:
        """Die offene Zuteilung der Person für die Aufgabe (bei mehreren die mit frühester Frist).

        Raises:
            NotFoundError: Die Person hat die Aufgabe nicht offen.
        """
        matching = [
            item for item in self._history.open_assignments(person_id) if item.task_id == task_id
        ]
        if not matching:
            raise NotFoundError(RESOURCE_ASSIGNMENT, f"{person_id}/{task_id}")
        return min(matching, key=lambda item: item.due_at)

    def complete(self, assignment_id: AssignmentId, now: dt.datetime) -> Assignment:
        """Erledigt die Zuteilung (pünktlich bis `due_at`, danach verspätet).

        Raises:
            NotFoundError: Die Zuteilung gibt es nicht.
            InvalidTransitionError: Die Zuteilung ist nicht mehr offen.
        """
        assignment = require_assignment(self._history, assignment_id)
        done = store_assignment(self._history, self._recorder, status.complete(assignment, now))
        self._events.assignment_completed(done)
        return done

    def skip(self, assignment_id: AssignmentId) -> Assignment:
        """Markiert die offene Zuteilung als „Bleibt unerledigt“ (zählt wie verpasst).

        Raises:
            NotFoundError: Die Zuteilung gibt es nicht.
            InvalidTransitionError: Die Zuteilung ist nicht mehr offen.
        """
        assignment = require_assignment(self._history, assignment_id)
        skipped = store_assignment(self._history, self._recorder, status.skip(assignment))
        self._events.assignment_skipped(skipped)
        return skipped

    def mark_missed(self, now: dt.datetime) -> tuple[Assignment, ...]:
        """Täglicher Lauf: markiert Zuteilungen als verpasst, deren Kulanzzeit abgelaufen ist."""
        settings = self._config.settings
        due = [
            item
            for item in self._history.assignments_since(now - OPEN_ASSIGNMENT_MAX_AGE)
            if status.is_missable(item, settings, now)
        ]
        missed = store_assignments(
            self._history, self._recorder, (status.miss(item) for item in due)
        )
        for item in missed:
            self._events.assignment_missed(item)
        return missed

    def points(self, assignment: Assignment) -> int:
        """Punkte, die die Zuteilung im aktuellen Status zählt (Faktoren aus den Einstellungen)."""
        return status.awarded_points(assignment, self._config.settings)
