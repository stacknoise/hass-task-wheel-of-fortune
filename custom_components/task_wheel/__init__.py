"""Aufgaben-Glücksrad: Aufgaben per Glücksrad fair an Personen verteilen (Schicht 1: Einstieg)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .infrastructure.events import HassRoundEvents
from .infrastructure.repository.factory import create_config_store, create_history_store
from .infrastructure.scheduler import HassTimerScheduler
from .runtime import TaskWheelData, compose
from .services import async_register_services
from .websocket import async_register_commands

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

type TaskWheelConfigEntry = ConfigEntry[TaskWheelData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Meldet Dienste und WebSocket-Befehle an; sie gehören nicht einer einzelnen Config Entry."""
    async_register_services(hass)
    async_register_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TaskWheelConfigEntry) -> bool:
    """Lädt den Bestand, verdrahtet die Dienste und setzt die Zeitgeber."""
    config = create_config_store(hass)
    history = create_history_store(hass)
    await config.async_load()
    await history.async_load()
    data = compose(
        config,
        history,
        timers=HassTimerScheduler(hass),
        events=HassRoundEvents(hass, config),
        clock=dt_util.now,
        spawn=hass.async_create_task,
    )
    entry.runtime_data = data
    now = data.clock()
    data.schedules.arm_all(now)
    data.maintenance.start(now)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TaskWheelConfigEntry) -> bool:
    """Meldet alle Zeitgeber ab und sichert den Bestand."""
    data = entry.runtime_data
    data.schedules.disarm_all()
    await data.config.async_flush()
    await data.history.async_flush()
    return True
