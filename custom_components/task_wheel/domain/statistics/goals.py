"""Erreichungsgrad der Zeitpläne: Soll aus „höchstens n-mal in x Zeiträumen“ gegen das Erledigte."""

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ..models import Assignment, MaxPerPeriod, Schedule, Task
from ..rules.periods import count_since, window_start
from ..status import DONE_STATUSES
from ..types import ScheduleId, TaskId

type Placed = tuple[Assignment, dt.datetime]


@dataclass(slots=True, frozen=True)
class TaskGoal:
    """Soll und Stand einer Aufgabe im aktuellen Fenster ihrer Häufigkeitsregel."""

    task_id: TaskId
    target: int
    assigned: int
    done: int

    @property
    def reached(self) -> int:
        """Erledigte Zuteilungen, höchstens so viele wie das Soll."""
        return min(self.done, self.target)


@dataclass(slots=True, frozen=True)
class ScheduleGoal:
    """Erreichungsgrad eines Zeitplans über seine Aufgaben mit Soll."""

    schedule_id: ScheduleId
    tasks: tuple[TaskGoal, ...]

    @property
    def target(self) -> int:
        """Summe der Soll-Werte."""
        return sum(goal.target for goal in self.tasks)

    @property
    def reached(self) -> int:
        """Summe der erreichten (erledigten, gedeckelten) Zuteilungen."""
        return sum(goal.reached for goal in self.tasks)

    @property
    def rate(self) -> float:
        """Erreichungsgrad 0 bis 1 (ein Zeitplan in der Liste hat immer ein Soll)."""
        return self.reached / self.target


def task_goal(task: Task, placed: Iterable[Placed], now: dt.datetime) -> TaskGoal | None:
    """Stand der Aufgabe im Fenster ihrer Regel; ohne „höchstens n-mal …“ gibt es kein Soll."""
    rule = task.frequency
    if not isinstance(rule, MaxPerPeriod):
        return None
    start = window_start(rule.period, rule.every, now)
    mine = [(item, started) for item, started in placed if item.task_id == task.id]
    done = [started for item, started in mine if item.status in DONE_STATUSES]
    return TaskGoal(
        task.id,
        rule.count,
        count_since(start, (started for _item, started in mine), now),
        count_since(start, done, now),
    )


def build_goals(
    schedules: Iterable[Schedule],
    tasks: Mapping[TaskId, Task],
    placed: Iterable[Placed],
    now: dt.datetime,
) -> tuple[ScheduleGoal, ...]:
    """Erreichungsgrad je aktivem Zeitplan mit mindestens einer Aufgabe mit Soll."""
    placed = tuple(placed)
    goals: list[ScheduleGoal] = []
    for schedule in schedules:
        if schedule.archived:
            continue
        found = (tasks.get(task_id) for task_id in schedule.task_ids)
        per_task = tuple(
            goal for task in found if task and (goal := task_goal(task, placed, now)) is not None
        )
        if per_task:
            goals.append(ScheduleGoal(schedule.id, per_task))
    return tuple(goals)
