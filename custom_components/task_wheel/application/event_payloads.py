"""Inhalt der Events (KONZEPT §6.2): nur Kennungen, Namen und Zahlen, keine Konfiguration."""

from typing import Any

from ..const.keys import (
    ATTR_ASSIGNMENT_ID,
    ATTR_ASSIGNMENTS,
    ATTR_DAYS_SINCE,
    ATTR_DUE_AT,
    ATTR_FROM_PERSON_ID,
    ATTR_FROM_PERSON_NAME,
    ATTR_ORIGIN,
    ATTR_PERSON_ID,
    ATTR_PERSON_NAME,
    ATTR_POINTS,
    ATTR_ROUND_ID,
    ATTR_SCHEDULE_ID,
    ATTR_SCHEDULE_NAME,
    ATTR_STATUS,
    ATTR_TASK_ID,
    ATTR_TASK_NAME,
)
from ..domain.models import Assignment, Round, Schedule
from .names import person_name, schedule_name, task_name
from .protocols import ConfigRepository

type Payload = dict[str, Any]


def assignment_payload(config: ConfigRepository, assignment: Assignment) -> Payload:
    """Eine Zuteilung mit Aufgabe, Person, Punkten und Frist."""
    return {
        ATTR_ASSIGNMENT_ID: assignment.id,
        ATTR_TASK_ID: assignment.task_id,
        ATTR_TASK_NAME: task_name(config, assignment),
        ATTR_PERSON_ID: assignment.person_id,
        ATTR_PERSON_NAME: person_name(config, assignment.person_id),
        ATTR_POINTS: assignment.points,
        ATTR_DUE_AT: assignment.due_at.isoformat(),
        ATTR_STATUS: str(assignment.status),
    }


def round_payload(config: ConfigRepository, round_: Round) -> Payload:
    """Eine Runde mit allen Zuteilungen."""
    return {
        ATTR_ROUND_ID: round_.id,
        ATTR_SCHEDULE_ID: round_.schedule_id,
        ATTR_SCHEDULE_NAME: schedule_name(config, round_.schedule_id),
        ATTR_ORIGIN: str(round_.origin),
        ATTR_ASSIGNMENTS: [assignment_payload(config, item) for item in round_.assignments],
    }


def swapped_payload(config: ConfigRepository, assignment: Assignment) -> Payload:
    """Eine getauschte Zuteilung samt abgebender Person."""
    payload = assignment_payload(config, assignment)
    if assignment.swap is not None:
        payload[ATTR_FROM_PERSON_ID] = assignment.swap.from_person_id
        payload[ATTR_FROM_PERSON_NAME] = person_name(config, assignment.swap.from_person_id)
    return payload


def reminder_payload(schedule: Schedule, days_since: int) -> Payload:
    """Erinnerung an einen Zeitplan ohne Auslosung."""
    return {
        ATTR_SCHEDULE_ID: schedule.id,
        ATTR_SCHEDULE_NAME: schedule.name,
        ATTR_DAYS_SINCE: days_since,
    }
