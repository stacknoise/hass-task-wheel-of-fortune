"""Eingaben einer Runde aus Konfiguration und Verlauf (KONZEPT §5.1): einmal pro Runde gelesen."""

import datetime as dt
from collections import defaultdict
from dataclasses import replace

from ..const.limits import RECENT_HISTORY_DAYS
from ..domain.availability.calendar import PersonAvailability
from ..domain.draw.types import DrawContext
from ..domain.enums import Load
from ..domain.models import Assignment, Schedule, Settings, Task
from ..domain.rules.factory import FrequencyRuleFactory
from ..domain.status import counted_points
from ..domain.types import PersonId, TaskId
from .protocols import ConfigRepository, HistoryRepository

type Recent = tuple[tuple[Assignment, dt.datetime], ...]

_DAY = dt.timedelta(days=1)
_NEVER = dt.datetime.min.replace(tzinfo=dt.UTC)


def recent_assignments(history: HistoryRepository, now: dt.datetime) -> Recent:
    """Zuteilungen der letzten `RECENT_HISTORY_DAYS` Tage mit dem Beginn ihrer Runde."""
    rounds = history.rounds
    since = now - RECENT_HISTORY_DAYS * _DAY
    return tuple(
        (item, rounds[item.round_id].started_at) for item in history.assignments_since(since)
    )


def assigned_times(recent: Recent) -> dict[TaskId, list[dt.datetime]]:
    """Zuteilungszeitpunkte je Aufgabe (für die Häufigkeitsregeln)."""
    times: defaultdict[TaskId, list[dt.datetime]] = defaultdict(list)
    for item, started in recent:
        times[item.task_id].append(started)
    return dict(times)


def window_points(recent: Recent, settings: Settings, now: dt.datetime) -> dict[PersonId, float]:
    """Punkte je Person im Fairness-Fenster (Offenes zählt voll, Abgeschlossenes mit Faktor)."""
    start = now - settings.fairness_window_days * _DAY
    points: defaultdict[PersonId, float] = defaultdict(float)
    for item, started in recent:
        if started >= start:
            points[item.person_id] += counted_points(item, settings)
    return dict(points)


def due_tasks(
    config: ConfigRepository, schedule: Schedule, recent: Recent, now: dt.datetime
) -> tuple[Task, ...]:
    """Aufgaben des Zeitplans, die laut Häufigkeitsregel jetzt an der Reihe sind.

    Gelöschte Aufgaben werden übergangen. Ist `skip_absent` aus, gilt Abwesenheit nicht.
    """
    times = assigned_times(recent)
    found = (config.tasks.get(task_id) for task_id in schedule.task_ids)
    due = (
        task
        for task in found
        if task is not None
        and FrequencyRuleFactory.create(task.frequency).is_due(times.get(task.id, ()), now)
    )
    if schedule.skip_absent:
        return tuple(due)
    return tuple(replace(task, respect_absence=False) for task in due)


def limit_to_participants(
    tasks: tuple[Task, ...], context: DrawContext, recent: Recent
) -> tuple[Task, ...]:
    """Beschränkt die Runde auf so viele Aufgaben, wie Personen mitmachen können.

    Jede Person bekommt je Runde höchstens eine Aufgabe; weitere Aufgaben wären nur "nicht
    verteilbar". Es bleiben die Aufgaben, die am längsten nicht zugeteilt wurden (nie Zugeteilte
    zuerst, bei Gleichstand gilt die Reihenfolge des Zeitplans), damit sie über die Runden
    abwechselnd drankommen. Die Reihenfolge der Auswahl bleibt die des Zeitplans.
    """
    if not tasks:
        return tasks
    start = context.now.date()
    end = start + max(task.due_days for task in tasks) * _DAY
    ignores_absence = not all(task.respect_absence for task in tasks)
    seats = sum(
        1
        for pid, person in context.persons.items()
        if person.load is not Load.PAUSED
        and (ignores_absence or context.availability[pid].present_in_window(start, end))
    )
    if seats >= len(tasks):
        return tasks
    last = {task_id: max(times) for task_id, times in assigned_times(recent).items()}
    ranked = sorted(range(len(tasks)), key=lambda i: (last.get(tasks[i].id, _NEVER), i))
    keep = sorted(ranked[:seats])
    return tuple(tasks[i] for i in keep)


def build_context(
    config: ConfigRepository, history: HistoryRepository, recent: Recent, now: dt.datetime
) -> DrawContext:
    """Schnappschuss von Personen, Anwesenheit, Punkten und letzten Inhabern."""
    persons = dict(config.persons)
    holders = {
        task_id: last.person_id
        for task_id in config.tasks
        if (last := history.last_assignment(task_id)) is not None
    }
    return DrawContext(
        now=now,
        persons=persons,
        availability={pid: PersonAvailability.of(person) for pid, person in persons.items()},
        points=window_points(recent, config.settings, now),
        last_holders=holders,
        fairness_window_days=config.settings.fairness_window_days,
    )
