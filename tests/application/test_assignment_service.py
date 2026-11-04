"""AssignmentService und SwapService gegen In-Memory-Speicher."""

import datetime as dt

import pytest

from custom_components.task_wheel.application.assignment_service import AssignmentService
from custom_components.task_wheel.application.protocols import NoEvents
from custom_components.task_wheel.application.statistics_service import StatisticsService
from custom_components.task_wheel.application.swap_service import SwapService
from custom_components.task_wheel.const import keys
from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.enums import Load
from custom_components.task_wheel.domain.errors import (
    InvalidTransitionError,
    NotFoundError,
    SwapRejectedError,
)
from custom_components.task_wheel.domain.models import Swap
from custom_components.task_wheel.domain.statistics.aggregate import recompute
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
        self.statistics = StatisticsService(self.config, self.history)
        self.assignments = AssignmentService(self.config, self.history, self.statistics)
        self.swaps = SwapService(self.config, self.history, self.statistics)

    def add_round(self, *assignments: object, started: dt.datetime = f.NOW) -> None:
        """Legt die Runde an; p2 und p3 sind mit verpassten Zuteilungen dabei (Tauschpartner)."""
        partners = tuple(
            f.assignment(
                id=f"partner-{ident}",
                person_id=ident,
                status=S.MISSED,
                due_at=started,
            )
            for ident in ("p2", "p3")
        )
        self.history.put_round(
            f.finished_round(
                started_at=started,
                finished_at=started,
                assignments=(*assignments, *partners),  # type: ignore[arg-type]
            )
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
    world.history.put_round(f.finished_round(assignments=(_open(), _open("a2", person_id="p2"))))
    world.swaps.swap("a1", "p2", f.NOW)
    assert world.assignments.mark_missed(DUE + DAY)[0].status is S.MISSED


def test_points_use_configured_factors() -> None:
    world = World(late_points_factor=0.5, missed_points_factor=-1.0)
    world.add_round(_open(points=4), _open("a2", points=4))
    assert world.assignments.points(world.assignments.complete("a1", DUE + DAY)) == 2
    missed = world.assignments.mark_missed(DUE + 30 * DAY)
    assert world.assignments.points(missed[0]) == -4


def _swap_round(world: World, *assignments: object) -> None:
    """Runde mit Bad (t1, p1) und Küche (t2, p2) als offene Zuteilungen, Aufgaben für alle."""
    world.config.put_task(f.task(id="t2", allowed=frozenset({"p1", "p2", "p3"})))
    world.history.put_round(f.finished_round(assignments=assignments))  # type: ignore[arg-type]
    world.statistics.record_round(world.history.rounds["r1"])


def _kitchen(ident: str = "a2", **overrides: object):
    return _open(ident, person_id="p2", task_id="t2", **overrides)


def test_swap_exchanges_both_assignments_and_points() -> None:
    world = World()
    _swap_round(world, _open(points=3), _kitchen(points=8))
    swapped = world.swaps.swap("a1", "p2", f.NOW)
    assert (swapped.status, swapped.person_id) == (S.SWAPPED, "p2")
    other = world.stored("a2")
    assert (other.status, other.person_id) == (S.SWAPPED, "p1")  # type: ignore[union-attr]
    assert world.stored("a1").swap == Swap(from_person_id="p1", to_person_id="p2", at=f.NOW)
    assert other.swap == Swap(from_person_id="p2", to_person_id="p1", at=f.NOW)  # type: ignore[union-attr]
    assert world.history.open_assignments("p1") == (other,)
    assert world.history.open_assignments("p2") == (swapped,)
    done = world.assignments.complete("a1", f.NOW)
    assert (done.person_id, world.assignments.points(done)) == ("p2", 3)
    done_other = world.assignments.complete("a2", f.NOW)
    assert (done_other.person_id, world.assignments.points(done_other)) == ("p1", 8)


def test_each_person_keeps_exactly_one_task_per_round() -> None:
    world = World()
    _swap_round(world, _open(), _kitchen())
    world.swaps.swap("a1", "p2", f.NOW)
    holders = sorted(item.person_id for item in world.history.rounds["r1"].assignments)
    assert holders == ["p1", "p2"]


def test_swap_keeps_statistics_equal_to_recomputation() -> None:
    world = World()
    _swap_round(world, _open(points=3), _kitchen(points=8))
    world.swaps.swap("a1", "p2", f.NOW)
    world.assignments.complete("a1", f.NOW)
    assert dict(world.history.aggregates) == recompute(world.history.rounds.values())
    assert world.history.aggregates["2026-11"]["p2"]["t1"] == {"on_time": [1, 3]}
    assert world.history.aggregates["2026-11"]["p1"]["t2"] == {"swapped": [1, 8]}


def test_swap_fires_event_for_both_assignments() -> None:
    world = World()
    events = _Events()
    swaps = SwapService(world.config, world.history, world.statistics, events)
    _swap_round(world, _open(), _kitchen())
    swaps.swap("a1", "p2", f.NOW)
    assert [(item.id, item.person_id) for item in events.swapped] == [("a1", "p2"), ("a2", "p1")]


class _Events(NoEvents):
    def __init__(self) -> None:
        self.swapped: list[object] = []

    def assignment_swapped(self, assignment: object) -> None:
        self.swapped.append(assignment)


def test_swap_with_earliest_open_assignment_of_target() -> None:
    world = World()
    _swap_round(world, _open(), _kitchen(due_at=DUE + DAY), _kitchen("a3", due_at=DUE - DAY))
    world.swaps.swap("a1", "p2", f.NOW)
    assert world.stored("a3").person_id == "p1"  # type: ignore[union-attr]
    assert world.stored("a2").person_id == "p2"  # type: ignore[union-attr]


@pytest.mark.parametrize("state", [S.ON_TIME, S.MISSED, S.SWAPPED])
def test_swap_needs_open_counterpart(state: S) -> None:
    world = World()
    done_at = f.NOW if state is S.ON_TIME else None
    _swap_round(world, _open(), _kitchen(status=state, done_at=done_at))
    with pytest.raises(SwapRejectedError) as caught:
        world.swaps.swap("a1", "p2", f.NOW)
    assert caught.value.key == keys.ERR_SWAP_NO_OPEN_ASSIGNMENT
    assert world.stored("a1").status is S.OPEN  # type: ignore[union-attr]


def test_swap_only_within_the_same_round() -> None:
    world = World()
    world.config.put_task(f.task(id="t2", allowed=frozenset({"p1", "p2", "p3"})))
    world.history.put_round(f.finished_round(assignments=(_open(),)))
    world.history.put_round(
        f.finished_round(id="r2", assignments=(_kitchen(round_id="r2"),))  # type: ignore[arg-type]
    )
    with pytest.raises(SwapRejectedError) as caught:
        world.swaps.swap("a1", "p2", f.NOW)
    assert caught.value.key == keys.ERR_SWAP_NO_OPEN_ASSIGNMENT
    assert world.stored("a1").status is S.OPEN  # type: ignore[union-attr]


def test_swap_twice_is_forbidden() -> None:
    world = World()
    _swap_round(world, _open(), _kitchen(), _open("a3", person_id="p3"))
    world.swaps.swap("a1", "p2", f.NOW)
    with pytest.raises(InvalidTransitionError):
        world.swaps.swap("a1", "p3", f.NOW)
    with pytest.raises(SwapRejectedError):  # a2 ist getauscht, also kein offenes Gegenstück
        world.swaps.swap("a3", "p1", f.NOW)


def test_swap_rejected_when_counter_task_disallows_requester() -> None:
    world = World()
    world.config.put_task(f.task(id="t2", allowed=frozenset({"p2", "p3"})))
    world.history.put_round(f.finished_round(assignments=(_open(), _kitchen())))
    with pytest.raises(SwapRejectedError) as caught:
        world.swaps.swap("a1", "p2", f.NOW)
    assert caught.value.key == keys.ERR_SWAP_NOT_ALLOWED
    assert (world.stored("a1").status, world.stored("a2").status) == (S.OPEN, S.OPEN)  # type: ignore[union-attr]


def test_swap_rejected_when_counter_task_is_not_swappable() -> None:
    world = World()
    world.config.put_task(f.task(id="t2", allowed=frozenset({"p1", "p2"}), swap_allowed=False))
    world.history.put_round(f.finished_round(assignments=(_open(), _kitchen())))
    with pytest.raises(SwapRejectedError) as caught:
        world.swaps.swap("a1", "p2", f.NOW)
    assert caught.value.key == keys.ERR_SWAP_DISABLED


def test_swap_rejected_when_requester_is_paused() -> None:
    world = World()
    world.config.put_person(f.person(id="p1", slug="p1", name="p1", absences=(), load=Load.PAUSED))
    _swap_round(world, _open(), _kitchen())
    with pytest.raises(SwapRejectedError) as caught:
        world.swaps.swap("a1", "p2", f.NOW)
    assert caught.value.key == keys.ERR_SWAP_PAUSED
    assert world.stored("a2").person_id == "p2"  # type: ignore[union-attr]


def test_swap_rejections_leave_assignments_unchanged() -> None:
    world = World()
    world.config.put_task(f.task(id="t2", allowed=frozenset({"p1"}), swap_allowed=False))
    world.history.put_round(f.finished_round(assignments=(_open(), _kitchen())))
    with pytest.raises(SwapRejectedError) as disabled:
        world.swaps.swap("a2", "p1", f.NOW)
    assert disabled.value.key == keys.ERR_SWAP_DISABLED
    with pytest.raises(SwapRejectedError) as same:
        world.swaps.swap("a1", "p1", f.NOW)
    assert same.value.key == keys.ERR_SWAP_SAME_PERSON
    assert world.stored("a2").status is S.OPEN  # type: ignore[union-attr]


def test_swap_validation_errors() -> None:
    world = World()
    _swap_round(world, _open(), _kitchen(), _open("a3", task_id="gone", person_id="p3"))
    with pytest.raises(NotFoundError):
        world.swaps.swap("nope", "p2", f.NOW)
    with pytest.raises(NotFoundError):
        world.swaps.swap("a3", "p2", f.NOW)
    with pytest.raises(NotFoundError):
        world.swaps.swap("a1", "ghost", f.NOW)
    with pytest.raises(NotFoundError):  # Aufgabe des Gegenstücks fehlt
        world.swaps.swap("a1", "p3", f.NOW)


def test_skip_marks_assignment_and_counts_like_missed() -> None:
    world = World(missed_points_factor=-0.5)
    world.add_round(_open(), _open("a2", person_id="p2"))
    for round_ in world.history.rounds.values():
        world.statistics.record_round(round_)
    skipped = world.assignments.skip("a1")
    assert (skipped.status, skipped.done_at) == (S.SKIPPED, None)
    assert world.history.open_assignments("p1") == ()
    assert world.assignments.points(skipped) == -2  # 5 Punkte * -0.5, gerundet
    assert world.history.aggregates["2026-11"]["p1"]["t1"]["skipped"][0] == 1


def test_skip_swapped_assignment_and_rejects_closed_ones() -> None:
    world = World()
    world.history.put_round(f.finished_round(assignments=(_open(), _open("a2", person_id="p2"))))
    world.swaps.swap("a1", "p2", f.NOW)
    assert world.assignments.skip("a1").status is S.SKIPPED
    world.assignments.complete("a2", f.NOW)
    for ident in ("a1", "a2"):
        with pytest.raises(InvalidTransitionError):
            world.assignments.skip(ident)
    with pytest.raises(NotFoundError):
        world.assignments.skip("nope")


def test_mark_missed_saves_and_records_once_per_round(monkeypatch) -> None:
    world = World(missed_grace_hours=0)
    world.add_round(_open(), _open("a2"))
    saved: list[object] = []
    real = world.history.put_round
    monkeypatch.setattr(world.history, "put_round", lambda r: saved.append(r) or real(r))
    missed = world.assignments.mark_missed(DUE + DAY)
    assert [m.id for m in missed] == ["a1", "a2"]
    assert len(saved) == 1
