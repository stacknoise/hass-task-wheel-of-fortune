import random

from custom_components.task_wheel.domain.draw.engine import DrawEngine
from custom_components.task_wheel.domain.draw.matching import safe_winners, unplaceable
from custom_components.task_wheel.domain.draw.weighting import UniformWeighting

from ..factories import task
from .helpers import FixedRandom, draw_round, make_context, make_person, max_matching


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
        results = draw_round(engine, tasks, ctx)
        winners = [r.winner_id for r in results if r.winner_id]
        assert len(winners) == len(set(winners))
        best = max_matching([t.allowed & frozenset(people) or frozenset(people) for t in tasks])
        assert len(winners) == best


def test_regression_last_person_with_previous_task_still_gets_it():
    ctx = make_context([make_person("a"), make_person("b")], last_holders={"t1": "b", "t2": "a"})
    tasks = [task(id="t1", allowed=fs("a", "b")), task(id="t2", allowed=fs("a", "b"))]
    for value in (0.0, 0.99):
        results = draw_round(DrawEngine(UniformWeighting(), FixedRandom(value)), tasks, ctx)
        assert all(r.winner_id for r in results)


def test_unplaceable_is_empty_when_everything_can_be_assigned():
    assert unplaceable([fs("a", "b"), fs("a")]) == frozenset()
    assert unplaceable([]) == frozenset()


def test_unplaceable_names_the_tasks_competing_for_too_few_people():
    # t0 und t1 wollen nur "a"; t2 hat genug andere Personen und ist nie betroffen
    assert unplaceable([fs("a"), fs("a"), fs("b", "c")]) == {0, 1}


def test_unplaceable_includes_tasks_nobody_can_do():
    assert unplaceable([fs(), fs("a")]) == {0}


def test_unplaceable_follows_alternating_paths():
    # t2 braucht "b", das t1 belegen könnte; t0 braucht "a", t1 nimmt "a" oder "b"
    assert unplaceable([fs("a"), fs("a", "b"), fs("b")]) == {0, 1, 2}
