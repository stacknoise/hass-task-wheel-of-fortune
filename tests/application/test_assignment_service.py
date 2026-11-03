"""AssignmentService und SwapService gegen In-Memory-Speicher."""

import datetime as dt

import pytest

from custom_components.task_wheel.application.assignment_service import AssignmentService
from custom_components.task_wheel.application.swap_service import SwapService
from custom_components.task_wheel.const import keys
from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.errors import (
    InvalidTransitionError,
    NotFoundError,
    SwapRejectedError,
)
from custom_components.task_wheel.infrastructure.repository.config_store import ConfigStore
from custom_components.task_wheel.infrastructure.repository.history_store import HistoryStore
from custom_components.task_wheel.infrastructure.repository.memory import MemoryStore

from ..domain import factories as f

DAY = dt.timedelta(days=1)
DUE = f.NOW + 7 * DAY


class World:
    """Repositories mit Personen p1..p3, einer Aufgabe und einer Runde mit offenen Zuteilungen."""

    def __init__(self, **settings: object) -> None:
        self.config = ConfigStore(MemoryStore())
        self.history = HistoryStore(MemoryStore())
        for ident in ("p1", "p2", "p3"):
            self.config.put_person(f.person(id=ident, slug=ident, name=ident, absences=()))
        self.config.put_task(f.task(allowed=frozenset({"p1", "p2", "p3"})))
        self.config.set_settings(f.settings(**settings))
        self.assignments = AssignmentService(self.config, self.history)
        self.swaps = SwapService(self.config, self.history)

    def add_round(self, *assignments: object, started: dt.datetime = f.NOW) -> None:
        self.history.put_round(
            f.finished_round(started_at=started, finished_at=started, assignments=assignments)  # type: ignore[arg-type]
        )

    def stored(self, assignment_id: str):
        return self.history.get_assignment(assignment_id)


def _open(ident: str = "a1", **overrides: object):
    return f.assignment(**{"id": ident, "due_at": DUE, **overrides})


def test_complete_on_time_persists_in_round() -> None:
    world = World()
    world.add_round(_open(), _open("a2"))
    done = world.assignments.complete("a1", f.NOW + DAY)
    assert (done.status, done.done_at) == (S.ON_TIME, f.NOW + DAY)
    assert world.stored("a1") == done
    assert world.stored("a2").status is S.OPEN  # type: ignore[union-attr]
    assert world.history.open_assignments("p1") == (world.stored("a2"),)


def test_complete_late_after_due() -> None:
    world = World()
    world.add_round(_open())
    assert world.assignments.complete("a1", DUE + DAY).status is S.LATE


def test_complete_unknown_and_twice() -> None:
    world = World()
    world.add_round(_open())
    with pytest.raises(NotFoundError):
        world.assignments.complete("nope", f.NOW)
    world.assignments.complete("a1", f.NOW)
    with pytest.raises(InvalidTransitionError):
        world.assignments.complete("a1", f.NOW)


def test_daily_run_marks_only_after_grace() -> None:
    world = World(missed_grace_hours=24)
    world.add_round(_open(), _open("a2", status=S.LATE, done_at=f.NOW))
    assert world.assignments.mark_missed(DUE + dt.timedelta(hours=24)) == ()
    missed = world.assignments.mark_missed(DUE + dt.timedelta(hours=25))
    assert [item.id for item in missed] == ["a1"]
    assert world.stored("a1").status is S.MISSED  # type: ignore[union-attr]
    assert world.stored("a2").status is S.LATE  # type: ignore[union-attr]
    assert world.assignments.mark_missed(DUE + 10 * DAY) == ()


def test_daily_run_includes_swapped_assignments() -> None:
    world = World(missed_grace_hours=0)
    world.add_round(_open())
    world.swaps.swap("a1", "p2", f.NOW)
    assert world.assignments.mark_missed(DUE + DAY)[0].status is S.MISSED


def test_points_use_configured_factors() -> None:
    world = World(late_points_factor=0.5, missed_points_factor=-1.0)
    world.add_round(_open(points=4), _open("a2", points=4))
    assert world.assignments.points(world.assignments.complete("a1", DUE + DAY)) == 2
    missed = world.assignments.mark_missed(DUE + 30 * DAY)
    assert world.assignments.points(missed[0]) == -4


def test_swap_moves_points_to_receiver_and_uses_joker() -> None:
    world = World(jokers_per_month=2)
    world.add_round(_open(points=3))
    assert world.swaps.jokers_left("p1", f.NOW) == 2
    swapped = world.swaps.swap("a1", "p2", f.NOW)
    assert (swapped.status, swapped.person_id) == (S.SWAPPED, "p2")
    assert world.history.open_assignments("p2") == (swapped,)
    assert world.history.open_assignments("p1") == ()
    assert world.swaps.jokers_left("p1", f.NOW) == 1
    assert world.swaps.jokers_left("p2", f.NOW) == 2
    done = world.assignments.complete("a1", f.NOW)
    assert (done.person_id, world.assignments.points(done)) == ("p2", 3)


def test_swap_fails_without_jokers_and_changes_nothing() -> None:
    world = World(jokers_per_month=1)
    world.add_round(_open(), _open("a2"))
    world.swaps.swap("a1", "p2", f.NOW)
    with pytest.raises(SwapRejectedError) as caught:
        world.swaps.swap("a2", "p3", f.NOW)
    assert caught.value.key == keys.ERR_NO_JOKERS
    assert world.stored("a2").status is S.OPEN  # type: ignore[union-attr]


def test_jokers_reset_at_start_of_next_month() -> None:
    world = World(jokers_per_month=1)
    started = dt.datetime(2026, 11, 20, tzinfo=f.TZ)
    world.add_round(
        _open(due_at=started + 30 * DAY), _open("a2", due_at=started + 30 * DAY), started=started
    )
    world.swaps.swap("a1", "p2", dt.datetime(2026, 11, 28, 12, tzinfo=f.TZ))
    assert world.swaps.jokers_left("p1", dt.datetime(2026, 11, 30, 23, 59, tzinfo=f.TZ)) == 0
    december = dt.datetime(2026, 12, 1, 0, 1, tzinfo=f.TZ)
    assert world.swaps.jokers_left("p1", december) == 1
    assert world.swaps.swap("a2", "p3", december).person_id == "p3"


def test_swap_rejections_leave_assignment_unchanged() -> None:
    world = World()
    world.config.put_task(f.task(id="t2", allowed=frozenset({"p1"}), swap_allowed=False))
    world.add_round(_open(), _open("a2", task_id="t2"))
    with pytest.raises(SwapRejectedError) as disabled:
        world.swaps.swap("a2", "p2", f.NOW)
    assert disabled.value.key == keys.ERR_SWAP_DISABLED
    with pytest.raises(SwapRejectedError):
        world.swaps.swap("a1", "p1", f.NOW)
    assert world.stored("a2").status is S.OPEN  # type: ignore[union-attr]


def test_swap_validation_errors() -> None:
    world = World()
    world.add_round(_open(), _open("a2", task_id="gone"))
    with pytest.raises(NotFoundError):
        world.swaps.swap("nope", "p2", f.NOW)
    with pytest.raises(NotFoundError):
        world.swaps.swap("a2", "p2", f.NOW)
    with pytest.raises(NotFoundError):
        world.swaps.swap("a1", "ghost", f.NOW)
    world.swaps.swap("a1", "p2", f.NOW)
    with pytest.raises(InvalidTransitionError):
        world.swaps.swap("a1", "p3", f.NOW)
