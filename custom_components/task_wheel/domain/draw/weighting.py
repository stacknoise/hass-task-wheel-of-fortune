"""Gewichtung der Kandidaten (Strategy) und Fabrik (KONZEPT §5.3)."""

import math
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Protocol

from ...const.defaults import FAIRNESS_DAMPING, UNIFORM_WEIGHT, WEIGHT_MAX, WEIGHT_MIN
from ..enums import WeightingKind
from ..errors import UnknownKindError
from .types import WeightInput

_FIELD_WEIGHTING = "weighting"


class Weighting(Protocol):
    """Bestimmt je Kandidat ein positives Gewicht (gleiche Reihenfolge wie die Eingabe)."""

    def weigh(self, inputs: Sequence[WeightInput]) -> tuple[float, ...]:
        """Liefert die Gewichte; jedes liegt über 0."""
        ...


class UniformWeighting:
    """Alle Kandidaten haben dieselbe Chance."""

    def weigh(self, inputs: Sequence[WeightInput]) -> tuple[float, ...]:
        """Gleiches Gewicht für alle."""
        return (UNIFORM_WEIGHT,) * len(inputs)


class FairnessWeighting:
    """Wer im Verhältnis zum fairen Anteil weniger Punkte hatte, bekommt ein größeres Segment.

    `f = Kapazität / Σ Kapazität`, `a = Punkte / Σ Punkte` (ohne Punkte: `a = f`),
    `w = f * exp(k * (f - a) / f)`, begrenzt auf `[WEIGHT_MIN, WEIGHT_MAX]`.
    """

    def __init__(self, damping: float = FAIRNESS_DAMPING) -> None:
        """Merkt sich die Dämpfung `k`."""
        self._damping = damping

    def weigh(self, inputs: Sequence[WeightInput]) -> tuple[float, ...]:
        """Gewichte nach der Fairness-Formel; ohne Kapazität gleichverteilt."""
        total_capacity = math.fsum(item.capacity for item in inputs)
        if total_capacity <= 0:
            return UniformWeighting().weigh(inputs)
        total_points = math.fsum(item.points for item in inputs)
        return tuple(self._weight(item, total_capacity, total_points) for item in inputs)

    def _weight(self, item: WeightInput, total_capacity: float, total_points: float) -> float:
        """Gewicht einer Person, begrenzt auf den erlaubten Bereich."""
        fair = item.capacity / total_capacity
        if fair <= 0:
            return WEIGHT_MIN
        actual = item.points / total_points if total_points > 0 else fair
        raw = fair * math.exp(self._damping * (fair - actual) / fair)
        return min(max(raw, WEIGHT_MIN), WEIGHT_MAX)


type WeightingBuilder = Callable[[], Weighting]

_BUILDERS: Mapping[WeightingKind, WeightingBuilder] = MappingProxyType(
    {
        WeightingKind.FAIRNESS: FairnessWeighting,
        WeightingKind.UNIFORM: UniformWeighting,
    }
)


class WeightingFactory:
    """Erzeugt die Gewichtung zur Einstellung."""

    @staticmethod
    def create(kind: WeightingKind) -> Weighting:
        """Liefert die Strategie zur Art.

        Raises:
            UnknownKindError: Die Art ist nicht registriert.
        """
        builder = _BUILDERS.get(kind)
        if builder is None:
            raise UnknownKindError(_FIELD_WEIGHTING, kind)
        return builder()
