"""Gerüsttest: Integration lässt sich hinzufügen und wieder entfernen."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.task_wheel.const import DOMAIN, INTEGRATION_NAME
from custom_components.task_wheel.const.keys import STORE_CONFIG
from custom_components.task_wheel.const.panel import (
    PANEL_DATA_KEY,
    PANEL_ELEMENT_NAME,
    PANEL_STATIC_URL,
    PANEL_URL_PATH,
)


async def test_add_and_remove_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == INTEGRATION_NAME

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_remove(entry.entry_id) == {"require_restart": False}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_second_instance_is_aborted(hass: HomeAssistant) -> None:
    first = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(first["flow_id"], {})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.ABORT


async def test_panel_is_registered_and_removed(hass: HomeAssistant) -> None:
    hass.data[PANEL_DATA_KEY] = f"{PANEL_STATIC_URL}/{PANEL_ELEMENT_NAME}.abc123.js"
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert PANEL_URL_PATH in hass.data["frontend_panels"]

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await hass.config_entries.async_remove(entry.entry_id)
    assert PANEL_URL_PATH not in hass.data["frontend_panels"]


async def test_panel_follows_a_changed_admin_only_setting(hass: HomeAssistant) -> None:
    hass.data[PANEL_DATA_KEY] = f"{PANEL_STATIC_URL}/{PANEL_ELEMENT_NAME}.abc123.js"
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(result["flow_id"], {})
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert hass.data["frontend_panels"][PANEL_URL_PATH].require_admin is False

    entry.runtime_data.configuration.update_settings({"panel_admin_only": True})
    await hass.async_block_till_done()
    assert hass.data["frontend_panels"][PANEL_URL_PATH].require_admin is True

    entry.runtime_data.configuration.update_settings({"jokers_per_month": 3})
    await hass.async_block_till_done()
    assert hass.data["frontend_panels"][PANEL_URL_PATH].require_admin is True


async def test_reloading_the_entry_keeps_one_registered_panel(
    hass: HomeAssistant,
) -> None:
    hass.data[PANEL_DATA_KEY] = f"{PANEL_STATIC_URL}/{PANEL_ELEMENT_NAME}.abc123.js"
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(result["flow_id"], {})
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_reload(entry.entry_id)
    assert PANEL_URL_PATH in hass.data["frontend_panels"]


async def test_damaged_storage_stops_the_setup_with_a_translated_error(
    hass: HomeAssistant, hass_storage: dict[str, object]
) -> None:
    hass_storage[STORE_CONFIG] = {
        "version": 1,
        "minor_version": 4,
        "key": STORE_CONFIG,
        "data": {"persons": "kaputt"},
    }
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    await hass.config_entries.flow.async_configure(result["flow_id"], {})
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert entry.error_reason_translation_key == "storage_corrupt"
