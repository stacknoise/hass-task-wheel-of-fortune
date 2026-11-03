"""Gemeinsame Zugriffe der Zuteilungs-Dienste auf den Verlauf (kein duplizierter Code)."""

from dataclasses import replace

from ..domain.errors import NotFoundError
from ..domain.models import Assignment
from ..domain.types import AssignmentId
from .protocols import HistoryRepository

RESOURCE_ASSIGNMENT = "assignment"


def require_assignment(history: HistoryRepository, assignment_id: AssignmentId) -> Assignment:
    """Liefert die Zuteilung oder wirft `NotFoundError`."""
    assignment = history.get_assignment(assignment_id)
    if assignment is None:
        raise NotFoundError(RESOURCE_ASSIGNMENT, assignment_id)
    return assignment


def store_assignment(history: HistoryRepository, updated: Assignment) -> Assignment:
    """Ersetzt die Zuteilung in ihrer Runde und sichert die Runde."""
    round_ = history.rounds[updated.round_id]
    assignments = tuple(updated if item.id == updated.id else item for item in round_.assignments)
    history.put_round(replace(round_, assignments=assignments))
    return updated
