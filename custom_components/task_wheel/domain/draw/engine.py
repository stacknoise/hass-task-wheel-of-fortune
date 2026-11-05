"""Ziehungs-Engine: Kandidaten, Gewichte, Zufall (KONZEPT §5.1 bis §5.3)."""

import secrets
from bisect import bisect_right
from collections.abc import Mapping, MutableMapping, Sequence
from itertools import accumulate

from ...const.limits import ONE_DAY
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


def secure_random() -> RandomSource:
    """Kryptografisch sicherer Zufall für den Betrieb (Ergebnis bestimmt nur das Backend)."""
    return secrets.SystemRandom()


def capacities(context: DrawContext) -> dict[PersonId, float]:
    """Kapazität je Person im Fairness-Fenster: Belastungsfaktor mal anwesende Tage."""
    end = context.now.date()
    start = end - (context.fairness_window_days - 1) * ONE_DAY
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

    def draw_task(
        self,
        task: Task,
        context: DrawContext,
        rest: Sequence[Task] = (),
        *,
        capacity: Mapping[PersonId, float] | None = None,
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None = None,
    ) -> TaskDraw:
        """Zieht für eine einzelne Aufgabe; `rest` sind die noch folgenden Aufgaben der Runde.

        `capacity` und `reach` kann der Aufrufer über eine ganze Runde teilen (sie ändern sich
        in einer Runde nicht); ohne sie rechnet die Engine selbst.
        """
        selection, segments, weights = self._wheel(task, context, rest, capacity, reach)
        if not segments:
            return TaskDraw(task.id, None, 0.0, (), selection.exclusions)
        winner = self._pick(segments, weights, {p.id for p in selection.candidates})
        return self._result(task, selection, segments, winner)

    def preview_task(
        self,
        task: Task,
        context: DrawContext,
        rest: Sequence[Task] = (),
        *,
        capacity: Mapping[PersonId, float] | None = None,
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None = None,
    ) -> TaskDraw:
        """Das Rad für eine Aufgabe ohne Ziehung: Segmente und Ausschlüsse, aber kein Gewinner.

        Stimmt mit dem Rad der späteren Ziehung überein, solange sich der Stand nicht ändert.
        """
        selection, segments, _weights = self._wheel(task, context, rest, capacity, reach)
        return TaskDraw(task.id, None, 0.0, segments, selection.exclusions)

    def _wheel(
        self,
        task: Task,
        context: DrawContext,
        rest: Sequence[Task],
        capacity: Mapping[PersonId, float] | None,
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None,
    ) -> tuple[CandidateSelection, tuple[Segment, ...], Sequence[float]]:
        """Filtert und gewichtet: Kandidaten, Segmente des Rads und deren Gewichte."""
        selection = self._selector.select(task, context, rest, reach)
        if not selection.candidates:
            return selection, (), ()
        shares = capacities(context) if capacity is None else capacity
        inputs = [
            WeightInput(p.id, shares[p.id], context.points.get(p.id, 0)) for p in selection.wheel
        ]
        weights = self._weighting.weigh(inputs)
        return selection, build_segments(weights, selection.wheel), weights

    def _pick(
        self, segments: Sequence[Segment], weights: Sequence[float], allowed: set[PersonId]
    ) -> Segment:
        """Wählt unter den erlaubten Segmenten eines anteilig zum Gewicht (kumulierte Summen)."""
        pool = [(s, w) for s, w in zip(segments, weights, strict=True) if s.person_id in allowed]
        cumulative = list(accumulate(w for _s, w in pool))
        target = self._rng.random() * cumulative[-1]
        return pool[min(bisect_right(cumulative, target), len(pool) - 1)][0]

    @staticmethod
    def _result(
        task: Task,
        selection: CandidateSelection,
        segments: Sequence[Segment],
        winner: Segment,
    ) -> TaskDraw:
        """Fasst Gewinner, Chance, Segmente und Ausschlüsse zusammen."""
        return TaskDraw(task.id, winner.person_id, winner.chance, segments, selection.exclusions)
