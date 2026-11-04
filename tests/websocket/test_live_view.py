"""Abonnement: erst der Snapshot, danach nur Änderungen je Objekt."""

import pytest

from custom_components.task_wheel.application.wire import to_wire
from custom_components.task_wheel.const.limits import MAX_SUBSCRIPTIONS
from custom_components.task_wheel.domain.errors import LimitReachedError
from custom_components.task_wheel.domain.statistics.report import Standing, WeekRate

from ..domain import factories as f
from .harness import Api
from .test_config import RECURRING


@pytest.fixture
def api() -> Api:
    return Api(0.1)


def test_subscribe_returns_snapshot_and_registers_cleanup(api: Api) -> None:
    reply = api.run("subscribe")
    assert {a["id"] for a in reply.result["assignments"]} == {"a1", "a2"}
    assert reply.on_close is not None
    assert api.pushed == []


def test_changes_arrive_as_deltas_per_object(api: Api) -> None:
    api.run("subscribe")
    api.run("assignment/complete", assignment_id="a1")
    assert len(api.pushed) == 1
    delta = api.pushed[0]
    assert set(delta) == {"assignments", "rounds"}
    assert delta["assignments"] == {"upsert": [], "remove": ["a1"]}
    assert delta["rounds"]["upsert"][0]["done"] == 2


def test_swap_exchanges_assignments_between_persons(api: Api) -> None:
    api.open_partner()
    api.run("subscribe")
    api.run("assignment/swap", assignment_id="a1", to_person_id="p2")
    delta = api.pushed[0]
    upserted = {item["id"]: item["person_id"] for item in delta["assignments"]["upsert"]}
    assert upserted == {"a1": "p2", "a2": "p1"}
    assert "persons" not in delta


def test_config_changes_show_up_and_removals_are_listed(api: Api) -> None:
    api.run("subscribe")
    created = api.result("person/create", person={"name": "Neu"})
    assert [p["id"] for p in api.pushed[-1]["persons"]["upsert"]] == [created["id"]]
    api.run("person/delete", person_id=created["id"])
    assert api.pushed[-1]["persons"] == {"upsert": [], "remove": [created["id"]]}
    api.run("settings/update", settings={"jokers_per_month": 4})
    assert api.pushed[-1]["settings"]["jokers_per_month"] == 4


def test_panel_round_steps_are_pushed(api: Api) -> None:
    api.run("subscribe")
    rid = api.result("draw/begin", schedule_id="s1")["id"]
    assert [r["id"] for r in api.pushed[-1]["panel_rounds"]["upsert"]] == [rid]
    api.run("draw/cancel", panel_round_id=rid)
    assert api.pushed[-1]["panel_rounds"]["remove"] == [rid]


def test_no_push_when_nothing_changed(api: Api) -> None:
    api.run("subscribe")
    api.run("history/list")
    api.data.live.publish()
    assert api.pushed == []


def test_unsubscribe_stops_pushes(api: Api) -> None:
    reply = api.run("subscribe")
    reply.on_close()
    reply.on_close()
    api.run("assignment/complete", assignment_id="a1")
    assert api.pushed == []


def test_second_subscriber_gets_current_state_and_first_gets_missed_delta(api: Api) -> None:
    first: list = []
    api.data.live.subscribe(first.append)
    api.history.put_round(
        f.finished_round(id="r2", assignments=(f.assignment(id="x1", round_id="r2"),))
    )
    snapshot, _ = api.data.live.subscribe(lambda delta: None)
    assert "x1" in snapshot.collections["assignments"]
    assert [a["id"] for a in first[0]["assignments"]["upsert"]] == ["x1"]


def test_subscription_limit(api: Api) -> None:
    for _ in range(MAX_SUBSCRIPTIONS):
        api.run("subscribe")
    with pytest.raises(LimitReachedError):
        api.run("subscribe")


def test_automatic_draw_by_timer_is_pushed(api: Api) -> None:
    created = api.result(
        "schedule/create", schedule={"name": "Plan", "trigger": RECURRING, "task_ids": ["t1"]}
    )
    api.run("subscribe")
    key = f"schedule:{created['id']}"
    planned, _ = api.timers.timers[key]
    api.now = planned
    api.timers.fire(key)
    delta = api.pushed[-1]
    assert len(delta["assignments"]["upsert"]) == 1
    changed = [s["id"] for s in delta["schedules"]["upsert"]]
    assert created["id"] in changed


def test_snapshot_without_subscribers_is_not_kept() -> None:
    api = Api()
    api.data.live.publish()
    assert api.data.live._last is None


def test_to_wire_adds_computed_values() -> None:
    assert to_wire(Standing("p1", 10, 8.0)) == {
        "person_id": "p1",
        "points": 10,
        "fair_points": 8.0,
        "difference": 2.0,
    }
    wired = to_wire(WeekRate(f.TODAY, 3, 1))
    assert wired["rate"] == 0.75
    assert to_wire({"a": (1, frozenset({2}))}) == {"a": [1, [2]]}


def test_observed_timers_pass_through_cancelling(api: Api) -> None:
    created = api.result(
        "schedule/create", schedule={"name": "Plan", "trigger": RECURRING, "task_ids": ["t1"]}
    )
    assert api.timers.timers
    api.data.schedules.disarm(created["id"])
    assert f"schedule:{created['id']}" not in api.timers.timers
    api.data.schedules.disarm_all()
    assert not api.timers.timers


def test_config_changed_anywhere_is_pushed(api: Api) -> None:
    api.run("subscribe")
    api.config.put_person(f.person(id="p3", slug="p3", name="Dritte", absences=()))
    assert [p["id"] for p in api.pushed[-1]["persons"]["upsert"]] == ["p3"]


def test_restricting_access_to_administrators_drops_all_subscribers(api: Api) -> None:
    api.run("subscribe")
    api.run("settings/update", settings={"panel_admin_only": True})
    api.pushed.clear()
    api.run("assignment/complete", assignment_id="a1")
    assert api.pushed == []


def test_other_settings_changes_keep_the_subscribers(api: Api) -> None:
    api.run("subscribe")
    api.run("settings/update", settings={"jokers_per_month": 4})
    api.run("settings/update", settings={"panel_admin_only": False})
    api.pushed.clear()
    api.run("settings/update", settings={"jokers_per_month": 5})
    assert api.pushed
