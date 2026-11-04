"""Panel-API gegen Home Assistant: Rechte, Fehlerantworten und Abonnement (läuft in der CI)."""

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.task_wheel.const import DOMAIN
from custom_components.task_wheel.domain.enums import AssignmentStatus
from custom_components.task_wheel.runtime import TaskWheelData

from .domain import factories as f
from .test_integration import _open_assignment, _setup

CONFIG_COMMANDS = [
    ("task_wheel/person/create", {"person": {"name": "Neu"}}),
    ("task_wheel/person/update", {"person_id": "p1", "person": {"color": "#112233"}}),
    ("task_wheel/person/delete", {"person_id": "p1"}),
    ("task_wheel/task/create", {"task": {"name": "Neu", "allowed": ["p1"]}}),
    ("task_wheel/task/update", {"task_id": "t1", "task": {"points": 2}}),
    ("task_wheel/task/delete", {"task_id": "t1"}),
    (
        "task_wheel/schedule/create",
        {"schedule": {"name": "Neu", "trigger": {"kind": "manual"}, "task_ids": ["t1"]}},
    ),
    ("task_wheel/schedule/update", {"schedule_id": "s1", "schedule": {"enabled": False}}),
    ("task_wheel/schedule/delete", {"schedule_id": "s1"}),
    ("task_wheel/settings/update", {"settings": {"jokers_per_month": 3}}),
]


async def _call(client: Any, command: str, **fields: Any) -> dict[str, Any]:
    await client.send_json_auto_id({"type": command, **fields})
    return await client.receive_json()


@pytest.mark.parametrize(("command", "fields"), CONFIG_COMMANDS)
async def test_non_admin_cannot_configure(
    hass: HomeAssistant, hass_ws_client: Any, hass_read_only_access_token: str, command, fields
) -> None:
    _, data = await _setup(hass)
    before = (dict(data.config.persons), dict(data.config.tasks), dict(data.config.schedules))
    client = await hass_ws_client(hass, hass_read_only_access_token)
    msg = await _call(client, command, **fields)
    assert msg["success"] is False
    assert msg["error"]["code"] == "unauthorized"
    after = (dict(data.config.persons), dict(data.config.tasks), dict(data.config.schedules))
    assert before == after


async def test_admin_can_configure(hass: HomeAssistant, hass_ws_client: Any) -> None:
    _, data = await _setup(hass)
    client = await hass_ws_client(hass)
    msg = await _call(client, "task_wheel/person/create", person={"name": "Carla"})
    assert msg["success"] is True
    assert msg["result"]["slug"] == "carla"
    assert msg["result"]["id"] in data.config.persons
    msg = await _call(client, "task_wheel/settings/update", settings={"jokers_per_month": 3})
    assert msg["result"]["jokers_per_month"] == 3


async def test_non_admin_can_read_complete_and_swap(
    hass: HomeAssistant, hass_ws_client: Any, hass_read_only_access_token: str
) -> None:
    _, data = await _setup(hass)
    assignment_id = _open_assignment(data, AssignmentStatus.OPEN)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    snapshot = await _call(client, "task_wheel/snapshot")
    assert snapshot["success"] is True
    assert {a["id"] for a in snapshot["result"]["assignments"]} == {assignment_id, "a2"}
    swapped = await _call(
        client, "task_wheel/assignment/swap", assignment_id=assignment_id, to_person_id="p2"
    )
    assert swapped["result"]["person_id"] == "p2"
    done = await _call(client, "task_wheel/assignment/complete", assignment_id=assignment_id)
    assert done["result"]["status"] in {"on_time", "late"}
    page = await _call(client, "task_wheel/history/list")
    assert page["success"] is True
    stats = await _call(client, "task_wheel/statistics/get")
    assert stats["success"] is True


