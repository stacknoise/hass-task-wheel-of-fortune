import dataclasses
import random
import secrets
import time

import pytest

from custom_components.task_wheel.domain.draw.engine import (
    DrawEngine,
    capacities,
    secure_random,
)
from custom_components.task_wheel.domain.draw.weighting import (
    FairnessWeighting,
    UniformWeighting,
)
from custom_components.task_wheel.domain.enums import Load
from custom_components.task_wheel.domain.models import WeeklyDaysAbsence

from ..factories import task
from .helpers import FixedRandom, make_context, make_person


def uniform(rng):
    return DrawEngine(UniformWeighting(), rng)


def test_production_rng_is_system_random():
    assert isinstance(secure_random(), secrets.SystemRandom)


def test_fixed_rng_picks_segment_by_cumulative_weight():
    ctx = make_context([make_person("a"), make_person("b")])
    t = task(allowed=frozenset({"a", "b"}))
    assert uniform(FixedRandom(0.0)).draw_task(t, ctx).winner_id == "a"
    assert uniform(FixedRandom(0.49)).draw_task(t, ctx).winner_id == "a"
    assert uniform(FixedRandom(0.5)).draw_task(t, ctx).winner_id == "b"
    assert uniform(FixedRandom(0.9999999)).draw_task(t, ctx).winner_id == "b"


def test_segments_sum_to_one_and_chance_matches_winner():
    ctx = make_context([make_person("a"), make_person("b"), make_person("c")])
    result = uniform(FixedRandom(0.5)).draw_task(task(allowed=frozenset({"a", "b", "c"})), ctx)
    assert sum(s.chance for s in result.segments) == pytest.approx(1.0)
    winner = next(s for s in result.segments if s.person_id == result.winner_id)
    assert result.chance == winner.chance
    assert result.distributable


def test_task_without_candidates_is_not_distributable():
    ctx = make_context([make_person("a", load=Load.PAUSED)])
    result = uniform(FixedRandom(0.1)).draw_task(task(allowed=frozenset({"a"})), ctx)
    assert not result.distributable
    assert result.winner_id is None
    assert not result.segments
    assert result.exclusions


def test_capacity_uses_load_and_presence():
    absent = WeeklyDaysAbsence(weekdays=frozenset({5, 6}))
    ctx = make_context(
        [
            make_person("full"),
            make_person("half", load=Load.HALF),
            make_person("away", absences=(absent,)),
            make_person("none", load=Load.PAUSED),
        ]
    )
    cap = capacities(ctx)
    assert cap["full"] == 30
    assert cap["half"] == 15
    assert cap["none"] == 0
    assert 20 < cap["away"] < 30


def test_points_assigned_in_round_count_immediately():
    ctx = make_context([make_person("a"), make_person("b")])
    tasks = [task(id=f"t{i}", allowed=frozenset({"a", "b"}), points=10) for i in range(2)]
    engine = DrawEngine(FairnessWeighting(), FixedRandom(0.0))
    first, second = engine.draw_round(tasks, ctx)
    assert first.winner_id == "a"
    chances = {s.person_id: s.chance for s in second.segments}
    assert chances["a"] < chances["b"]


def test_no_repeat_uses_winner_of_earlier_task_in_round():
    ctx = make_context([make_person("a"), make_person("b")])
    same = [task(id="t1", allowed=frozenset({"a", "b"}), no_repeat=True)] * 2
    first, second = uniform(FixedRandom(0.0)).draw_round(same, ctx)
    assert first.winner_id == "a"
    assert second.winner_id == "b"


def test_draw_round_does_not_mutate_context():
    ctx = make_context([make_person("a")], points={"a": 1})
    snapshot = dict(ctx.points)
    uniform(FixedRandom(0.0)).draw_round([task(allowed=frozenset({"a"}))], ctx)
    assert dict(ctx.points) == snapshot
    assert dataclasses.is_dataclass(ctx)


def test_statistical_chances_within_tolerance():
    """10 000 Ziehungen: beobachtete Häufigkeit liegt nahe an der berechneten Chance."""
    ctx = make_context(
        [make_person("a"), make_person("b", load=Load.HALF), make_person("c")],
        points={"a": 20, "b": 2, "c": 8},
    )
    t = task(allowed=frozenset({"a", "b", "c"}))
    engine = DrawEngine(FairnessWeighting(), random.Random(20261103))  # noqa: S311
    expected = {s.person_id: s.chance for s in engine.draw_task(t, ctx).segments}
    draws = 10_000
    wins = dict.fromkeys(expected, 0)
    for _ in range(draws):
        wins[engine.draw_task(t, ctx).winner_id] += 1
    for pid, chance in expected.items():
        assert wins[pid] / draws == pytest.approx(chance, abs=0.02)
    assert expected["b"] > expected["a"]


def test_round_runtime_is_measured_and_small():
    """Runde mit 10 Aufgaben x 6 Personen (Ziel < 5 ms, großzügige Obergrenze gegen Flackern)."""
    people = [make_person(f"p{i}") for i in range(6)]
    ctx = make_context(people)
    allowed = frozenset(p.id for p in people)
    tasks = [task(id=f"t{i}", allowed=allowed) for i in range(10)]
    engine = DrawEngine(FairnessWeighting(), random.Random(1))  # noqa: S311
    runs = 50
    start = time.perf_counter()
    for _ in range(runs):
        engine.draw_round(tasks, ctx)
    per_round_ms = (time.perf_counter() - start) / runs * 1000
    print(f"Laufzeit pro Runde: {per_round_ms:.2f} ms")  # noqa: T201
    assert per_round_ms < 50
