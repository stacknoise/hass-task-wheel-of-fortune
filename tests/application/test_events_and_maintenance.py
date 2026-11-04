"""Events aus Zuteilungen, Wartungslauf, Zeitplan speichern/löschen, Komposition, Nachschlagen."""

import datetime as dt
from unittest.mock import MagicMock

import pytest

from custom_components.task_wheel.application import event_payloads as payloads
from custom_components.task_wheel.application.assignment_service import AssignmentService
from custom_components.task_wheel.application.daily import next_daily
from custom_components.task_wheel.application.lookup import find_by_ref
from custom_components.task_wheel.application.maintenance_service import (
    TIMER_MAINTENANCE,
    MaintenanceService,
)
from custom_components.task_wheel.application.notification_service import NotificationService
from custom_components.task_wheel.application.schedule_service import timer_key
from custom_components.task_wheel.application.statistics_service import StatisticsService
from custom_components.task_wheel.application.swap_service import SwapService
from custom_components.task_wheel.const.defaults import MAINTENANCE_HOUR
from custom_components.task_wheel.const.keys import (
    ATTR_DAYS_SINCE,
    ATTR_FROM_PERSON_ID,
    ATTR_FROM_PERSON_NAME,
    ATTR_PERSON_NAME,
    ATTR_TASK_NAME,
)
from custom_components.task_wheel.domain.enums import AssignmentStatus, RoundOrigin
from custom_components.task_wheel.domain.errors import AmbiguousReferenceError, NotFoundError
from custom_components.task_wheel.domain.models import Recurring
from custom_components.task_wheel.runtime import compose

from ..domain import factories as f
from .test_assignment_service import DUE
from .test_assignment_service import World as AssignmentWorld
from .world import DAY, FakeTimers, RecordingEvents, World


class EventWorld(AssignmentWorld):
    """Wie `World` der Zuteilungstests, aber mit aufzeichnenden Events."""

    def __init__(self) -> None:
        super().__init__()
        self.events = RecordingEvents()
        self.assignments = AssignmentService(
            self.config, self.history, self.statistics, self.events
        )
        self.swaps = SwapService(self.config, self.history, self.statistics, self.events)


def _open(ident: str = "a1", **overrides: object):
    return f.assignment(**{"id": ident, "due_at": DUE, **overrides})


def test_complete_fires_event() -> None:
    world = EventWorld()
    world.add_round(_open())
    done = world.assignments.complete("a1", f.NOW + DAY)
    assert world.events.completed == [done]


def test_failed_complete_fires_nothing() -> None:
    world = EventWorld()
    with pytest.raises(NotFoundError):
        world.assignments.complete("missing", f.NOW)
    assert world.events.completed == []


def _swap_world() -> EventWorld:
    world = EventWorld()
    world.history.put_round(
        f.finished_round(assignments=(_open(person_id="p1"), _open("a2", person_id="p2")))
    )
    return world


def test_swap_fires_event_per_assignment_with_giver() -> None:
    world = _swap_world()
    swapped = world.swaps.swap("a1", "p2", f.NOW)
    assert world.events.swapped == [swapped, world.history.get_assignment("a2")]
    assert [(item.person_id, item.swap.from_person_id) for item in world.events.swapped] == [  # type: ignore[union-attr]
        ("p2", "p1"),
        ("p1", "p2"),
    ]


def test_mark_missed_fires_event_per_assignment() -> None:
    world = EventWorld()
    world.add_round(_open(due_at=f.NOW - 3 * DAY))
    missed = world.assignments.mark_missed(f.NOW)
    assert world.events.missed == list(missed)
    assert len(missed) == 1


def test_find_open_picks_earliest_due() -> None:
    world = EventWorld()
    world.add_round(_open("late", person_id="p1", due_at=DUE + DAY), _open("early", person_id="p1"))
    assert world.assignments.find_open("p1", "t1").id == "early"


def test_find_open_unknown_raises() -> None:
    with pytest.raises(NotFoundError):
        EventWorld().assignments.find_open("p1", "t1")


def test_payloads_contain_names_and_ids_only() -> None:
    world = _swap_world()
    swapped = world.swaps.swap("a1", "p2", f.NOW)
    data = payloads.swapped_payload(world.config, swapped)
    assert data[ATTR_FROM_PERSON_ID] == "p1"
    assert data[ATTR_FROM_PERSON_NAME] == "p1"
    assert data[ATTR_PERSON_NAME] == "p2"
    assert data[ATTR_TASK_NAME] == world.config.tasks["t1"].name


def test_payload_names_fall_back_to_ids_after_deletion() -> None:
    world = EventWorld()
    assignment = _open(task_id="gone", person_id="gone")
    world.add_round(assignment)
    data = payloads.assignment_payload(world.config, assignment)
    assert (data[ATTR_TASK_NAME], data[ATTR_PERSON_NAME]) == ("gone", "gone")
    round_data = payloads.round_payload(world.config, world.history.rounds[assignment.round_id])
    assert round_data["schedule_name"] == world.history.rounds[assignment.round_id].schedule_id
    assert payloads.reminder_payload(f.schedule(), 3)[ATTR_DAYS_SINCE] == 3


