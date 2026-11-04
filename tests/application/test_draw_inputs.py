"""Eingaben einer Runde: Punkte im Fenster, Zuteilungszeitpunkte, Aufgabenauswahl."""

import datetime as dt

from custom_components.task_wheel.application.draw_inputs import (
    assigned_times,
    build_context,
    due_tasks,
    limit_to_participants,
    recent_assignments,
    window_points,
)
from custom_components.task_wheel.const.limits import RECENT_HISTORY_DAYS
from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.enums import Period
from custom_components.task_wheel.domain.models import MaxPerPeriod

from ..domain import factories as f
from ..domain.draw.helpers import FixedRandom
from .world import DAY, World

NOW = f.NOW


def add_round(
    world: World, ident: str, started: dt.datetime, *assignments, schedule_id: str = "s1"
) -> None:
    world.history.put_round(
        f.finished_round(
            id=ident,
            schedule_id=schedule_id,
            started_at=started,
            finished_at=started,
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


def test_assignments_before_the_fairness_window_do_not_count_but_still_serve_frequency():
    world = World(fairness_window_days=30)
    add_round(world, "r1", NOW - 40 * DAY, item("a1", "r1"))
    recent = recent_assignments(world.history, NOW)
    assert window_points(recent, world.config.settings, NOW) == {}
    assert assigned_times(recent) == {"t1": [NOW - 40 * DAY]}


def test_history_older_than_the_lookback_is_left_out():
    world = World()
    add_round(world, "r1", NOW - (RECENT_HISTORY_DAYS + 1) * DAY, item("a1", "r1"))
    assert recent_assignments(world.history, NOW) == ()


def test_context_holds_last_holder_availability_and_a_copy_of_the_persons():
    world = World()
    add_round(world, "r1", NOW - DAY, item("a1", "r1", person_id="p2"))
    recent = recent_assignments(world.history, NOW)
    context = build_context(world.config, world.history, recent, NOW)
    assert context.last_holders == {"t1": "p2"}
    assert set(context.availability) == {"p1", "p2"}
    world.config.remove_person("p2")
    assert set(context.persons) == {"p1", "p2"}


def test_due_tasks_keep_the_order_of_the_schedule():
    world = World()
    schedule = world.put_schedule(task_ids=("t2", "t1"))
    tasks = due_tasks(world.config, schedule, (), NOW)
    assert [t.id for t in tasks] == ["t2", "t1"]
    assert all(t.respect_absence for t in tasks)


def test_round_is_limited_to_as_many_randomly_picked_tasks_as_persons_take_part():
    world = World()
    world.config.put_task(f.task(id="t3", name="t3"))
    schedule = world.put_schedule(task_ids=("t1", "t2", "t3"))
    context = build_context(world.config, world.history, (), NOW)
    tasks = due_tasks(world.config, schedule, (), NOW)
    # zwei Personen, drei Aufgaben: die beiden kleinsten Zufallszahlen (t3, t1) bleiben,
    # in Zeitplanreihenfolge
    picked = limit_to_participants(tasks, context, FixedRandom(0.5, 0.9, 0.1))
    assert [t.id for t in picked] == ["t1", "t3"]


def test_round_keeps_all_tasks_when_enough_persons_take_part():
    world = World()
    schedule = world.put_schedule(task_ids=("t1", "t2"))
    context = build_context(world.config, world.history, (), NOW)
    tasks = due_tasks(world.config, schedule, (), NOW)
    assert limit_to_participants(tasks, context, FixedRandom(0.5)) == tasks


def _daily(ident: str):
    return f.task(id=ident, name=ident, frequency=MaxPerPeriod(count=1, period=Period.DAY, every=1))


def test_daily_tasks_are_always_part_of_a_limited_round():
    world = World()
    world.config.put_task(_daily("t3"))
    world.config.put_task(f.task(id="t4", name="t4"))
    schedule = world.put_schedule(task_ids=("t1", "t2", "t3", "t4"))
    context = build_context(world.config, world.history, (), NOW)
    tasks = due_tasks(world.config, schedule, (), NOW)
    # zwei Personen: t3 (täglich) ist gesetzt, t2 hat unter den übrigen die kleinste Zufallszahl
    picked = limit_to_participants(tasks, context, FixedRandom(0.9, 0.1, 0.5, 0.7))
    assert [t.id for t in picked] == ["t2", "t3"]


def test_more_daily_tasks_than_persons_are_picked_randomly_among_themselves():
    world = World()
    for ident in ("t3", "t4"):
        world.config.put_task(_daily(ident))
    world.config.put_task(_daily("t5"))
    schedule = world.put_schedule(task_ids=("t3", "t4", "t5", "t1"))
    context = build_context(world.config, world.history, (), NOW)
    tasks = due_tasks(world.config, schedule, (), NOW)
    picked = limit_to_participants(tasks, context, FixedRandom(0.5, 0.9, 0.1))
    assert [t.id for t in picked] == ["t3", "t5"]


def test_task_over_several_days_is_not_daily():
    weekly = f.task(frequency=MaxPerPeriod(count=1, period=Period.DAY, every=2))
    assert not weekly.is_daily
