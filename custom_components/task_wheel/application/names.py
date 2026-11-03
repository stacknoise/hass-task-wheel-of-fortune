"""Namen für Meldungen: gelöschte Elemente werden über ihre Kennung genannt."""

from ..domain.models import Assignment
from .protocols import ConfigRepository


def task_name(config: ConfigRepository, assignment: Assignment) -> str:
    """Name der Aufgabe; eine inzwischen gelöschte Aufgabe wird über ihre Kennung genannt."""
    task = config.tasks.get(assignment.task_id)
    return task.name if task is not None else assignment.task_id


def person_name(config: ConfigRepository, person_id: str) -> str:
    """Name der Person; eine inzwischen gelöschte Person wird über ihre Kennung genannt."""
    person = config.persons.get(person_id)
    return person.name if person is not None else person_id


def schedule_name(config: ConfigRepository, schedule_id: str) -> str:
    """Name des Zeitplans; ein gelöschter Zeitplan wird über seine Kennung genannt."""
    schedule = config.schedules.get(schedule_id)
    return schedule.name if schedule is not None else schedule_id
