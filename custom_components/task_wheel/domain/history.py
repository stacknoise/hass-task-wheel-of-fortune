"""Filter der Historie (KONZEPT §6): Runden und Zuteilungen, die zu einer Abfrage passen."""

import datetime as dt
from dataclasses import dataclass

from .enums import AssignmentStatus
from .models import Assignment, Round
from .types import PersonId, ScheduleId, TaskId
from .validation import ensure_time_range


@dataclass(slots=True, frozen=True, kw_only=True)
class HistoryFilter:
    """Abfrage der Historie; leere Felder filtern nicht.

    `person_id` trifft die aktuelle Person und bei einem Tausch auch die abgebende.
    Der Zeitraum gilt für den Rundenbeginn (`since` einschließlich, `until` ausschließlich).
    """

    schedule_id: ScheduleId | None = None
    person_id: PersonId | None = None
    task_id: TaskId | None = None
    status: AssignmentStatus | None = None
    since: dt.datetime | None = None
    until: dt.datetime | None = None

    def __post_init__(self) -> None:
        """Prüft Zeitzonen und Reihenfolge des Zeitraums."""
        ensure_time_range(self.since, self.until)

    def matches_round(self, round_: Round) -> bool:
        """Zeitplan und Zeitraum der Runde passen."""
        return (
            _same(self.schedule_id, round_.schedule_id)
            and (self.since is None or round_.started_at >= self.since)
            and (self.until is None or round_.started_at < self.until)
        )

    def matches_assignment(self, assignment: Assignment) -> bool:
        """Aufgabe, Status und Person (aktuelle oder abgebende) passen."""
        return (
            _same(self.task_id, assignment.task_id)
            and _same(self.status, assignment.status)
            and self._involves(assignment)
        )

    def _involves(self, assignment: Assignment) -> bool:
        if self.person_id is None:
            return True
        previous = assignment.swap.from_person_id if assignment.swap else None
        return self.person_id in (assignment.person_id, previous)

    def matching(self, round_: Round) -> tuple[Assignment, ...]:
        """Passende Zuteilungen der Runde; leer, wenn die Runde selbst nicht passt."""
        if not self.matches_round(round_):
            return ()
        return tuple(item for item in round_.assignments if self.matches_assignment(item))


def _same[T](wanted: T | None, actual: T) -> bool:
    """Kein Filter gesetzt oder gleich."""
    return wanted is None or wanted == actual
