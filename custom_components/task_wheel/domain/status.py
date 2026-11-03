"""Statusübergänge der Zuteilungen (KONZEPT §5.4) als Tabelle, dazu Punkte und Fristen."""

import datetime as dt
from collections.abc import Callable, Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import Final

from .enums import AssignmentAction, AssignmentStatus
from .errors import InvalidTransitionError
from .models import Assignment, Settings, Swap
from .types import PersonId

_S = AssignmentStatus
_A = AssignmentAction

# (Status, Aktion) -> neuer Status. Alles, was hier fehlt, ist unzulässig.
TRANSITIONS: Final[Mapping[tuple[AssignmentStatus, AssignmentAction], AssignmentStatus]] = (
    MappingProxyType(
        {
            (_S.OPEN, _A.COMPLETE_ON_TIME): _S.ON_TIME,
            (_S.OPEN, _A.COMPLETE_LATE): _S.LATE,
            (_S.OPEN, _A.MISS): _S.MISSED,
            (_S.OPEN, _A.SWAP): _S.SWAPPED,
            (_S.SWAPPED, _A.COMPLETE_ON_TIME): _S.ON_TIME,
            (_S.SWAPPED, _A.COMPLETE_LATE): _S.LATE,
            (_S.SWAPPED, _A.MISS): _S.MISSED,
        }
    )
)

# Noch nicht abgeschlossen: kann erledigt oder verpasst werden (offen oder getauscht).
PENDING_STATUSES: Final[frozenset[AssignmentStatus]] = frozenset({_S.OPEN, _S.SWAPPED})

# Status -> Faktor auf die Aufgabenpunkte; nicht gelistete Status zählen noch nicht.
_POINT_FACTORS: Final[Mapping[AssignmentStatus, Callable[[Settings], float]]] = MappingProxyType(
    {
        _S.ON_TIME: lambda _settings: 1.0,
        _S.LATE: lambda settings: settings.late_points_factor,
        _S.MISSED: lambda settings: settings.missed_points_factor,
    }
)


def _no_points(_settings: Settings) -> float:
    """Offene und getauschte Zuteilungen zählen noch nicht."""
    return 0.0


def next_status(status: AssignmentStatus, action: AssignmentAction) -> AssignmentStatus:
    """Liefert den Folgestatus.

    Raises:
        InvalidTransitionError: Die Aktion ist im Status nicht zulässig.
    """
    target = TRANSITIONS.get((status, action))
    if target is None:
        raise InvalidTransitionError(status, action)
    return target


def completion_action(assignment: Assignment, now: dt.datetime) -> AssignmentAction:
    """Erledigen gilt bis einschließlich `due_at` als pünktlich, danach als verspätet."""
    return _A.COMPLETE_ON_TIME if now <= assignment.due_at else _A.COMPLETE_LATE


def complete(assignment: Assignment, now: dt.datetime) -> Assignment:
    """Erledigt die Zuteilung zum Zeitpunkt `now` (pünktlich oder verspätet)."""
    status = next_status(assignment.status, completion_action(assignment, now))
    return replace(assignment, status=status, done_at=now)


def miss(assignment: Assignment) -> Assignment:
    """Markiert die Zuteilung als verpasst."""
    return replace(assignment, status=next_status(assignment.status, _A.MISS))


def swap(assignment: Assignment, to_person_id: PersonId, now: dt.datetime) -> Assignment:
    """Übergibt die Zuteilung an `to_person_id`; die Punkte gehen mit."""
    status = next_status(assignment.status, _A.SWAP)
    record = Swap(from_person_id=assignment.person_id, to_person_id=to_person_id, at=now)
    return replace(assignment, status=status, person_id=to_person_id, swap=record)


def missed_deadline(assignment: Assignment, settings: Settings) -> dt.datetime:
    """Zeitpunkt, nach dem eine offene Zuteilung als verpasst gilt (Frist + Kulanzzeit)."""
    return assignment.due_at + dt.timedelta(hours=settings.missed_grace_hours)


def is_missable(assignment: Assignment, settings: Settings, now: dt.datetime) -> bool:
    """Die Zuteilung darf verpasst werden und die Kulanzzeit ist abgelaufen."""
    return (assignment.status, _A.MISS) in TRANSITIONS and now > missed_deadline(
        assignment, settings
    )


def points_factor(status: AssignmentStatus, settings: Settings) -> float:
    """Faktor auf die Aufgabenpunkte im Status (offen und getauscht zählen noch nicht)."""
    return _POINT_FACTORS.get(status, _no_points)(settings)


def awarded_points(assignment: Assignment, settings: Settings) -> int:
    """Punkte, die der Person der Zuteilung im aktuellen Status gutgeschrieben werden."""
    return round(assignment.points * points_factor(assignment.status, settings))
