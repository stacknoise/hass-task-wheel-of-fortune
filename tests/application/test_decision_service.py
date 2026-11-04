"""Entscheidungslog: Einträge der Auslosung, des Tausches, Abfrage und Bereinigung."""

import pytest

from custom_components.task_wheel.application.statistics_service import StatisticsService
from custom_components.task_wheel.application.swap_service import SwapService
from custom_components.task_wheel.domain.decisions import DecisionFilter, Exchange
from custom_components.task_wheel.domain.enums import (
    DecisionKind,
    ExclusionReason,
    Period,
    RoundOrigin,
)
from custom_components.task_wheel.domain.errors import ValidationError
from custom_components.task_wheel.domain.models import EveryRound, MaxPerPeriod, WeeklyDaysAbsence

from ..domain import factories as f
from .world import DAY, World

NOW = f.NOW


def _only(world: World):
    (record,) = world.decision_store.records.values()
    return record


def test_draw_is_logged_per_task_with_wheel_and_winner():
    world = World(0.1, 0.9)
    round_ = world.draws.draw("s1", RoundOrigin.AUTO, NOW)
    record = _only(world)
    assert (record.kind, record.round_id, record.origin) == (
        DecisionKind.DRAW,
        round_.id,
        RoundOrigin.AUTO,
    )
    assert record.schedule_name == world.config.schedules["s1"].name
    first, second = record.tasks
    assert (first.task_id, first.winner_id) == ("t1", "p1")
    assert [(w.person_id, w.person_name) for w in first.wheel] == [("p1", "p1"), ("p2", "p2")]
    assert second.winner_id == "p2"
    assert {e.person_id: e.reason for e in second.excluded} == {"p1": ExclusionReason.TAKEN}


def test_task_nobody_can_take_is_logged_as_unassigned_with_reason():
    world = World(0.1)
    away = (WeeklyDaysAbsence(weekdays=frozenset(range(7))),)
    world.config.put_person(f.person(id="p1", slug="p1", name="p1", absences=away))
    daily = MaxPerPeriod(count=1, period=Period.DAY, every=1)
    world.config.put_task(
        f.task(id="t1", name="A", allowed=frozenset({"p1"}), points=5, frequency=daily)
    )
    world.draws.draw("s1", RoundOrigin.AUTO, NOW)
    (item,) = _only(world).tasks
    assert (item.task_id, item.assigned, item.wheel) == ("t1", False, ())
    assert {e.person_id: e.reason for e in item.excluded} == {
        "p1": ExclusionReason.ABSENT,
        "p2": "not_allowed",
    }


def test_person_not_allowed_for_the_task_is_logged_with_that_reason():
    world = World(0.1, 0.9)
    world.config.put_task(
        f.task(id="t1", name="A", allowed=frozenset({"p1"}), points=5, frequency=EveryRound())
    )
    world.draws.draw("s1", RoundOrigin.AUTO, NOW)
    first = _only(world).tasks[0]
    assert [(w.person_id) for w in first.wheel] == ["p1"]
    assert [(e.person_id, e.reason) for e in first.excluded] == [("p2", "not_allowed")]


def test_log_keeps_names_after_rename_or_delete():
    world = World(0.1, 0.9)
    world.draws.draw("s1", RoundOrigin.AUTO, NOW)
    world.config.remove_person("p1")
    record = _only(world)
    assert record.tasks[0].wheel[0].person_name == "p1"


def test_swap_is_logged_with_both_people_and_tasks():
    world = World(0.1, 0.9)
    round_ = world.draws.draw("s1", RoundOrigin.AUTO, NOW)
    swaps = SwapService(
        world.config,
        world.history,
        StatisticsService(world.config, world.history),
        world.events,
        world.decisions,
    )
    first = next(a for a in round_.assignments if a.person_id == "p1")
    swaps.swap(first.id, "p2", NOW)
    log = list(world.decision_store.records.values())
    assert [r.kind for r in log] == [DecisionKind.DRAW, DecisionKind.SWAP]
    exchange = log[1].exchange
    assert (exchange.person_id, exchange.other_person_id) == ("p1", "p2")
    assert (exchange.task_id, exchange.other_task_id) == ("t1", "t2")
    assert exchange.before_start is False
    assert log[1].round_id == round_.id


def test_exchange_before_start_carries_the_note():
    world = World()
    world.decisions.record_exchange(
        DecisionKind.EXCHANGE,
        "s1",
        Exchange(
            person_id="p1",
            person_name="Anna",
            task_id="t1",
            task_name="A",
            other_task_id="t2",
            other_task_name="B",
            before_start=True,
        ),
        NOW,
    )
    record = _only(world)
    assert record.exchange.before_start is True and record.tasks == ()
    assert record.involves_person("p1") and record.involves_task("t2")
    assert not record.involves_person("p2")


def test_page_filters_and_pages_newest_first():
    world = World(0.1, 0.9)
    for step in range(3):
        world.draws.draw("s1", RoundOrigin.AUTO, NOW + step * DAY)
    page = world.decisions.page(limit=2)
    assert [r.at for r in page.entries] == [NOW + 2 * DAY, NOW + DAY]
    assert page.next_offset == 2
    rest = world.decisions.page(offset=2, limit=2)
    assert [r.at for r in rest.entries] == [NOW] and rest.next_offset is None
    by_person = world.decisions.page(DecisionFilter(person_id="p1"))
    assert len(by_person.entries) == 3
    assert not world.decisions.page(DecisionFilter(person_id="x")).entries
    assert not world.decisions.page(DecisionFilter(kind=DecisionKind.SWAP)).entries
    since = world.decisions.page(DecisionFilter(since=NOW + DAY))
    assert len(since.entries) == 2
    only_t = world.decisions.page(DecisionFilter(task_id="t2", schedule_id="s1"))
    assert len(only_t.entries) == 3


@pytest.mark.parametrize(("limit", "offset"), [(0, 0), (201, 0), (10, -1)])
def test_page_rejects_bad_bounds(limit, offset):
    with pytest.raises(ValidationError):
        World().decisions.page(offset=offset, limit=limit)


def test_purge_uses_the_retention_setting():
    world = World(0.1, 0.9, decision_retention_days=7)
    world.draws.draw("s1", RoundOrigin.AUTO, NOW - 8 * DAY)
    world.draws.draw("s1", RoundOrigin.AUTO, NOW - 6 * DAY)
    assert world.decisions.purge(NOW) == 1
    assert [r.at for r in world.decision_store.records.values()] == [NOW - 6 * DAY]


def test_store_drops_the_oldest_over_the_limit(monkeypatch):
    monkeypatch.setattr("custom_components.task_wheel.const.limits.MAX_STORED_DECISIONS", 2)
    world = World(0.1, 0.9)
    for step in range(3):
        world.draws.draw("s1", RoundOrigin.AUTO, NOW + step * DAY)
    assert [r.at for r in world.decision_store.records.values()] == [NOW + DAY, NOW + 2 * DAY]
