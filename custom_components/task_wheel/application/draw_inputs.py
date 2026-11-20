"""Eingaben einer Runde aus Konfiguration und Verlauf (KONZEPT §5.1): einmal pro Runde gelesen."""

import datetime as dt
from collections import defaultdict
from dataclasses import replace

from ..const.limits import ONE_DAY, RECENT_HISTORY
from ..domain.availability.calendar import PersonAvailability
from ..domain.draw.feasibility import pick_assignable, unassignable_tasks
from ..domain.draw.types import DrawContext, RandomSource
from ..domain.models import Assignment, Schedule, Settings, Task
from ..domain.plan.due import DueRanking, rank_tasks
from ..domain.plan.window import PeriodWindow, period_window
from ..domain.status import counted_points
from ..domain.types import PersonId, ScheduleId, TaskId
from .protocols import ConfigRepository, HistoryRepository

type Recent = tuple[tuple[Assignment, dt.datetime], ...]


def recent_assignments(history: HistoryRepository, now: dt.datetime) -> Recent:
    """Zuteilungen der letzten `RECENT_HISTORY_DAYS` Tage mit dem Beginn ihrer Runde."""
    rounds = history.rounds
    since = now - RECENT_HISTORY
    return tuple(
        (item, rounds[item.round_id].started_at) for item in history.assignments_since(since)
    )


def last_periods(history: HistoryRepository, schedule_id: ScheduleId) -> dict[TaskId, int]:
    """Nummer der jüngsten Periode je Aufgabe, in der der Zeitplan sie zugeteilt hat."""
    last: dict[TaskId, int] = {}
    for round_ in history.rounds.values():
        if round_.schedule_id != schedule_id:
            continue
        for item in round_.assignments:
            last[item.task_id] = max(
                last.get(item.task_id, round_.period_index), round_.period_index
            )
    return last


def window_points(recent: Recent, settings: Settings, now: dt.datetime) -> dict[PersonId, float]:
    """Punkte je Person im Fairness-Fenster (Offenes zählt voll, Abgeschlossenes mit Faktor)."""
    start = now - settings.fairness_window_days * ONE_DAY
    points: defaultdict[PersonId, float] = defaultdict(float)
    for item, started in recent:
        if started >= start:
            points[item.person_id] += counted_points(item, settings)
    return dict(points)


def ranked_tasks(
    config: ConfigRepository,
    history: HistoryRepository,
    schedule: Schedule,
    period: int,
    rng: RandomSource,
) -> DueRanking:
    """Die Aufgaben des Zeitplans für die Periode `period`: jede Auslosung, fällige, übrige.

    Gelöschte Aufgaben werden übergangen. Ist `skip_absent` aus, gilt Abwesenheit nicht.
    """
    found = (config.tasks.get(task_id) for task_id in schedule.task_ids)
    tasks = tuple(respecting_schedule(schedule, task) for task in found if task is not None)
    return rank_tasks(schedule, tasks, last_periods(history, schedule.id), period, rng)


def respecting_schedule(schedule: Schedule, task: Task) -> Task:
    """Die Aufgabe, wie der Zeitplan sie behandelt (ohne `skip_absent` zählt Abwesenheit nicht)."""
    return task if schedule.skip_absent else replace(task, respect_absence=False)


def shuffled(tasks: tuple[Task, ...], rng: RandomSource) -> tuple[Task, ...]:
    """Die Aufgaben in zufälliger Reihenfolge (jede Anordnung gleich wahrscheinlich).

    In dieser Reihenfolge wird gezogen. Bliebe sie die des Zeitplans, wäre bei Einschränkungen
    (nur bestimmte Personen erlaubt) die Folge der Gewinner in jeder Runde dieselbe.
    """
    keys = [rng.random() for _ in tasks]
    return tuple(tasks[i] for i in sorted(range(len(tasks)), key=keys.__getitem__))


def choose_tasks(ranking: DueRanking, context: DrawContext) -> tuple[Task, ...]:
    """Wählt die Aufgaben der Auslosung so, dass sich alle vergeben lassen.

    Jede Person bekommt je Auslosung höchstens eine Aufgabe, und nicht jede darf, kann oder ist da
    (erlaubt, belastbar, im Periodenfenster anwesend). Gewählt wird eine größtmögliche Menge der
    „jede Auslosung“-Aufgaben und der fälligen, in dieser Reihenfolge: sind mehr fällig als
    Personen, entscheidet der gewichtete Zufall (Überlast). Ist nichts vergebbar fällig (Lücke),
    zieht der Zufall die erste vergebbare der übrigen Aufgaben nach.
    """
    priority = ranking.priority
    picked = pick_assignable(priority, context, range(len(priority))) if priority else ()
    for spare in () if picked else ranking.spare:
        picked = pick_assignable((spare,), context, (0,))
        if picked:
            break
    return picked


def unassignable_every_draw(
    config: ConfigRepository, history: HistoryRepository, schedule: Schedule, now: dt.datetime
) -> tuple[Task, ...]:
    """„Jede Auslosung“-Aufgaben des Zeitplans, die sich nicht alle verteilen lassen.

    Geprüft wird die Konfiguration: erlaubte Personen und Belastbarkeit, jede Person höchstens
    eine Aufgabe. Abwesenheit zählt nicht (vorübergehend; die Auslosung wählt dann zufällig).
    """
    found = (config.tasks.get(entry.task_id) for entry in schedule.entries if entry.every_draw)
    tasks = [replace(task, respect_absence=False) for task in found if task]
    context = build_context(config, history, (), now, period_window(schedule, 0))
    return unassignable_tasks(tasks, context)


def build_context(
    config: ConfigRepository,
    history: HistoryRepository,
    recent: Recent,
    now: dt.datetime,
    window: PeriodWindow,
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