async def test_non_admin_can_draw_in_panel(
    hass: HomeAssistant, hass_ws_client: Any, hass_read_only_access_token: str
) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    begun = await _call(
        client,
        "task_wheel/draw/begin",
        schedule_id="s1",
        starts_at=f.NOW.isoformat(),
        duration=3,
        duration_unit="day",
    )
    rid = begun["result"]["id"]
    spun = await _call(client, "task_wheel/draw/spin_rest", panel_round_id=rid)
    assert spun["success"] is True
    committed = await _call(client, "task_wheel/draw/commit", panel_round_id=rid)
    assert committed["result"]["origin"] == "manual"


async def test_unknown_and_extra_fields_are_rejected(
    hass: HomeAssistant, hass_ws_client: Any
) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    extra = await _call(client, "task_wheel/snapshot", extra=1)
    assert extra["error"]["code"] == "invalid_format"
    too_long = await _call(client, "task_wheel/person/create", person={"name": "x" * 1000})
    assert too_long["error"]["code"] == "invalid_format"
    unknown_field = await _call(
        client, "task_wheel/person/create", person={"name": "Neu", "admin": True}
    )
    assert unknown_field["error"]["code"] == "invalid_format"


async def test_domain_errors_are_answered_with_their_key(
    hass: HomeAssistant, hass_ws_client: Any
) -> None:
    await _setup(hass)
    client = await hass_ws_client(hass)
    missing = await _call(client, "task_wheel/assignment/complete", assignment_id="nope")
    assert missing["success"] is False
    assert missing["error"]["code"] == "not_found"
    invalid = await _call(client, "task_wheel/person/create", person={"name": "Neu", "color": "x"})
    assert invalid["error"]["code"] == "invalid_format"


async def test_panel_admin_only_blocks_non_admins(
    hass: HomeAssistant, hass_ws_client: Any, hass_read_only_access_token: str
) -> None:
    _, data = await _setup(hass)
    data.config.set_settings(f.settings(panel_admin_only=True))
    client = await hass_ws_client(hass, hass_read_only_access_token)
    msg = await _call(client, "task_wheel/snapshot")
    assert msg["error"]["code"] == "unauthorized"


async def test_commands_report_not_loaded_without_entry(
    hass: HomeAssistant, hass_ws_client: Any
) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)
    msg = await _call(client, "task_wheel/snapshot")
    assert msg["success"] is False
    assert msg["error"]["code"] == "not_loaded"


async def test_subscribe_sends_deltas_until_unsubscribed(
    hass: HomeAssistant, hass_ws_client: Any
) -> None:
    _, data = await _setup(hass)
    assignment_id = _open_assignment(data)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "task_wheel/subscribe"})
    first = await client.receive_json()
    assert first["success"] is True
    assert [a["id"] for a in first["result"]["assignments"]] == [assignment_id]
    subscription = first["id"]

    await hass.services.async_call(
        DOMAIN, "complete", {"assignment_id": assignment_id}, blocking=True
    )
    event = await client.receive_json()
    assert event["type"] == "event"
    assert event["id"] == subscription
    assert event["event"]["assignments"] == {"upsert": [], "remove": [assignment_id]}

    await client.send_json_auto_id({"type": "unsubscribe_events", "subscription": subscription})
    assert (await client.receive_json())["success"] is True
    assert not _listeners(data)


async def test_closing_the_connection_unsubscribes(
    hass: HomeAssistant, hass_ws_client: Any
) -> None:
    _, data = await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "task_wheel/subscribe"})
    await client.receive_json()
    assert len(_listeners(data)) == 1
    await client.close()
    await hass.async_block_till_done()
    assert not _listeners(data)


async def test_changes_made_elsewhere_are_pushed(hass: HomeAssistant, hass_ws_client: Any) -> None:
    _, data = await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "task_wheel/subscribe"})
    await client.receive_json()
    data.config.set_settings(f.settings(jokers_per_month=4))
    settings_event = await client.receive_json()
    assert settings_event["event"]["settings"]["jokers_per_month"] == 4
    await hass.services.async_call(DOMAIN, "draw", {"schedule": "wochenplan"}, blocking=True)
    drawn_event = await client.receive_json()
    assert len(drawn_event["event"]["assignments"]["upsert"]) == 1


def _listeners(data: TaskWheelData) -> dict[int, Any]:
    return data.live._listeners
