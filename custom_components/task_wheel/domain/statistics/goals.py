"""Soll-Ist je Zeitplan und Aufgabe: Verlosungen im Fenster der Regel „n-mal in x Zeiträumen“."""

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ...const.defaults import DEFAULT_GOAL_WINDOWS
from ...const.limits import ONE_DAY
from ..enums import DONE_STATUSES, Period
from ..models import Assignment, MaxPerPeriod, Schedule, Task
from ..rules.periods import local_date, shift_periods, window_start
from ..types import ScheduleId, TaskId

type Placed = tuple[Assignment, dt.datetime]


@dataclass(slots=True, frozen=True)
class GoalWindow:
    """Ein Fenster aus `every` Perioden von `start` bis `end` (einschließlich) mit den Zahlen."""

    start: dt.date
    end: dt.date
    assigned: int
    done: int


@dataclass(slots=True, frozen=True)
class TaskGoal:
    """Soll und Stand einer Aufgabe in einem Zeitplan: laufendes Fenster zuerst, dann frühere."""

    schedule_id: ScheduleId
    task_id: TaskId
    target: int
    period: Period
    every: int
    windows: tuple[GoalWindow, ...]


def _window(
    start: dt.date, end: dt.date, placed: Iterable[tuple[dt.date, bool]], today: dt.date
) -> GoalWindow:
    """Zählt Zuteilungen (Tag, erledigt) in `[start, end]`, höchstens bis heute."""
    last = min(end, today)
    inside = [done for day, done in placed if start <= day <= last]
    return GoalWindow(start, end, len(inside), sum(inside))


def task_goal(
    schedule_id: ScheduleId,
    task: Task,
    placed: Iterable[Placed],
    now: dt.datetime,
    windows: int = DEFAULT_GOAL_WINDOWS,
) -> TaskGoal | None:
    """Soll-Ist der Aufgabe im Zeitplan; ohne „höchstens n-mal …“ gibt es kein Soll.

    Gezählt werden nur Zuteilungen, die dieser Zeitplan ausgelost hat.

    Die Fenster schließen lückenlos aneinander an (je `every` Perioden): das erste endet mit der
    laufenden Periode, die übrigen sind abgeschlossene frühere Fenster.
    """
    rule = task.frequency
    if not isinstance(rule, MaxPerPeriod):
        return None
    mine = [
        (local_date(started, now), item.status in DONE_STATUSES)
        for item, started in placed
        if item.task_id == task.id and item.schedule_id == schedule_id
    ]
    first = window_start(rule.period, rule.every, now)
    result: list[GoalWindow] = []
    for back in range(windows):
        start = shift_periods(rule.period, first, -back * rule.every)
        end = shift_periods(rule.period, start, rule.every) - ONE_DAY
        result.append(_window(start, end, mine, now.date()))
    return TaskGoal(schedule_id, task.id, rule.count, rule.period, rule.every, tuple(result))


def goals_start(
    tasks: Iterable[Task], now: dt.datetime, windows: int = DEFAULT_GOAL_WINDOWS
) -> dt.date:
    """Frühester Tag der Fenster aller Aufgaben mit Soll (so weit muss der Verlauf reichen)."""
    starts = [
        shift_periods(
            task.frequency.period,
            window_start(task.frequency.period, task.frequency.every, now),
            -(windows - 1) * task.frequency.every,
        )
        for task in tasks
        if isinstance(task.frequency, MaxPerPeriod)
    ]
    return min(starts, default=now.date())


def build_goals(
    schedules: Iterable[Schedule],
    tasks: Mapping[TaskId, Task],
    placed: Iterable[Placed],
    now: dt.datetime,
    windows: int = DEFAULT_GOAL_WINDOWS,
) -> tuple[TaskGoal, ...]:
    """Soll-Ist je Zeitplan (nicht archiviert) für dessen Aufgaben mit „höchstens n-mal …“.

    Eine Aufgabe in mehreren Zeitplänen erscheint je Zeitplan und wird dort getrennt gezählt.
    """
    placed = tuple(placed)
    found = (
        task_goal(schedule.id, tasks[task_id], placed, now, windows)
        for schedule in schedules
        if not schedule.archived
        for task_id in schedule.task_ids
        if task_id in tasks
    )
    return tuple(goal for goal in found if goal is not None)
