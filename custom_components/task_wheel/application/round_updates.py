"""Gemeinsame Zugriffe der Zuteilungs-Dienste auf den Verlauf (kein duplizierter Code)."""

from collections.abc import Iterable
from dataclasses import replace

from ..const.keys import RESOURCE_ASSIGNMENT
from ..domain.errors import NotFoundError
from ..domain.models import Assignment
from ..domain.statistics.aggregate import AssignmentChange
from ..domain.types import AssignmentId, RoundId
from .protocols import AssignmentRecorder, HistoryRepository


def require_assignment(history: HistoryRepository, assignment_id: AssignmentId) -> Assignment:
    """Liefert die Zuteilung oder wirft `NotFoundError`."""
    assignment = history.get_assignment(assignment_id)
    if assignment is None:
        raise NotFoundError(RESOURCE_ASSIGNMENT, assignment_id)
    return assignment


def store_assignments(
    history: HistoryRepository, recorder: AssignmentRecorder, updated: Iterable[Assignment]
) -> tuple[Assignment, ...]:
    """Ersetzt Zuteilungen in ihren Runden; je Runde ein Speichern und ein Fortschreiben."""
    stored = tuple(updated)
    by_round: dict[RoundId, dict[AssignmentId, Assignment]] = {}
    for item in stored:
        by_round.setdefault(item.round_id, {})[item.id] = item
    for round_id, changes in by_round.items():
        round_ = history.rounds[round_id]
        pairs = tuple(
            AssignmentChange(item, changes[item.id])
            for item in round_.assignments
            if item.id in changes
        )
        assignments = tuple(changes.get(item.id, item) for item in round_.assignments)
        history.put_round(replace(round_, assignments=assignments))
        recorder.record(round_, pairs)
    return stored


def store_assignment(
    history: HistoryRepository, recorder: AssignmentRecorder, updated: Assignment
) -> Assignment:
    """Ersetzt die Zuteilung in ihrer Runde, sichert die Runde und schreibt die Aggregate fort."""
    return store_assignments(history, recorder, (updated,))[0]
