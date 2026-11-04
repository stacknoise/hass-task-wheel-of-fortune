"""Gemeinsame Zugriffe der Zuteilungs-Dienste auf den Verlauf (kein duplizierter Code)."""

from dataclasses import replace

from ..const.keys import RESOURCE_ASSIGNMENT
from ..domain.errors import NotFoundError
from ..domain.models import Assignment
from ..domain.statistics.aggregate import AssignmentChange
from ..domain.types import AssignmentId
from .protocols import AssignmentRecorder, HistoryRepository


def require_assignment(history: HistoryRepository, assignment_id: AssignmentId) -> Assignment:
    """Liefert die Zuteilung oder wirft `NotFoundError`."""
    assignment = history.get_assignment(assignment_id)
    if assignment is None:
        raise NotFoundError(RESOURCE_ASSIGNMENT, assignment_id)
    return assignment


def store_assignment(
    history: HistoryRepository, recorder: AssignmentRecorder, updated: Assignment
) -> Assignment:
    """Ersetzt die Zuteilung in ihrer Runde, sichert die Runde und schreibt die Aggregate fort."""
    round_ = history.rounds[updated.round_id]
    before = history.get_assignment(updated.id)
    assignments = tuple(updated if item.id == updated.id else item for item in round_.assignments)
    history.put_round(replace(round_, assignments=assignments))
    recorder.record(round_, (AssignmentChange(before, updated),))
    return updated
