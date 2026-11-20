"""Eingaben einer Runde: Punkte im Fenster, letzte Perioden, Aufgabenauswahl."""

import datetime as dt

from custom_components.task_wheel.application.draw_inputs import (
    build_context,
    choose_tasks,
    last_periods,
    ranked_tasks,
    recent_assignments,
    shuffled,
    window_points,
)
from custom_components.task_wheel.const.limits import RECENT_HISTORY_DAYS
from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.plan.window import PeriodWindow

from ..domain import factories as f
from ..domain.draw.helpers import FixedRandom
from .world import DAY, World

NOW = f.NOW
WINDOW = PeriodWindow(NOW, NOW + 7 * DAY)


def add_round(
    world: World,
    ident: str,
    started: dt.datetime,
    *assignments,
    schedule_id: str = "s1",
    period: int = 0,
) -> None:
    world.history.put_round(
        f.finished_round(
            id=ident,
            schedule_id=schedule_id,
            started_at=started,
            finished_at=started,
            period_index=period,
            assignments=assignments,
        )
    )


def item(ident: str, round_id: str, **overrides: object):
    return f.assignment(id=ident, round_id=round_id, **overrides)


def test_window_points_weigh_open_full_and_finished_by_factor():
    world = World(late_points_factor=0.5, missed_points_factor=-1.0)
    add_round(
        world,
        "r1",
        NOW - DAY,
        item("a1", "r1", points=4),
        item("a2", "r1", points=4, status=S.LATE, done_at=NOW),
        item("a3", "r1", points=4, status=S.MISSED),
        item("a4", "r1", points=4, status=S.ON_TIME, done_at=NOW, person_id="p2"),
    )
    recent = recent_assignments(world.history, NOW)
    points = window_points(recent, world.config.settings, NOW)
    assert points == {"p1": 4 + 2 - 4, "p2": 4}


def test_assignments_before_the_fairness_window_do_not_count():
    world = World(fairness_window_days=30)
    add_round(world, "r1", NOW - 40 * DAY, item("a1", "r1"))
    recent = recent_assignments(world.history, NOW)
    assert window_points(recent, world.config.settings, NOW) == {}


def test_history_older_than_the_lookback_is_left_out():
    world = World()
    add_round(world, "r1", NOW - (RECENT_HISTORY_DAYS + 1) * DAY, item("a1", "r1"))
    assert recent_assignments(world.history, NOW) == ()


def test_context_holds_last_holder_availability_and_a_copy_of_the_persons():
    world = World()
    add_round(world, "r1", NOW - DAY, item("a1", "r1", person_id="p2"))
    recent = recent_assignments(world.history, NOW)
    context = build_context(world.config, world.history, recent, NOW, WINDOW)
    assert context.last_holders == {"t1": "p2"}
    assert set(context.availability) == {"p1", "p2"}
    world.config.remove_person("p2")
    assert set(context.persons) == {"p1", "p2"}


def _only(ident: str, *persons: str, **overrides: object):
    return f.task(id=ident, name=ident, allowed=frozenset(persons), **overrides)


def _ranking(world: World, schedule, rng, period: int = 5):
    return ranked_tasks(world.config, world.history, schedule, period, rng)


def test_last_periods_take_the_newest_period_per_task_of_that_schedule_only():
    world = World()
    add_round(world, "r1", NOW - 3 * DAY, item("a1", "r1"), period=2)
    add_round(world, "r2", NOW - DAY, item("a2", "r2", task_id="t2"), period=4)
    add_round(world, "r3", NOW, item("a3", "r3", schedule_id="s9"), period=9, schedule_id="s9")
    assert last_periods(world.history, "s1") == {"t1": 2, "t2": 4}


def test_ranking_orders_every_draw_before_due_and_keeps_the_schedule_order():
    world = World()
    for ident in ("t3", "t4"):
        world.config.put_task(f.task(id=ident, name=ident))
    entries = f.entries("t4") + f.entries("t3", every_draw=False) + f.entries("t1")
    schedule = world.put_schedule(entries=entries, run_days=30)
    add_round(world, "r1", NOW - DAY, item("a1", "r1", task_id="t3"), period=0)
    ranking = _ranking(world, schedule, FixedRandom(0.5), period=40)
    assert {t.id for t in ranking.required} == {"t4", "t1"}
    assert [t.id for t in ranking.due] == ["t3"]  # 40 Auslosungen her, Zielabstand 30
    assert all(t.respect_absence for t in ranking.priority)


