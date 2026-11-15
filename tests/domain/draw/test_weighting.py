import math

import pytest

from custom_components.task_wheel.const.defaults import WEIGHT_MAX, WEIGHT_MIN
from custom_components.task_wheel.domain.draw.types import WeightInput
from custom_components.task_wheel.domain.draw.weighting import (
    FairnessWeighting,
    UniformWeighting,
    WeightingFactory,
)
from custom_components.task_wheel.domain.enums import WeightingKind
from custom_components.task_wheel.domain.errors import UnknownKindError


def inputs(*rows):
    return [WeightInput(f"p{i}", cap, pts) for i, (cap, pts) in enumerate(rows)]


def test_uniform_gives_equal_weights():
    assert UniformWeighting().weigh(inputs((1, 0), (5, 9))) == (1.0, 1.0)


def test_fairness_without_points_gives_everyone_the_same_weight_whatever_the_capacity():
    weights = FairnessWeighting().weigh(inputs((10, 0), (30, 0), (1, 0)))
    assert weights[1] == pytest.approx(weights[0]) == pytest.approx(weights[2])


def test_capacity_counts_only_through_the_deviation_from_the_fair_share():
    # gleiche Abweichung (halber fairer Anteil an Punkten) bei sehr verschiedener Kapazität
    weights = FairnessWeighting().weigh(inputs((10, 1), (30, 3), (60, 6)))
    assert weights[0] == pytest.approx(weights[1]) == pytest.approx(weights[2])


def test_fairness_favours_person_with_fewer_points():
    low, high = FairnessWeighting().weigh(inputs((10, 0), (10, 10)))
    assert low > high


def test_fairness_formula_for_known_values():
    f, a = 0.5, 0.25
    expected = math.exp(-a / f)
    weights = FairnessWeighting().weigh(inputs((1, 1), (1, 3)))
    assert weights[0] == pytest.approx(min(expected, WEIGHT_MAX))


def test_weights_are_clamped_and_positive():
    weights = FairnessWeighting().weigh(inputs((1, 0), (1000, 10_000), (0, 0)))
    assert all(WEIGHT_MIN <= w <= WEIGHT_MAX for w in weights)
    assert weights[2] == WEIGHT_MIN


def test_zero_capacity_everywhere_falls_back_to_uniform():
    assert FairnessWeighting().weigh(inputs((0, 3), (0, 1))) == (1.0, 1.0)


def test_factory_builds_both_kinds():
    assert isinstance(WeightingFactory.create(WeightingKind.FAIRNESS), FairnessWeighting)
    assert isinstance(WeightingFactory.create(WeightingKind.UNIFORM), UniformWeighting)


def test_factory_rejects_unknown_kind():
    with pytest.raises(UnknownKindError):
        WeightingFactory.create("nope")  # type: ignore[arg-type]
