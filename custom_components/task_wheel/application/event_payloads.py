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
from .protocols import ConfigRepository

type Payload = dict[str, Any]


def _task_name(config: ConfigRepository, assignment: Assignment) -> str:
    """Name der Aufgabe; eine inzwischen gelöschte Aufgabe wird über ihre Kennung genannt."""
    task = config.tasks.get(assignment.task_id)
    return task.name if task is not None else assignment.task_id


def _person_name(config: ConfigRepository, person_id: str) -> str:
    """Name der Person; eine inzwischen gelöschte Person wird über ihre Kennung genannt."""
    person = config.persons.get(person_id)
    return person.name if person is not None else person_id


def _schedule_name(config: ConfigRepository, schedule_id: str) -> str:
    """Name des Zeitplans; ein gelöschter Zeitplan wird über seine Kennung genannt."""
    schedule = config.schedules.get(schedule_id)
    return schedule.name if schedule is not None else schedule_id


def assignment_payload(config: ConfigRepository, assignment: Assignment) -> Payload:
    """Eine Zuteilung mit Aufgabe, Person, Punkten und Frist."""
    return {
        ATTR_ASSIGNMENT_ID: assignment.id,
        ATTR_TASK_ID: assignment.task_id,
        ATTR_TASK_NAME: _task_name(config, assignment),
        ATTR_PERSON_ID: assignment.person_id,
        ATTR_PERSON_NAME: _person_name(config, assignment.person_id),
        ATTR_POINTS: assignment.points,
        ATTR_DUE_AT: assignment.due_at.isoformat(),
        ATTR_STATUS: str(assignment.status),
    }


def round_payload(config: ConfigRepository, round_: Round) -> Payload:
    """Eine Runde mit allen Zuteilungen."""
    return {
        ATTR_ROUND_ID: round_.id,
        ATTR_SCHEDULE_ID: round_.schedule_id,
        ATTR_SCHEDULE_NAME: _schedule_name(config, round_.schedule_id),
        ATTR_ORIGIN: str(round_.origin),
        ATTR_ASSIGNMENTS: [assignment_payload(config, item) for item in round_.assignments],
    }


def swapped_payload(config: ConfigRepository, assignment: Assignment) -> Payload:
    """Eine getauschte Zuteilung samt abgebender Person."""
    payload = assignment_payload(config, assignment)
    if assignment.swap is not None:
        payload[ATTR_FROM_PERSON_ID] = assignment.swap.from_person_id
        payload[ATTR_FROM_PERSON_NAME] = _person_name(config, assignment.swap.from_person_id)
    return payload


def reminder_payload(schedule: Schedule, days_since: int) -> Payload:
    """Erinnerung an einen Zeitplan ohne Auslosung."""
    return {
        ATTR_SCHEDULE_ID: schedule.id,
        ATTR_SCHEDULE_NAME: schedule.name,
        ATTR_DAYS_SINCE: days_since,
    }
