"""Tausch einer Zuteilung gegen einen Joker (KONZEPT §5.4); Uhrzeit kommt als Parameter."""

import datetime as dt

from ..const.limits import OPEN_ASSIGNMENT_MAX_AGE_DAYS
from ..domain import status
from ..domain.enums import AssignmentAction, Period
from ..domain.errors import NotFoundError
from ..domain.models import Assignment
from ..domain.rules.periods import period_start
from ..domain.swap import SwapContext, ensure_swap_possible, jokers_left, jokers_used
from ..domain.types import AssignmentId, PersonId
from .protocols import ConfigRepository, HistoryRepository
from .round_updates import require_assignment, store_assignment

_RESOURCE_PERSON = "person"
_RESOURCE_TASK = "task"
_OPEN_MAX_AGE = dt.timedelta(days=OPEN_ASSIGNMENT_MAX_AGE_DAYS)


class SwapService:
    """Prüft und führt einen Tausch aus; Joker werden je Kalendermonat gezählt."""

    def __init__(self, config: ConfigRepository, history: HistoryRepository) -> None:
        """Hält die Repositories."""
        self._config = config
        self._history = history

    def jokers_left(self, person_id: PersonId, now: dt.datetime) -> int:
        """Verbleibende Joker im laufenden Kalendermonat (ohne Rücksetzen, der Monat zählt neu)."""
        month_start = dt.datetime.combine(
            period_start(Period.MONTH, now), dt.time.min, tzinfo=now.tzinfo
        )
        recent = self._history.assignments_since(month_start - _OPEN_MAX_AGE)
        return jokers_left(self._config.settings, jokers_used(recent, person_id, now))

    def swap(
        self, assignment_id: AssignmentId, to_person_id: PersonId, now: dt.datetime
    ) -> Assignment:
        """Übergibt die offene Zuteilung an `to_person_id` und verbraucht einen Joker.

        Raises:
            NotFoundError: Zuteilung, Aufgabe oder Person gibt es nicht.
            InvalidTransitionError: Die Zuteilung ist nicht (mehr) offen oder schon getauscht.
            SwapRejectedError: Die Aufgabe oder die neue Person lässt den Tausch nicht zu.
        """
        assignment = require_assignment(self._history, assignment_id)
        task = self._config.tasks.get(assignment.task_id)
        receiver = self._config.persons.get(to_person_id)
        if task is None:
            raise NotFoundError(_RESOURCE_TASK, assignment.task_id)
        if receiver is None:
            raise NotFoundError(_RESOURCE_PERSON, to_person_id)
        status.next_status(assignment.status, AssignmentAction.SWAP)
        left = self.jokers_left(assignment.person_id, now)
        ensure_swap_possible(SwapContext(assignment, task, receiver, left, now))
        return store_assignment(self._history, status.swap(assignment, to_person_id, now))