def test_next_daily_uses_local_hour_and_rolls_over() -> None:
    after = dt.datetime(2026, 11, 3, 4, 0, tzinfo=dt.UTC)
    assert next_daily(3, after) == dt.datetime(2026, 11, 4, 3, 0, tzinfo=dt.UTC)
    assert next_daily(5, after) == dt.datetime(2026, 11, 3, 5, 0, tzinfo=dt.UTC)


def test_find_by_ref_matches_any_key_or_raises() -> None:
    people = [f.person(id="p1", slug="anna"), f.person(id="p2", slug="ben")]
    keys = lambda p: (p.id, p.slug)  # noqa: E731
    assert find_by_ref(people, "ben", "person", keys).id == "p2"
    assert find_by_ref(people, "p1", "person", keys).slug == "anna"
    with pytest.raises(NotFoundError):
        find_by_ref(people, "zoe", "person", keys)


def test_find_by_ref_rejects_an_ambiguous_reference() -> None:
    tasks = [f.task(id="t1", name="Müll"), f.task(id="t2", name="Müll"), f.task(id="t3")]
    keys = lambda t: (t.id, t.name)  # noqa: E731
    with pytest.raises(AmbiguousReferenceError) as err:
        find_by_ref(tasks, "Müll", "task", keys)
    assert err.value.key == "ambiguous_reference"
    assert find_by_ref(tasks, "t2", "task", keys).id == "t2"


def _maintenance(world: EventWorld):
    timers, spawned = FakeTimers(), []
    service = MaintenanceService(
        world.config, world.history, world.assignments, timers, spawned.append
    )
    return service, timers, spawned


async def test_maintenance_marks_missed_purges_and_rearms() -> None:
    world = EventWorld()
    for ident, started in (("r_old", f.NOW - 800 * DAY), ("r_new", f.NOW - 5 * DAY)):
        old = ident == "r_old"
        item = _open(
            f"a_{ident}",
            round_id=ident,
            due_at=f.NOW - 3 * DAY,
            status=AssignmentStatus.SKIPPED if old else AssignmentStatus.OPEN,
        )
        world.history.put_round(
            f.finished_round(id=ident, started_at=started, finished_at=started, assignments=(item,))
        )
    service, timers, spawned = _maintenance(world)
    service.start(f.NOW)
    assert [item.id for item in world.events.missed] == ["a_r_new"]
    assert len(spawned) == 1
    await spawned[0]
    assert set(world.history.rounds) == {"r_new"}
    at, _ = timers.timers[TIMER_MAINTENANCE]
    assert (at.hour, at > f.NOW) == (MAINTENANCE_HOUR, True)


def test_maintenance_arms_the_next_run_even_if_marking_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = EventWorld()
    service, timers, _spawned = _maintenance(world)

    def boom(*_args: object) -> None:
        raise KeyError

    monkeypatch.setattr(world.assignments, "mark_missed", boom)
    with pytest.raises(KeyError):
        service.run(f.NOW)
    assert TIMER_MAINTENANCE in timers.timers


async def test_maintenance_keeps_old_rounds_with_open_assignments() -> None:
    world = EventWorld()
    started = f.NOW - 800 * DAY
    item = _open("a_old", round_id="r_old", due_at=f.NOW + 30 * DAY)
    world.history.put_round(
        f.finished_round(id="r_old", started_at=started, finished_at=started, assignments=(item,))
    )
    service, _timers, spawned = _maintenance(world)
    service.run(f.NOW)
    await spawned[0]
    assert set(world.history.rounds) == {"r_old"}


async def test_maintenance_keeps_recent_rounds() -> None:
    world = EventWorld()
    world.add_round(_open())
    service, timers, spawned = _maintenance(world)
    timers.schedule("x", f.NOW, lambda _: None)
    service.run(f.NOW)
    await spawned[0]
    assert len(world.history.rounds) == 1


def test_maintenance_timer_fires_run_again() -> None:
    world = EventWorld()
    world.add_round(_open())
    service, timers, spawned = _maintenance(world)
    service.start(f.NOW)
    spawned[0].close()
    timers.fire(TIMER_MAINTENANCE)
    spawned[1].close()
    assert TIMER_MAINTENANCE in timers.timers


def test_schedule_save_arms_and_delete_disarms() -> None:
    world = World()
    trigger = Recurring(weekdays=frozenset({1}), time=dt.time(8))
    schedule = f.schedule(id="s2", slug="s2", trigger=trigger, task_ids=("t1",))
    world.schedules.save(schedule, f.NOW)
    assert world.config.schedules["s2"] == schedule
    assert timer_key("s2") in world.timers.timers
    world.schedules.delete("s2")
    assert "s2" not in world.config.schedules
    assert timer_key("s2") not in world.timers.timers


def test_compose_shares_statistics_and_events() -> None:
    world = World()
    events = RecordingEvents()
    data = compose(
        world.config,
        world.history,
        timers=FakeTimers(),
        events=events,
        notifications=NotificationService(
            world.config, MagicMock(), MagicMock(), lambda coro: coro.close()
        ),
        clock=lambda: f.NOW,
        spawn=lambda coro: coro.close(),
    )
    round_ = data.draws.draw("s1", RoundOrigin.SERVICE, f.NOW)
    assert events.drawn == [round_]
    assert isinstance(data.statistics, StatisticsService)
    done = data.assignments.complete(round_.assignments[0].id, f.NOW)
    assert events.completed == [done]