def test_task_that_was_drawn_recently_is_not_due_but_spare_for_a_gap():
    world = World()
    schedule = world.put_schedule(entries=f.entries("t1", every_draw=False, min_count=2))
    add_round(world, "r1", NOW - DAY, item("a1", "r1"), period=4)
    ranking = _ranking(world, schedule, FixedRandom(0.5), period=5)
    assert ranking.due == ()
    assert [t.id for t in ranking.spare] == ["t1"]


def test_unknown_tasks_of_the_schedule_are_left_out():
    world = World()
    schedule = world.put_schedule(task_ids=("t1", "gone"))
    assert [t.id for t in _ranking(world, schedule, FixedRandom(0.5)).required] == ["t1"]


def test_skip_absent_off_ignores_absence():
    world = World()
    schedule = world.put_schedule(skip_absent=False)
    assert not any(t.respect_absence for t in _ranking(world, schedule, FixedRandom(0.5)).required)


def _context(world: World):
    return build_context(world.config, world.history, (), NOW, WINDOW)


def test_round_is_limited_to_as_many_tasks_as_persons_can_take():
    world = World()
    for ident in ("t3", "t4", "t5"):
        world.config.put_task(f.task(id=ident, name=ident))
    schedule = world.put_schedule(task_ids=("t3", "t4", "t5"))
    picked = choose_tasks(_ranking(world, schedule, FixedRandom(0.1, 0.5, 0.9)), _context(world))
    assert {t.id for t in picked} == {"t4", "t5"}  # zwei Personen: die größten Zufallszahlen


def test_every_draw_tasks_win_over_due_tasks():
    world = World()
    world.config.put_task(f.task(id="t3", name="t3"))
    entries = f.entries("t3", every_draw=False) + f.entries("t1", "t2")
    schedule = world.put_schedule(entries=entries)
    picked = choose_tasks(_ranking(world, schedule, FixedRandom(0.1), period=99), _context(world))
    assert [t.id for t in picked] == ["t1", "t2"]


def test_a_gap_is_filled_with_one_spare_task():
    world = World()
    schedule = world.put_schedule(entries=f.entries("t1", "t2", every_draw=False, min_count=1))
    add_round(world, "r1", NOW, item("a1", "r1"), item("a2", "r1", task_id="t2"), period=4)
    ranking = _ranking(world, schedule, FixedRandom(0.5))
    assert ranking.priority == ()
    assert len(choose_tasks(ranking, _context(world))) == 1


def test_tasks_nobody_can_do_are_not_part_of_the_round():
    world = World()
    world.config.put_task(_only("t3", "gone"))
    schedule = world.put_schedule(task_ids=("t3", "t1"))
    picked = choose_tasks(_ranking(world, schedule, FixedRandom(0.1)), _context(world))
    assert [t.id for t in picked] == ["t1"]


def test_tasks_that_only_one_person_may_do_never_land_in_a_round_together():
    world = World()
    for task in (_only("t3", "p1"), _only("t4", "p1")):
        world.config.put_task(task)
    schedule = world.put_schedule(task_ids=("t3", "t4", "t2"))
    picked = choose_tasks(_ranking(world, schedule, FixedRandom(0.1)), _context(world))
    assert len(picked) == 2
    assert {t.id for t in picked} & {"t3", "t4"} != {"t3", "t4"}


def test_overload_is_decided_by_weighted_chance():
    world = World()
    for ident in ("t3", "t4"):
        world.config.put_task(f.task(id=ident, name=ident))
    schedule = world.put_schedule(task_ids=("t3", "t4", "t1"))
    add_round(world, "r1", NOW, item("a1", "r1", task_id="t3"), period=0)
    # alle drei fällig, aber nur zwei Personen: die Zufallszahlen entscheiden
    ranking = _ranking(world, schedule, FixedRandom(0.99, 0.01, 0.5), period=60)
    assert len(choose_tasks(ranking, _context(world))) == 2


def test_shuffled_orders_the_tasks_by_their_random_numbers():
    tasks = (f.task(id="t1"), f.task(id="t2"), f.task(id="t3"))
    assert [t.id for t in shuffled(tasks, FixedRandom(0.5, 0.9, 0.1))] == ["t3", "t1", "t2"]
    assert [t.id for t in shuffled(tasks, FixedRandom(0.1, 0.5, 0.9))] == ["t1", "t2", "t3"]


def test_shuffled_keeps_all_tasks_and_handles_an_empty_round():
    tasks = (f.task(id="t1"), f.task(id="t2"))
    assert sorted(t.id for t in shuffled(tasks, FixedRandom(0.7, 0.2))) == ["t1", "t2"]
    assert shuffled((), FixedRandom(0.5)) == ()
