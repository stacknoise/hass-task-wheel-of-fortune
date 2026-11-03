"""`Notifier` für Home Assistant: prüft das Ziel beim Speichern und beim Senden."""

import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from ...const.notification import NOTIFY_TIMEOUT_SECONDS
from ...domain.enums import NotifyTargetKind
from ...domain.errors import InvalidNotifyTargetError, NotifyFailedError
from .factory import NotifierFactory
from .target import classify


class HassNotifier:
    """Erkennt die Art des Ziels bei jedem Aufruf neu (Entitäten und Dienste kommen und gehen)."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Merkt sich Home Assistant."""
        self._hass = hass

    def check(self, target: str) -> None:
        """Lehnt Ziele ab, die es nicht gibt oder die nicht zu `notify` gehören."""
        if classify(self._hass, target) is NotifyTargetKind.NONE:
            raise InvalidNotifyTargetError(target)

    async def async_send(self, target: str, title: str, message: str) -> None:
        """Sendet mit Zeitlimit; Fehler des Dienstes werden zu `NotifyFailedError`."""
        sender = NotifierFactory.create(classify(self._hass, target), self._hass)
        try:
            async with asyncio.timeout(NOTIFY_TIMEOUT_SECONDS):
                await sender.send(target, title, message)
        except (HomeAssistantError, TimeoutError) as err:
            raise NotifyFailedError(target) from err
