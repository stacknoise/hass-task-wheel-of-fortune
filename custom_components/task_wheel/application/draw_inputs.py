"""Eingaben einer Runde aus Konfiguration und Verlauf (KONZEPT §5.1): einmal pro Runde gelesen."""

import datetime as dt
from collections import defaultdict
from dataclasses import replace

from ..const.limits import ONE_DAY, RECENT_HISTORY
from ..domain.availability.calendar import PersonAvailability
from ..domain.draw.types import DrawContext, RandomSource
from ..domain.enums import Load
from ..domain.models import Assignment, Schedule, Settings, Task
from ..domain.rules.factory import FrequencyRuleFactory
from ..domain.status import counted_points
from ..domain.types import PersonId, TaskId
from .protocols import ConfigRepository, HistoryRepository

type Recent = tuple[tuple[Assignment, dt.datetime], ...]


def recent_assignments(history: HistoryRepository, now: dt.datetime) -> Recent:
    """Zuteilungen der letzten `RECENT_HISTORY_DAYS` Tage mit dem Beginn ihrer Runde."""
    rounds = history.rounds
    since = now - RECENT_HISTORY
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
    start = now - settings.fairness_window_days * ONE_DAY
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


def _seats(tasks: tuple[Task, ...], context: DrawContext) -> int:
    """Personen, die in dieser Runde eine Aufgabe übernehmen können (nicht pausiert, anwesend)."""
    start = context.now.date()
    end = start + max(task.due_days for task in tasks) * ONE_DAY
    ignores_absence = not all(task.respect_absence for task in tasks)
    return sum(
        1
        for pid, person in context.persons.items()
        if person.load is not Load.PAUSED
        and (ignores_absence or context.availability[pid].present_in_window(start, end))
    )


def _random_pick(tasks: tuple[Task, ...], rng: RandomSource, count: int) -> tuple[Task, ...]:
    """`count` zufällig gewählte Aufgaben (gleiche Chance), in der Reihenfolge des Zeitplans."""
    keys = [rng.random() for _ in tasks]
    ranked = sorted(range(len(tasks)), key=keys.__getitem__)
    return tuple(tasks[i] for i in sorted(ranked[:count]))


def limit_to_participants(
    tasks: tuple[Task, ...], context: DrawContext, rng: RandomSource
) -> tuple[Task, ...]:
    """Beschränkt die Runde auf so viele Aufgaben, wie Personen mitmachen können.

    Jede Person bekommt je Runde höchstens eine Aufgabe; weitere Aufgaben wären nur "nicht
    verteilbar". Gibt es mehr Aufgaben als Plätze, wird zufällig gewählt (nicht vorhersehbar);
    die Reihenfolge der Auswahl bleibt die des Zeitplans.
    """
    if not tasks:
        return tasks
    seats = _seats(tasks, context)
    return tasks if seats >= len(tasks) else _random_pick(tasks, rng, seats)


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
