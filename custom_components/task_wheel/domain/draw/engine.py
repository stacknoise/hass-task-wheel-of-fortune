"""Ziehungs-Engine: Kandidaten, Gewichte, Zufall (KONZEPT §5.1 bis §5.3)."""

import datetime as dt
import secrets
from bisect import bisect_right
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from itertools import accumulate

from ..models import Person, Task
from ..types import PersonId, TaskId
from .candidates import CandidateSelector
from .types import (
    CandidateSelection,
    DrawContext,
    RandomSource,
    Segment,
    TaskDraw,
    WeightInput,
)
from .weighting import Weighting

_DAY = dt.timedelta(days=1)


def secure_random() -> RandomSource:
    """Kryptografisch sicherer Zufall für den Betrieb (Ergebnis bestimmt nur das Backend)."""
    return secrets.SystemRandom()


def capacities(context: DrawContext) -> dict[PersonId, float]:
    """Kapazität je Person im Fairness-Fenster: Belastungsfaktor mal anwesende Tage."""
    end = context.now.date()
    start = end - (context.fairness_window_days - 1) * _DAY
    return {
        pid: person.load.factor * context.availability[pid].present_day_count(start, end)
        for pid, person in context.persons.items()
    }


def build_segments(weights: Sequence[float], candidates: Sequence[Person]) -> tuple[Segment, ...]:
    """Normiert die Gewichte zu Chancen (Summe 1) und bildet die Segmente des Rads."""
    total = sum(weights)
    return tuple(
        Segment(person.id, weight, weight / total)
        for person, weight in zip(candidates, weights, strict=True)
    )


class DrawEngine:
    """Zieht je Aufgabe eine Person; der Zufall wird injiziert."""

    def __init__(
        self,
        weighting: Weighting,
        rng: RandomSource,
        selector: CandidateSelector | None = None,
    ) -> None:
        """Übernimmt Gewichtung, Zufallsquelle und Filterkette."""
        self._weighting = weighting
        self._rng = rng
        self._selector = selector or CandidateSelector()

    def draw_round(self, tasks: Iterable[Task], context: DrawContext) -> tuple[TaskDraw, ...]:
        """Zieht für alle Aufgaben nacheinander.

        Punkte, die in dieser Runde vergeben wurden, zählen sofort mit, damit nicht alle Aufgaben
        an dieselbe Person gehen. Die Kapazitäten werden einmal je Runde berechnet.
        """
        capacity = capacities(context)
        points: dict[PersonId, float] = dict(context.points)
        last_holders = dict(context.last_holders)
        round_holders = set(context.round_holders)
        results: list[TaskDraw] = []
        ordered = tuple(tasks)
        reach: dict[TaskId, frozenset[PersonId]] = {}
        for index, task in enumerate(ordered):
            current = DrawContext(
                context.now,
                context.persons,
                context.availability,
                points,
                last_holders,
                context.fairness_window_days,
                frozenset(round_holders),
            )
            result = self._draw_task(
                task, current, capacity, points, rest=ordered[index + 1 :], reach=reach
            )
            if result.winner_id is not None:
                points[result.winner_id] = points.get(result.winner_id, 0) + task.points
                last_holders[task.id] = result.winner_id
                round_holders.add(result.winner_id)
            results.append(result)
        return tuple(results)

    def draw_task(self, task: Task, context: DrawContext, rest: Sequence[Task] = ()) -> TaskDraw:
        """Zieht für eine einzelne Aufgabe; `rest` sind die noch folgenden Aufgaben der Runde."""
        return self._draw_task(task, context, capacities(context), context.points, rest=rest)

    def preview_task(self, task: Task, context: DrawContext, rest: Sequence[Task] = ()) -> TaskDraw:
        """Das Rad für eine Aufgabe ohne Ziehung: Segmente und Ausschlüsse, aber kein Gewinner.

        Stimmt mit dem Rad der späteren Ziehung überein, solange sich der Stand nicht ändert.
        """
        selection, segments, _weights = self._wheel(
            task, context, capacities(context), context.points, rest=rest
        )
        return TaskDraw(task.id, None, 0.0, segments, selection.exclusions)

    def _wheel(
        self,
        task: Task,
        context: DrawContext,
        capacity: Mapping[PersonId, float],
        points: Mapping[PersonId, float],
        *,
        rest: Sequence[Task] = (),
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None = None,
    ) -> tuple[CandidateSelection, tuple[Segment, ...], Sequence[float]]:
        """Filtert und gewichtet: Kandidaten, Segmente des Rads und deren Gewichte."""
        selection = self._selector.select(task, context, rest, reach)
        if not selection.candidates:
            return selection, (), ()
        inputs = [
            WeightInput(p.id, capacity[p.id], points.get(p.id, 0)) for p in selection.candidates
        ]
        weights = self._weighting.weigh(inputs)
        return selection, build_segments(weights, selection.candidates), weights

    def _draw_task(
        self,
        task: Task,
        context: DrawContext,
        capacity: Mapping[PersonId, float],
        points: Mapping[PersonId, float],
        *,
        rest: Sequence[Task] = (),
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None = None,
    ) -> TaskDraw:
        """Filtert, gewichtet und zieht; ohne Kandidaten bleibt die Aufgabe unverteilt."""
        selection, segments, weights = self._wheel(
            task, context, capacity, points, rest=rest, reach=reach
        )
        if not segments:
            return TaskDraw(task.id, None, 0.0, (), selection.exclusions)
        winner = self._pick(segments, weights)
        return self._result(task, selection, segments, winner)

    def _pick(self, segments: Sequence[Segment], weights: Sequence[float]) -> Segment:
        """Wählt ein Segment anteilig zum Gewicht (kumulierte Summen, binäre Suche)."""
        cumulative = list(accumulate(weights))
        target = self._rng.random() * cumulative[-1]
        index = min(bisect_right(cumulative, target), len(segments) - 1)
        return segments[index]

    @staticmethod
    def _result(
        task: Task,
        selection: CandidateSelection,
        segments: Sequence[Segment],
        winner: Segment,
    ) -> TaskDraw:
        """Fasst Gewinner, Chance, Segmente und Ausschlüsse zusammen."""
        return TaskDraw(task.id, winner.person_id, winner.chance, segments, selection.exclusions)
