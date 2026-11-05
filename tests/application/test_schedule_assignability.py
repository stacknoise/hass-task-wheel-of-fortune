"""Zeitpläne speichern: Aufgaben „in jeder Runde“ müssen an verschiedene Personen gehen können."""

import pytest

from custom_components.task_wheel.application.config_service import ConfigService
from custom_components.task_wheel.domain.enums import RoundOrigin
from custom_components.task_wheel.domain.errors import ValidationError
from custom_components.task_wheel.domain.models import EveryRound, WeeklyDaysAbsence

from ..domain import factories as f
from .world import World

NOW = f.NOW
SCHEDULE = {"name": "Neu", "trigger": {"kind": "manual"}, "task_ids": ["t3", "t4"]}


def _service(world: World) -> ConfigService:
    return ConfigService(
        world.config, world.history, world.schedules, world.draws, lambda _target: None
    )


def _world_with(*tasks) -> World:
    world = World()
    for task in tasks:
        world.config.put_task(task)
    return world


def _only(ident: str, *persons: str, **overrides: object):
    fields = {"frequency": EveryRound(), **overrides}
    return f.task(id=ident, name=ident, allowed=frozenset(persons), **fields)


def test_saving_is_refused_when_every_round_tasks_need_the_same_person():
    world = _world_with(_only("t3", "p1"), _only("t4", "p1"))
    with pytest.raises(ValidationError) as caught:
        _service(world).create_schedule(SCHEDULE, NOW)
    assert (caught.value.field, caught.value.key) == ("task_ids", "schedule_tasks_unassignable")
    assert caught.value.placeholders == {"tasks": "t3, t4"}


def test_updating_a_schedule_is_checked_too():
    world = _world_with(_only("t3", "p1"), _only("t4", "p1"))
    schedule = world.put_schedule(task_ids=("t3",))
    with pytest.raises(ValidationError):
        _service(world).update_schedule(schedule.id, {"task_ids": ["t3", "t4"]}, NOW)


def test_enough_suitable_persons_allow_saving():
    world = _world_with(_only("t3", "p1"), _only("t4", "p1", "p2"))
    created = _service(world).create_schedule(SCHEDULE, NOW)
    assert created.task_ids == ("t3", "t4")


def test_absent_persons_do_not_block_saving_and_the_draw_picks_at_random():
    world = World(0.9, 0.1)
    world.config.put_person(
        f.person(
            id="p2",
            slug="p2",
            name="p2",
            absences=(WeeklyDaysAbsence(weekdays=frozenset(range(7))),),
        )
    )
    world.config.put_task(_only("t3", "p1", "p2"))
    world.config.put_task(_only("t4", "p1", "p2"))
    created = _service(world).create_schedule(SCHEDULE, NOW)
    round_ = world.draws.draw(created.id, RoundOrigin.MANUAL, NOW)
    assert len(round_.assignments) == 1
