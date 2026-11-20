"""Soll-Ist je Zeitplan und Aufgabe: Verlosungen je Lauf gegen die Mindesthäufigkeit."""

import datetime as dt
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from ...const.defaults import DEFAULT_GOAL_WINDOWS
from ..enums import DONE_STATUSES
from ..models import Round, Schedule
from ..plan.window import period_index_at, period_start
from ..types import ScheduleId, TaskId


@dataclass(slots=True, frozen=True)
class GoalWindow:
    """Ein Lauf von `start` bis `end` (Kalendertage) mit den Zahlen.

    `elapsed` ist die Zahl der Auslosungen des Laufs, die schon stattfinden konnten (im laufenden
    Lauf weniger als `draws`); das anteilige Soll ist `target * elapsed / draws`.
    """

    start: dt.date
    end: dt.date
    draws: int
    elapsed: int
    assigned: int
    done: int


@dataclass(slots=True, frozen=True)
class TaskGoal:
    """Soll und Stand einer Aufgabe in einem Zeitplan: laufender Lauf zuerst, dann frühere."""

    schedule_id: ScheduleId
    task_id: TaskId
    target: int
    windows: tuple[GoalWindow, ...]


def _window(schedule: Schedule, run: int, current: int, counts: tuple[int, int]) -> GoalWindow:
    """Der Lauf `run`; `current` ist die Nummer der laufenden Periode, `counts` (Ist, erledigt)."""
    draws = schedule.draws_per_run
    first, after = run * draws, (run + 1) * draws
    start = period_start(schedule, first).date()
    end = period_start(schedule, after).date() - dt.timedelta(days=1)
    elapsed = max(0, min(draws, current + 1 - first))
    return GoalWindow(start, end, draws, elapsed, *counts)


def _counts(rounds: Iterable[Round], draws: int) -> dict[tuple[int, TaskId], tuple[int, int]]:
    """Zuteilungen (Ist, erledigt) je Lauf und Aufgabe, in einem Durchlauf über die Runden."""
    assigned: Counter[tuple[int, TaskId]] = Counter()
    done: Counter[tuple[int, TaskId]] = Counter()
    for round_ in rounds:
        run = round_.period_index // draws
        for item in round_.assignments:
            assigned[run, item.task_id] += 1
            done[run, item.task_id] += item.status in DONE_STATUSES
    return {key: (count, done[key]) for key, count in assigned.items()}


def schedule_goals(
    schedule: Schedule,
    rounds: Iterable[Round],
    now: dt.datetime,
    windows: int = DEFAULT_GOAL_WINDOWS,
) -> tuple[TaskGoal, ...]:
    """Soll-Ist je Aufgabe des Zeitplans für die letzten `windows` Läufe (der laufende zuerst).

    Gezählt werden nur Zuteilungen, die dieser Zeitplan ausgelost hat. Vor dem Beginn des
    Zeitplans und für archivierte gibt es kein Soll.
    """
    current = period_index_at(schedule, now)
    if current is None or schedule.archived:
        return ()
    draws = schedule.draws_per_run
    counts = _counts((round_ for round_ in rounds if round_.schedule_id == schedule.id), draws)
    current_run = current // draws
    runs = [run for run in range(current_run, current_run - windows, -1) if run >= 0]
    return tuple(
        TaskGoal(
            schedule.id,
            entry.task_id,
            draws if entry.every_draw else entry.min_count,
            tuple(
                _window(schedule, run, current, counts.get((run, entry.task_id), (0, 0)))
                for run in runs
            ),
        )
        for entry in schedule.entries
    )


def build_goals(
    schedules: Iterable[Schedule],
    rounds: Iterable[Round],
    now: dt.datetime,
    windows: int = DEFAULT_GOAL_WINDOWS,
) -> tuple[TaskGoal, ...]:
    """Soll-Ist je Zeitplan (nicht archiviert) für alle seine Aufgaben.

    Eine Aufgabe in mehreren Zeitplänen erscheint je Zeitplan und wird dort getrennt gezählt.
    """
    kept = tuple(rounds)
    return tuple(
        goal for schedule in schedules for goal in schedule_goals(schedule, kept, now, windows)
    )
