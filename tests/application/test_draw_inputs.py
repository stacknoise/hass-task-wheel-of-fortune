"""Eingaben einer Runde: Punkte im Fenster, Zuteilungszeitpunkte, Aufgabenauswahl."""

import datetime as dt

from custom_components.task_wheel.application.draw_inputs import (
    assigned_times,
    build_context,
    due_tasks,
    recent_assignments,
    window_points,
)
from custom_components.task_wheel.const.limits import RECENT_HISTORY_DAYS
from custom_components.task_wheel.domain.enums import AssignmentStatus as S

from ..domain import factories as f
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
