"""Fälligkeit der Aufgaben einer Auslosung: Abstand ausgleichen, Überlast und Lücken per Zufall.

Jede Aufgabe mit „mindestens n-mal je Lauf“ hat einen Zielabstand von `Auslosungen je Lauf ÷ n`
Auslosungen. Sie ist fällig, sobald seit ihrer letzten Zuteilung (auch aus dem Lauf davor, der
Zähler wird an der Grenze nicht zurückgesetzt) mindestens der abgerundete Zielabstand vergangen
ist. Eine Aufgabe ohne Vorgeschichte ist mit Wahrscheinlichkeit „1 ÷ Zielabstand“ fällig (zufällige
Phase, damit neue Aufgaben nicht zusammenfallen). „Jede Auslosung“ ist immer dabei und wird nicht
ausgeglichen.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ...const.defaults import GAP_WEIGHT_FLOOR
from ...const.keys import NOTE_DEFERRED, NOTE_FILLED, NOTE_NOT_DUE
from ..draw.types import RandomSource, TaskNote
from ..models import Schedule, ScheduleEntry, Task
from ..types import TaskId


@dataclass(slots=True, frozen=True)
class TaskTiming:
    """Zielabstand einer Aufgabe und was seit ihrer letzten Zuteilung vergangen ist."""

    spacing: float
    elapsed: int | None

    @property
    def minimum_gap(self) -> int:
        """Kleinster Abstand in Auslosungen, ab dem die Aufgabe fällig ist (abgerundet)."""
        return max(1, math.floor(self.spacing))

    @property
    def arrears(self) -> int:
        """Verzug: um wie viele Auslosungen der Mindestabstand überschritten ist (0 = pünktlich)."""
        return 0 if self.elapsed is None else max(0, self.elapsed - self.minimum_gap)

    @property
    def progress(self) -> float | None:
        """Fortschritt: verstrichener Abstand ÷ Zielabstand (`None` ohne Vorgeschichte)."""
        return None if self.elapsed is None else self.elapsed / self.spacing


@dataclass(slots=True, frozen=True)
class DueRanking:
    """Die Aufgaben einer Auslosung in Reihenfolge ihrer Wichtigkeit.

    `required` sind die „jede Auslosung“-Aufgaben (zufällige Reihenfolge, falls nicht alle
    vergebbar sind), `due` die fälligen (nach Verzug zufällig
    gewichtet), `spare` die noch nicht fälligen (nach Fortschritt zufällig gewichtet; sie füllen
    nur eine Lücke).
    """

    required: tuple[Task, ...]
    due: tuple[Task, ...]
    spare: tuple[Task, ...]

    @property
    def priority(self) -> tuple[Task, ...]:
        """Die Aufgaben, die in die Auswahl kommen: „jede Auslosung“ zuerst, dann die fälligen."""
        return (*self.required, *self.due)


def timing_of(
    schedule: Schedule, entry: ScheduleEntry, last_periods: Mapping[TaskId, int], period: int
) -> TaskTiming:
    """Zielabstand und verstrichene Auslosungen der Aufgabe vor der Periode `period`."""
    spacing = schedule.draws_per_run / entry.min_count
    last = last_periods.get(entry.task_id)
    return TaskTiming(spacing, None if last is None else period - last)


def _weighted_order(items: Sequence[tuple[Task, float]], rng: RandomSource) -> tuple[Task, ...]:
    """Zufällige Reihenfolge ohne Zurücklegen; ein größeres Gewicht kommt eher nach vorn."""
    keyed = [(rng.random() ** (1 / weight), task) for task, weight in items]
    return tuple(task for _, task in sorted(keyed, key=lambda pair: -pair[0]))


def _is_due(timing: TaskTiming, rng: RandomSource) -> bool:
    """Fälligkeit; ohne Vorgeschichte entscheidet der Zufall (zufällige Phase)."""
    if timing.elapsed is None:
        return rng.random() < 1 / timing.minimum_gap
    return timing.elapsed >= timing.minimum_gap


def rank_tasks(
    schedule: Schedule,
    tasks: Sequence[Task],
    last_periods: Mapping[TaskId, int],
    period: int,
    rng: RandomSource,
) -> DueRanking:
    """Ordnet die Aufgaben des Zeitplans für die Auslosung der Periode `period`.

    Aufgaben, die nicht (mehr) im Zeitplan stehen, sind nicht dabei.
    """
    required: list[tuple[Task, float]] = []
    due: list[tuple[Task, float]] = []
    spare: list[tuple[Task, float]] = []
    for task in tasks:
        entry = schedule.entry_for(task.id)
        if entry is None:
            continue
        if entry.every_draw:
            required.append((task, 1.0))
            continue
        timing = timing_of(schedule, entry, last_periods, period)
        if _is_due(timing, rng):
            due.append((task, 1 + timing.arrears))
        else:
            spare.append((task, max(timing.progress or rng.random(), GAP_WEIGHT_FLOOR)))
    return DueRanking(
        _weighted_order(required, rng), _weighted_order(due, rng), _weighted_order(spare, rng)
    )


def task_notes(ranking: DueRanking, picked: Sequence[Task]) -> tuple[TaskNote, ...]:
    """Die Vermerke zu allen Aufgaben, die nicht ganz regulär ausgelost wurden."""
    chosen = {task.id for task in picked}
    notes = [TaskNote(task.id, NOTE_DEFERRED) for task in ranking.priority if task.id not in chosen]
    for task in ranking.spare:
        reason = NOTE_FILLED if task.id in chosen else NOTE_NOT_DUE
        notes.append(TaskNote(task.id, reason))
    return tuple(notes)
