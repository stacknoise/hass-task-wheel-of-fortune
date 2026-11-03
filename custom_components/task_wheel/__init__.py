"""Task Wheel of Fortune: Aufgaben per Glücksrad fair verteilen (Schicht 1: Einstieg)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .application.fanout import FanOutRoundEvents
from .application.notification_service import NotificationService
from .const import DOMAIN
from .const.notification import TEXTS_DIRECTORY
from .entities.factory import PLATFORMS
from .entities.signals import EntityEvents
from .infrastructure.events import HassRoundEvents
from .infrastructure.notifier.hass_notifier import HassNotifier
from .infrastructure.notifier.texts import load_catalog
from .infrastructure.panel import async_register_panel, async_register_static, async_remove_panel
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
    await async_register_static(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TaskWheelConfigEntry) -> bool:
    """Lädt den Bestand, verdrahtet die Dienste und setzt die Zeitgeber."""
    config = create_config_store(hass)
    history = create_history_store(hass)
    await config.async_load()
    await history.async_load()
    texts = await hass.async_add_executor_job(
        load_catalog, Path(__file__).parent / TEXTS_DIRECTORY, hass.config.language
    )
    notifications = NotificationService(config, HassNotifier(hass), texts, hass.async_create_task)
    data = compose(
        config,
        history,
        timers=HassTimerScheduler(hass),
        events=FanOutRoundEvents(HassRoundEvents(hass, config), EntityEvents(hass), notifications),
        notifications=notifications,
        clock=dt_util.now,
        spawn=hass.async_create_task,
    )
    entry.runtime_data = data
    await async_register_panel(hass, require_admin=config.settings.panel_admin_only)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    now = data.clock()
    data.schedules.arm_all(now)
    data.maintenance.start(now)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TaskWheelConfigEntry) -> bool:
    """Meldet alle Zeitgeber ab und sichert den Bestand."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    data = entry.runtime_data
    async_remove_panel(hass)
    data.schedules.disarm_all()
    await data.config.async_flush()
    await data.history.async_flush()
    return True
