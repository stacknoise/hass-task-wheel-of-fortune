"""RoundService: Auslosung löschen und Statistik zurückrechnen."""

import datetime as dt

import pytest

from custom_components.task_wheel.application.round_service import RoundService
from custom_components.task_wheel.domain.errors import NotFoundError
from custom_components.task_wheel.domain.statistics.aggregate import recompute

from ..domain import factories as f
from .test_assignment_service import World, _open
from .world import RecordingEvents


def _service(world: World) -> tuple[RoundService, RecordingEvents]:
    events = RecordingEvents()
    return RoundService(world.history, world.statistics, events), events


def test_delete_removes_round_assignments_and_index() -> None:
    world = World()
    world.add_round(_open(), _open("a2", person_id="p2"))
    service, events = _service(world)
    removed = service.delete("r1")
    assert removed.id == "r1"
    assert "r1" not in world.history.rounds
    assert world.history.get_assignment("a1") is None
    assert world.history.open_assignments("p1") == ()
    assert events.deleted == [removed]


def test_delete_takes_done_points_out_of_the_statistics() -> None:
    world = World()
    world.add_round(_open(), _open("a2", person_id="p2"))
    world.statistics.record_round(world.history.rounds["r1"])
    world.assignments.complete("a1", f.NOW)
    service, _ = _service(world)
    service.delete("r1")
    assert dict(world.history.aggregates) == {}


def test_delete_keeps_other_rounds_in_the_statistics() -> None:
    world = World()
    world.add_round(_open(), started=f.NOW)
    later = f.NOW + dt.timedelta(hours=1)
    world.history.put_round(
        f.finished_round(
            id="r2", started_at=later, finished_at=later, assignments=(_open("b1", round_id="r2"),)
        )
    )
    for round_ in world.history.rounds.values():
        world.statistics.record_round(round_)
    service, _ = _service(world)
    service.delete("r1")
    assert dict(world.history.aggregates) == recompute(world.history.rounds.values())
    assert dict(world.history.aggregates) != {}


def test_delete_unknown_round() -> None:
    service, events = _service(World())
    with pytest.raises(NotFoundError):
        service.delete("nope")
    assert events.deleted == []
