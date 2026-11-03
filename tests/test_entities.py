"""Sensoren, To-do-Listen und Buttons gegen Home Assistant (läuft in der CI)."""

import datetime as dt

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.task_wheel.const import DOMAIN
from custom_components.task_wheel.const.entities import (
    KEY_BUTTON_DRAW,
    KEY_SENSOR_NEXT_DRAW,
    KEY_SENSOR_OPEN,
    KEY_SENSOR_POINTS,
    KEY_TODO_TASKS,
)
from custom_components.task_wheel.domain.enums import AssignmentStatus
from custom_components.task_wheel.domain.models import OnceTrigger
from custom_components.task_wheel.entities.base import device_name, unique_id
from custom_components.task_wheel.runtime import TaskWheelData

from .domain import factories as f
from .test_integration import _setup

DAY = dt.timedelta(days=1)


def _entity_id(hass: HomeAssistant, domain: str, item_id: str, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id(item_id, key))


def _state(hass: HomeAssistant, domain: str, item_id: str, key: str) -> str:
    entity_id = _entity_id(hass, domain, item_id, key)
    assert entity_id is not None, (domain, item_id, key)
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


async def _press_draw(hass: HomeAssistant, schedule_id: str = "s1") -> None:
    entity_id = _entity_id(hass, "button", schedule_id, KEY_BUTTON_DRAW)
    await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done()


async def _drawn_owner(hass: HomeAssistant, data: TaskWheelData) -> str:
    """Zieht eine Runde über den Button und liefert die Person, die die Aufgabe bekam."""
    await _press_draw(hass)
    (round_,) = data.history.rounds.values()
    (assignment,) = round_.assignments
    return assignment.person_id


async def test_entities_exist_for_persons_and_schedules(hass: HomeAssistant) -> None:
    await _setup(hass)
    await hass.async_block_till_done()
    for person in ("p1", "p2"):
        assert _state(hass, "sensor", person, KEY_SENSOR_OPEN) == "0"
        assert _state(hass, "sensor", person, KEY_SENSOR_POINTS) == "0"
        assert _state(hass, "todo", person, KEY_TODO_TASKS) == "0"
    assert _state(hass, "sensor", "s1", KEY_SENSOR_NEXT_DRAW) == "unknown"
    assert _entity_id(hass, "button", "s1", KEY_BUTTON_DRAW) is not None


async def test_draw_button_updates_open_sensor_and_todo(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    await hass.async_block_till_done()
    owner = await _drawn_owner(hass, data)
    other = "p2" if owner == "p1" else "p1"
    assert _state(hass, "sensor", owner, KEY_SENSOR_OPEN) == "1"
    assert _state(hass, "todo", owner, KEY_TODO_TASKS) == "1"
    assert _state(hass, "sensor", other, KEY_SENSOR_OPEN) == "0"


async def test_completing_the_todo_item_completes_the_assignment(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    await hass.async_block_till_done()
    owner = await _drawn_owner(hass, data)
    (assignment,) = next(iter(data.history.rounds.values())).assignments
    await hass.services.async_call(
        "todo",
        "update_item",
        {
            "entity_id": _entity_id(hass, "todo", owner, KEY_TODO_TASKS),
            "item": assignment.id,
            "status": "completed",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    done = data.history.get_assignment(assignment.id)
    assert done is not None and done.status is AssignmentStatus.ON_TIME
    assert _state(hass, "todo", owner, KEY_TODO_TASKS) == "0"
    assert _state(hass, "sensor", owner, KEY_SENSOR_OPEN) == "0"
    assert _state(hass, "sensor", owner, KEY_SENSOR_POINTS) == str(assignment.points)


async def test_todo_only_accepts_completion(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    await hass.async_block_till_done()
    owner = await _drawn_owner(hass, data)
    (assignment,) = next(iter(data.history.rounds.values())).assignments
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": _entity_id(hass, "todo", owner, KEY_TODO_TASKS),
                "item": assignment.id,
                "rename": "etwas anderes",
            },
            blocking=True,
        )
    assert data.history.get_assignment(assignment.id).status is AssignmentStatus.OPEN  # type: ignore[union-attr]


async def test_swap_updates_both_persons(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    await hass.async_block_till_done()
    owner = await _drawn_owner(hass, data)
    other = "p2" if owner == "p1" else "p1"
    (assignment,) = next(iter(data.history.rounds.values())).assignments
    await hass.services.async_call(
        DOMAIN, "swap", {"assignment_id": assignment.id, "to_person": other}, blocking=True
    )
    await hass.async_block_till_done()
    assert _state(hass, "sensor", owner, KEY_SENSOR_OPEN) == "0"
    assert _state(hass, "sensor", other, KEY_SENSOR_OPEN) == "1"


async def test_next_draw_sensor_follows_the_trigger(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    at = data.clock() + DAY
    data.schedules.save(f.schedule(trigger=OnceTrigger(at=at), task_ids=("t1",)), data.clock())
    await hass.async_block_till_done()
    assert dt_util.parse_datetime(_state(hass, "sensor", "s1", KEY_SENSOR_NEXT_DRAW)) == at
    data.schedules.save(
        f.schedule(trigger=OnceTrigger(at=at), task_ids=("t1",), enabled=False), data.clock()
    )
    await hass.async_block_till_done()
    assert _state(hass, "sensor", "s1", KEY_SENSOR_NEXT_DRAW) == "unknown"


async def test_deleted_person_and_schedule_lose_entities_and_devices(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    await hass.async_block_till_done()
    devices = dr.async_get(hass)
    assert devices.async_get_device(identifiers={(DOMAIN, "p2")}) is not None
    data.config.remove_person("p2")
    data.schedules.delete("s1")
    await hass.async_block_till_done()
    for domain, item, key in (
        ("sensor", "p2", KEY_SENSOR_OPEN),
        ("sensor", "p2", KEY_SENSOR_POINTS),
        ("todo", "p2", KEY_TODO_TASKS),
        ("sensor", "s1", KEY_SENSOR_NEXT_DRAW),
        ("button", "s1", KEY_BUTTON_DRAW),
    ):
        assert _entity_id(hass, domain, item, key) is None
    assert devices.async_get_device(identifiers={(DOMAIN, "p2")}) is None
    assert devices.async_get_device(identifiers={(DOMAIN, "s1")}) is None
    assert devices.async_get_device(identifiers={(DOMAIN, "p1")}) is not None
    assert _entity_id(hass, "todo", "p1", KEY_TODO_TASKS) is not None


async def test_renamed_person_renames_the_device(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    await hass.async_block_till_done()
    data.config.put_person(f.person(id="p1", slug="anna", name="Annabelle", absences=()))
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "p1")})
    assert device is not None and device.name == device_name("Annabelle")


async def test_archived_schedule_has_no_button(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    await hass.async_block_till_done()
    data.schedules.save(
        f.schedule(
            task_ids=("t1",),
            trigger=data.config.schedules["s1"].trigger,
            enabled=False,
            archived=True,
        ),
        data.clock(),
    )
    await hass.async_block_till_done()
    assert _entity_id(hass, "button", "s1", KEY_BUTTON_DRAW) is None


async def test_entry_unloads_and_reloads_with_entities(hass: HomeAssistant) -> None:
    entry, _ = await _setup(hass)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
