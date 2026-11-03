"""HassTimerScheduler gegen die Zeitgeber von Home Assistant (läuft nur mit HA, d. h. in der CI)."""

import datetime as dt

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.task_wheel.infrastructure.scheduler import HassTimerScheduler

HOUR = dt.timedelta(hours=1)


async def test_timer_fires_once_at_the_set_time(hass: HomeAssistant) -> None:
    scheduler = HassTimerScheduler(hass)
    fired: list[dt.datetime] = []
    at = dt_util.utcnow() + HOUR
    scheduler.schedule("a", at, fired.append)

    async_fire_time_changed(hass, at - dt.timedelta(seconds=1))
    await hass.async_block_till_done()
    assert fired == []

    async_fire_time_changed(hass, at + dt.timedelta(seconds=1))
    await hass.async_block_till_done()
    async_fire_time_changed(hass, at + 2 * HOUR)
    await hass.async_block_till_done()
    assert len(fired) == 1


async def test_scheduling_the_same_key_again_replaces_the_timer(hass: HomeAssistant) -> None:
    scheduler = HassTimerScheduler(hass)
    fired: list[str] = []
    at = dt_util.utcnow() + HOUR
    scheduler.schedule("a", at, lambda _now: fired.append("old"))
    scheduler.schedule("a", at + HOUR, lambda _now: fired.append("new"))

    async_fire_time_changed(hass, at + dt.timedelta(seconds=1))
    await hass.async_block_till_done()
    assert fired == []

    async_fire_time_changed(hass, at + HOUR + dt.timedelta(seconds=1))
    await hass.async_block_till_done()
    assert fired == ["new"]


async def test_cancel_and_cancel_all_stop_timers(hass: HomeAssistant) -> None:
    scheduler = HassTimerScheduler(hass)
    fired: list[str] = []
    at = dt_util.utcnow() + HOUR
    for key in ("a", "b", "c"):
        scheduler.schedule(key, at, lambda _now, key=key: fired.append(key))
    scheduler.cancel("a")
    scheduler.cancel("unbekannt")
    scheduler.cancel_all()

    async_fire_time_changed(hass, at + HOUR)
    await hass.async_block_till_done()
    assert fired == []
