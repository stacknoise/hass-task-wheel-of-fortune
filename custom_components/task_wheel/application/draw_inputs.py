"""Eingaben einer Runde aus Konfiguration und Verlauf (KONZEPT §5.1): einmal pro Runde gelesen."""

import datetime as dt
from collections import defaultdict
from dataclasses import replace

from ..const.limits import ONE_DAY, RECENT_HISTORY
from ..domain.availability.calendar import PersonAvailability
from ..domain.deadline import DeadlineWindow
from ..domain.draw.feasibility import pick_assignable, unassignable_tasks
from ..domain.draw.types import DrawContext, RandomSource
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
    return tuple(respecting_schedule(schedule, task) for task in due)


def respecting_schedule(schedule: Schedule, task: Task) -> Task:
    """Die Aufgabe, wie der Zeitplan sie behandelt (ohne `skip_absent` zählt Abwesenheit nicht)."""
    return task if schedule.skip_absent else replace(task, respect_absence=False)


def _priority(tasks: tuple[Task, ...], rng: RandomSource) -> list[int]:
    """Reihenfolge der Auswahl: Aufgaben „in jeder Runde“ und tägliche zuerst, dann zufällig."""
    keys = [rng.random() for _ in tasks]
    return sorted(range(len(tasks)), key=lambda i: (not tasks[i].is_mandatory, keys[i]))


def select_assignable(
    tasks: tuple[Task, ...], context: DrawContext, rng: RandomSource
) -> tuple[Task, ...]:
    """Wählt die Aufgaben der Runde so, dass sich alle vergeben lassen.

    Jede Person bekommt je Runde höchstens eine Aufgabe, und nicht jede darf, kann oder ist da
    (erlaubt, belastbar, im Fristfenster anwesend). Gewählt wird eine größtmögliche Menge, die
    sich vollständig an verschiedene Personen vergeben lässt. Aufgaben „in jeder Runde“ und täglich
    anfallende sind zuerst dabei, der Rest wird zufällig gefüllt (nicht vorhersehbar). Gibt es etwa
    wegen Abwesenheit weniger Personen als solche Aufgaben, entscheidet der Zufall unter ihnen.
    Aufgaben, die niemand übernehmen kann, und solche, die um dieselben Personen konkurrieren und
    leer ausgingen, bleiben draußen. Die Reihenfolge der Auswahl bleibt die des Zeitplans.
    """
    return pick_assignable(tasks, context, _priority(tasks, rng)) if tasks else tasks


def unassignable_every_round(
    config: ConfigRepository, history: HistoryRepository, schedule: Schedule, now: dt.datetime
) -> tuple[Task, ...]:
    """Aufgaben „in jeder Runde“ des Zeitplans, die sich nicht alle verteilen lassen.

    Geprüft wird die Konfiguration: erlaubte Personen und Belastbarkeit, jede Person höchstens
    eine Aufgabe. Abwesenheit zählt nicht (vorübergehend; die Auslosung wählt dann zufällig).
    """
    found = (config.tasks.get(task_id) for task_id in schedule.task_ids)
    tasks = [replace(task, respect_absence=False) for task in found if task and task.every_round]
    context = build_context(config, history, (), now, schedule.deadline.window(now))
    return unassignable_tasks(tasks, context)


def build_context(
    config: ConfigRepository,
    history: HistoryRepository,
    recent: Recent,
    now: dt.datetime,
    window: DeadlineWindow,
) -> DrawContext:
    """Schnappschuss von Personen, Anwesenheit, Punkten, letzten Inhabern und Frist-Fenster."""
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
        window=window,
    )
