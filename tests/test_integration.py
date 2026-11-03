"""Einstieg, Dienste, Events, Zeitgeber und Options Flow gegen Home Assistant (läuft in der CI)."""

import datetime as dt

import pytest
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.task_wheel.const import DOMAIN
from custom_components.task_wheel.const.events import (
    EVENT_ANIMATE,
    EVENT_COMPLETED,
    EVENT_DRAWN,
    EVENT_SWAPPED,
)
from custom_components.task_wheel.domain.enums import AssignmentStatus
from custom_components.task_wheel.domain.errors import InvalidNotifyTargetError
from custom_components.task_wheel.domain.models import (
    EveryRound,
    ManualTrigger,
    OnceAbsence,
    Recurring,
)
from custom_components.task_wheel.runtime import TaskWheelData

from .domain import factories as f

DAY = dt.timedelta(days=1)


async def _setup(hass: HomeAssistant) -> tuple[ConfigEntry, TaskWheelData]:
    """Legt die Integration über den Config Flow an und füllt Personen, Aufgabe und Zeitplan."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    data: TaskWheelData = entry.runtime_data
    for ident, slug in (("p1", "anna"), ("p2", "ben")):
        data.config.put_person(f.person(id=ident, slug=slug, name=slug.title(), absences=()))
    data.config.put_task(f.task(frequency=EveryRound()))
    data.config.put_schedule(
        f.schedule(trigger=ManualTrigger(), task_ids=("t1",), slug="wochenplan")
    )
    return entry, data


def _open_assignment(data: TaskWheelData) -> str:
    """Eine offene Zuteilung für p1 mit Frist in einer Woche."""
    now = data.clock()
    item = f.assignment(id="a1", round_id="r1", person_id="p1", due_at=now + 7 * DAY)
    data.history.put_round(
        f.finished_round(id="r1", started_at=now, finished_at=now, assignments=(item,))
    )
    return item.id


async def test_draw_service_fires_drawn_and_animate_events(hass: HomeAssistant) -> None:
    await _setup(hass)
    drawn = async_capture_events(hass, EVENT_DRAWN)
    animate = async_capture_events(hass, EVENT_ANIMATE)
    await hass.services.async_call(
        DOMAIN,
        "draw",
        {"schedule": "wochenplan", "animate_on": "sensor.display"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert len(drawn) == 1
    assert drawn[0].data["schedule_name"] == "Wochenrunde"
    assert drawn[0].data["origin"] == "service"
    assert drawn[0].data["assignments"][0]["task_name"] == "Müll"
    assert len(animate) == 1
    assert animate[0].data["animate_on"] == "sensor.display"


async def test_draw_sends_notifications_to_legacy_service_and_entity(hass: HomeAssistant) -> None:
    legacy = async_mock_service(hass, "notify", "mobile_app_anna")
    entity = async_mock_service(hass, "notify", "send_message")
    hass.states.async_set("notify.ben_phone", "unknown")
    _, data = await _setup(hass)
    for ident, slug, target in (
        ("p1", "anna", "notify.mobile_app_anna"),
        ("p2", "ben", "notify.ben_phone"),
    ):
        person = f.person(id=ident, slug=slug, name=slug.title(), absences=(), notify_target=target)
        data.config.put_person(person)
    await hass.services.async_call(DOMAIN, "draw", {"schedule": "wochenplan"}, blocking=True)
    await hass.async_block_till_done()
    assert [call.data["title"] for call in legacy] == ["New tasks: Wochenrunde"]
    assert "Müll" in legacy[0].data["message"]
    assert [call.data["entity_id"] for call in entity] == ["notify.ben_phone"]


async def test_notification_target_is_checked(hass: HomeAssistant) -> None:
    async_mock_service(hass, "notify", "mobile_app_anna")
    _, data = await _setup(hass)
    data.notifications.check_target(None)
    data.notifications.check_target("notify.mobile_app_anna")
    with pytest.raises(InvalidNotifyTargetError):
        data.notifications.check_target("notify.gone")
    with pytest.raises(InvalidNotifyTargetError):
        data.notifications.check_target("script.turn_on")


async def test_draw_without_animate_fires_no_animation(hass: HomeAssistant) -> None:
    await _setup(hass)
    animate = async_capture_events(hass, EVENT_ANIMATE)
    await hass.services.async_call(DOMAIN, "draw", {"schedule": "s1"}, blocking=True)
    await hass.async_block_till_done()
    assert animate == []


async def test_complete_by_id_and_by_person_and_task(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    completed = async_capture_events(hass, EVENT_COMPLETED)
    assignment_id = _open_assignment(data)
    await hass.services.async_call(
        DOMAIN, "complete", {"person": "anna", "task": "Müll"}, blocking=True
    )
    assert data.history.get_assignment(assignment_id).status is not AssignmentStatus.OPEN  # type: ignore[union-attr]
    await hass.async_block_till_done()
    assert len(completed) == 1
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "complete", {"assignment_id": assignment_id}, blocking=True
        )


async def test_complete_needs_exactly_one_target(hass: HomeAssistant) -> None:
    await _setup(hass)
    for payload in ({}, {"person": "anna"}, {"assignment_id": "a1", "person": "anna", "task": "x"}):
        with pytest.raises(vol.Invalid):
            await hass.services.async_call(DOMAIN, "complete", payload, blocking=True)


async def test_swap_service_hands_over_and_fires_event(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    swapped = async_capture_events(hass, EVENT_SWAPPED)
    assignment_id = _open_assignment(data)
    await hass.services.async_call(
        DOMAIN, "swap", {"assignment_id": assignment_id, "to_person": "ben"}, blocking=True
    )
    await hass.async_block_till_done()
    assert data.history.get_assignment(assignment_id).person_id == "p2"  # type: ignore[union-attr]
    assert swapped[0].data["from_person_name"] == "Anna"


async def test_swap_to_unknown_person_is_a_translated_error(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    assignment_id = _open_assignment(data)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "swap", {"assignment_id": assignment_id, "to_person": "zoe"}, blocking=True
        )
    assert err.value.translation_key == "not_found"


async def test_set_absence_adds_once_absence_and_drops_expired(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    today = data.clock().date()
    old = OnceAbsence(start=today - 9 * DAY, end=today - 8 * DAY)
    data.config.put_person(f.person(id="p1", slug="anna", name="Anna", absences=(old,)))
    await hass.services.async_call(
        DOMAIN,
        "set_absence",
        {"person": "anna", "start": today.isoformat(), "end": (today + DAY).isoformat()},
        blocking=True,
    )
    assert data.config.persons["p1"].absences == (OnceAbsence(start=today, end=today + DAY),)


async def test_set_absence_with_reversed_dates_is_rejected(hass: HomeAssistant) -> None:
    _, data = await _setup(hass)
    today = data.clock().date()
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN,
            "set_absence",
            {"person": "anna", "start": today.isoformat(), "end": (today - DAY).isoformat()},
            blocking=True,
        )
    assert err.value.translation_key == "invalid_order"


async def test_unknown_fields_are_rejected(hass: HomeAssistant) -> None:
    await _setup(hass)
    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, "draw", {"schedule": "s1", "extra": 1}, blocking=True
        )


async def test_services_report_not_loaded_after_unload(hass: HomeAssistant) -> None:
    entry, _ = await _setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, "draw", {"schedule": "s1"}, blocking=True)
    assert err.value.translation_key == "not_loaded"


async def test_timers_are_armed_on_save_and_cancelled_on_unload(hass: HomeAssistant) -> None:
    entry, data = await _setup(hass)
    drawn = async_capture_events(hass, EVENT_DRAWN)
    now = data.clock()
    trigger = Recurring(weekdays=frozenset(range(7)), time=(now + dt.timedelta(hours=2)).time())
    schedule = f.schedule(trigger=trigger, task_ids=("t1",))
    data.schedules.save(schedule, now)
    at = data.schedules.next_run(schedule, now)
    assert at is not None

    async_fire_time_changed(hass, at + dt.timedelta(seconds=1))
    await hass.async_block_till_done()
    assert [event.data["origin"] for event in drawn] == ["auto"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    async_fire_time_changed(hass, at + 2 * DAY)
    await hass.async_block_till_done()
    assert len(drawn) == 1


async def test_options_flow_updates_settings(hass: HomeAssistant) -> None:
    entry, data = await _setup(hass)
    form = await hass.config_entries.options.async_init(entry.entry_id)
    assert form["type"] == "form"
    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            "jokers_per_month": 3,
            "fairness_window_days": 14,
            "history_retention_days": 90,
            "late_points_factor": 0.5,
            "missed_points_factor": -0.5,
            "missed_grace_hours": 12,
            "panel_admin_only": True,
        },
    )
    assert result["type"] == "create_entry"
    settings = data.config.settings
    assert (settings.jokers_per_month, settings.fairness_window_days) == (3, 14)
    assert (settings.late_points_factor, settings.missed_points_factor) == (0.5, -0.5)
    assert settings.panel_admin_only is True


async def test_options_flow_aborts_when_not_loaded(hass: HomeAssistant) -> None:
    entry, _ = await _setup(hass)
    await hass.config_entries.async_unload(entry.entry_id)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "abort"
    assert result["reason"] == "not_loaded"
