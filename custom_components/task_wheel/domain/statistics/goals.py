"""Soll-Ist je Aufgabe: wie oft wurde sie im Fenster ihrer Regel „n-mal in x Zeiträumen“ verlost."""

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ...const.defaults import DEFAULT_GOAL_WINDOWS
from ..enums import Period
from ..models import Assignment, MaxPerPeriod, Task
from ..rules.periods import local_date, shift_periods, window_start
from ..status import DONE_STATUSES
from ..types import TaskId

type Placed = tuple[Assignment, dt.datetime]
_DAY = dt.timedelta(days=1)


@dataclass(slots=True, frozen=True)
class GoalWindow:
    """Ein Fenster aus `every` Perioden von `start` bis `end` (einschließlich) mit den Zahlen."""

    start: dt.date
    end: dt.date
    assigned: int
    done: int


@dataclass(slots=True, frozen=True)
class TaskGoal:
    """Soll und Stand einer Aufgabe: das laufende Fenster zuerst, dann frühere (neueste zuerst)."""

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
    task: Task, placed: Iterable[Placed], now: dt.datetime, windows: int = DEFAULT_GOAL_WINDOWS
) -> TaskGoal | None:
    """Soll-Ist der Aufgabe; ohne „höchstens n-mal …“ gibt es kein Soll.

    Die Fenster schließen lückenlos aneinander an (je `every` Perioden): das erste endet mit der
    laufenden Periode, die übrigen sind abgeschlossene frühere Fenster.
    """
    rule = task.frequency
    if not isinstance(rule, MaxPerPeriod):
        return None
    mine = [
        (local_date(started, now), item.status in DONE_STATUSES)
        for item, started in placed
        if item.task_id == task.id
    ]
    first = window_start(rule.period, rule.every, now)
    result: list[GoalWindow] = []
    for back in range(windows):
        start = shift_periods(rule.period, first, -back * rule.every)
        end = shift_periods(rule.period, start, rule.every) - _DAY
        result.append(_window(start, end, mine, now.date()))
    return TaskGoal(task.id, rule.count, rule.period, rule.every, tuple(result))


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
    tasks: Mapping[TaskId, Task],
    placed: Iterable[Placed],
    now: dt.datetime,
    windows: int = DEFAULT_GOAL_WINDOWS,
) -> tuple[TaskGoal, ...]:
    """Soll-Ist aller Aufgaben mit „höchstens n-mal in x Zeiträumen“."""
    placed = tuple(placed)
    found = (task_goal(task, placed, now, windows) for task in tasks.values())
    return tuple(goal for goal in found if goal is not None)
