"""Tausch zweier Zuteilungen einer Runde, Aufgabe gegen Aufgabe (KONZEPT §5.4)."""

import datetime as dt

from ..const.keys import RESOURCE_PERSON, RESOURCE_TASK
from ..domain import status
from ..domain.enums import AssignmentAction
from ..domain.errors import NotFoundError
from ..domain.models import Assignment
from ..domain.swap import SwapSide, ensure_swap_possible, find_counterpart
from ..domain.types import AssignmentId, PersonId
from .protocols import (
    AssignmentRecorder,
    ConfigRepository,
    HistoryRepository,
    NoEvents,
    RoundEvents,
)
from .round_updates import require_assignment, store_assignments


class SwapService:
    """Prüft und führt einen Tausch aus; beide Personen behalten je eine Aufgabe."""

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

    def _side(self, assignment: Assignment) -> SwapSide:
        """Zuteilung mit Aufgabe und Person, oder `NotFoundError`."""
        task = self._config.tasks.get(assignment.task_id)
        person = self._config.persons.get(assignment.person_id)
        if task is None:
            raise NotFoundError(RESOURCE_TASK, assignment.task_id)
        if person is None:
            raise NotFoundError(RESOURCE_PERSON, assignment.person_id)
        return SwapSide(assignment, task, person)

    def swap(
        self, assignment_id: AssignmentId, to_person_id: PersonId, now: dt.datetime
    ) -> Assignment:
        """Tauscht die offene Zuteilung gegen die offene Zuteilung von `to_person_id`.

        Gegenstück ist die offene Zuteilung der Zielperson in derselben Runde (bei mehreren die
        mit der frühesten Frist). Beide Zuteilungen werden getauscht und gemeinsam gespeichert.

        Returns:
            Die getauschte Zuteilung `assignment_id`, die jetzt `to_person_id` gehört.

        Raises:
            NotFoundError: Zuteilung, Aufgabe oder Person gibt es nicht.
            InvalidTransitionError: Die Zuteilung ist nicht (mehr) offen oder schon getauscht.
            SwapRejectedError: Es fehlt das Gegenstück oder eine Aufgabe, Person oder Regel
                lässt den Tausch nicht zu (in beiden Richtungen).
        """
        assignment = require_assignment(self._history, assignment_id)
        if to_person_id not in self._config.persons:
            raise NotFoundError(RESOURCE_PERSON, to_person_id)
        status.next_status(assignment.status, AssignmentAction.SWAP)
        round_ = self._history.rounds[assignment.round_id]
        other = find_counterpart(round_.assignments, assignment, to_person_id)
        ensure_swap_possible(self._side(assignment), self._side(other), now)
        swapped, swapped_other = store_assignments(
            self._history,
            self._recorder,
            (
                status.swap(assignment, other.person_id, now),
                status.swap(other, assignment.person_id, now),
            ),
        )
        self._events.assignment_swapped(swapped)
        self._events.assignment_swapped(swapped_other)
        return swapped
