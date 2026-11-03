"""Eingaben einer Runde aus Konfiguration und Verlauf (KONZEPT §5.1): einmal pro Runde gelesen."""

import datetime as dt
from collections import defaultdict
from dataclasses import replace

from ..const.limits import RECENT_HISTORY_DAYS
from ..domain.availability.calendar import PersonAvailability
from ..domain.draw.types import DrawContext
from ..domain.models import Assignment, Schedule, Settings, Task
from ..domain.rules.factory import FrequencyRuleFactory
from ..domain.status import counted_points
from ..domain.types import PersonId, TaskId
from .protocols import ConfigRepository, HistoryRepository

type Recent = tuple[tuple[Assignment, dt.datetime], ...]

_DAY = dt.timedelta(days=1)


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
