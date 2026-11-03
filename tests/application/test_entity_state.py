"""EntityStateService: Werte der Entitäten aus Indizes und Aggregaten."""

from custom_components.task_wheel.application.assignment_service import AssignmentService
from custom_components.task_wheel.application.entity_state import EntityStateService
from custom_components.task_wheel.application.statistics_service import StatisticsService
from custom_components.task_wheel.domain.enums import AssignmentStatus, RoundOrigin
from custom_components.task_wheel.domain.models import OnceTrigger

from ..domain import factories as f
from .world import DAY, World

NOW = f.NOW


def _setup(**settings: object) -> tuple[World, EntityStateService, AssignmentService]:
    world = World(0.1, 0.9, **settings)
    state = EntityStateService(world.config, world.history, world.schedules)
    assignments = AssignmentService(
        world.config, world.history, StatisticsService(world.config, world.history)
    )
    world.draws.draw("s1", RoundOrigin.MANUAL, NOW)
    return world, state, assignments


def test_open_count_and_items_are_sorted_by_deadline() -> None:
    world, state, _ = _setup()
    assert (state.open_count("p1"), state.open_count("p2")) == (1, 1)
    (item,) = state.open_items("p1")
    assert (item.task_name, item.points, item.due_at) == ("A", 5, NOW + 7 * DAY)
    assert state.open_count("unbekannt") == 0 and state.open_items("unbekannt") == ()
    later = f.assignment(id="a9", round_id="r9", person_id="p1", due_at=NOW + DAY)
    world.history.put_round(
        f.finished_round(id="r9", started_at=NOW, finished_at=NOW, assignments=(later,))
    )
    assert [i.assignment_id for i in state.open_items("p1")] == ["a9", item.assignment_id]


def test_deleted_task_is_named_by_its_id() -> None:
    world, state, _ = _setup()
    world.config.remove_task("t1")
    assert state.open_items("p1")[0].task_name == "t1"


def test_month_points_count_only_completed_work_with_factors() -> None:
    world, state, assignments = _setup(late_points_factor=0.5)
    assert state.month_points("p1", NOW) == 0
    (item,) = state.open_items("p1")
    assignments.complete(item.assignment_id, NOW)
    assert state.month_points("p1", NOW) == 5
    assert state.month_points("p2", NOW) == 0
    assert state.open_count("p1") == 0
    assert state.month_points("p1", NOW + 40 * DAY) == 0
    (other,) = state.open_items("p2")
    assignments.complete(other.assignment_id, NOW + 20 * DAY)
    assert state.month_points("p2", NOW) == 1
    assert world.history.get_assignment(other.assignment_id).status is AssignmentStatus.LATE  # type: ignore[union-attr]


def test_next_draw_follows_trigger_state() -> None:
    world, state, _ = _setup()
    assert state.next_draw("s1", NOW) is None
    assert state.next_draw("fehlt", NOW) is None
    world.put_schedule(trigger=OnceTrigger(at=NOW + DAY), enabled=True)
    assert state.next_draw("s1", NOW) == NOW + DAY
    world.put_schedule(trigger=OnceTrigger(at=NOW + DAY), enabled=False)
    assert state.next_draw("s1", NOW) is None
