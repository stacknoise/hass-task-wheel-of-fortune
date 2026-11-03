"""Zeitgeber auf Basis von `async_track_point_in_time` (umsetzt das Protokoll `TimerPort`)."""

import datetime as dt

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_time

from ..application.protocols import FireCallback


class HassTimerScheduler:
    """Hält je Schlüssel höchstens einen Zeitgeber und meldet alle beim Entladen ab."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Merkt sich die HA-Instanz."""
        self._hass = hass
        self._cancels: dict[str, CALLBACK_TYPE] = {}

    def schedule(self, key: str, at: dt.datetime, callback_: FireCallback) -> None:
        """Setzt den Zeitgeber `key` neu; die Auslösung läuft im Ereignisschleifen-Thread."""
        self.cancel(key)

        @callback
        def _fire(fired: dt.datetime) -> None:
            self._cancels.pop(key, None)
            callback_(fired)

        self._cancels[key] = async_track_point_in_time(self._hass, _fire, at)

    def cancel(self, key: str) -> None:
        """Meldet den Zeitgeber ab, falls es ihn gibt."""
        cancel = self._cancels.pop(key, None)
        if cancel is not None:
            cancel()

    def cancel_all(self) -> None:
        """Meldet alle Zeitgeber ab."""
        for key in tuple(self._cancels):
            self.cancel(key)
