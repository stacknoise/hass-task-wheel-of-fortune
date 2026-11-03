import random

from custom_components.task_wheel.domain.draw.engine import DrawEngine
from custom_components.task_wheel.domain.draw.matching import max_matching, safe_winners
from custom_components.task_wheel.domain.draw.weighting import UniformWeighting

from ..factories import task
from .helpers import FixedRandom, make_context, make_person


def fs(*ids):
    return frozenset(ids)


def test_max_matching_uses_augmenting_paths():
    assert max_matching([fs("a", "b"), fs("a")]) == 2
    assert max_matching([fs("a"), fs("a")]) == 1
    assert max_matching([]) == 0


def test_safe_winners_keep_the_rest_solvable():
    assert safe_winners(fs("a", "b"), [fs("a")]) == fs("b")
    assert safe_winners(fs("a", "b"), [fs("a", "b")]) == fs("a", "b")
    assert safe_winners(fs("a"), [fs("a")]) == fs("a")


def test_every_person_gets_a_task_for_any_draw_when_tasks_cover_people():
    """Zufällige Fälle: Wird alles verteilt, was verteilbar ist, egal wie gezogen wird."""
    rnd = random.Random(7)  # noqa: S311
    ids = ["a", "b", "c", "d"]
    for _ in range(300):
        people = ids[: rnd.randint(2, 4)]
        tasks = [
            task(
                id=f"t{i}",
                allowed=frozenset(rnd.sample(people, rnd.randint(1, len(people)))),
                no_repeat=True,
            )
            for i in range(rnd.randint(1, 5))
        ]
        holders = {t.id: rnd.choice(people) for t in tasks}
        ctx = make_context([make_person(p) for p in people], last_holders=holders)
        engine = DrawEngine(UniformWeighting(), random.Random(rnd.random()))  # noqa: S311
        results = engine.draw_round(tasks, ctx)
        winners = [r.winner_id for r in results if r.winner_id]
        assert len(winners) == len(set(winners))
        best = max_matching([t.allowed & frozenset(people) or frozenset(people) for t in tasks])
        assert len(winners) == best


def test_regression_last_person_with_previous_task_still_gets_it():
    ctx = make_context([make_person("a"), make_person("b")], last_holders={"t1": "b", "t2": "a"})
    tasks = [task(id="t1", allowed=fs("a", "b")), task(id="t2", allowed=fs("a", "b"))]
    for value in (0.0, 0.99):
        results = DrawEngine(UniformWeighting(), FixedRandom(value)).draw_round(tasks, ctx)
        assert all(r.winner_id for r in results)
