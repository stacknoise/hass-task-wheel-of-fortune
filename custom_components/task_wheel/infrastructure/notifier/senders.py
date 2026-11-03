"""Versandarten als Strategien: eine Klasse je Art des Ziels."""

from typing import Protocol

from homeassistant.core import HomeAssistant

from ...const.notification import (
    NOTIFY_DOMAIN,
    NOTIFY_FIELD_ENTITY,
    NOTIFY_FIELD_MESSAGE,
    NOTIFY_FIELD_TITLE,
    NOTIFY_SEND_MESSAGE,
)
from ...domain.errors import InvalidNotifyTargetError
from .target import service_name


class Sender(Protocol):
    """Schickt Titel und Nachricht an ein Ziel dieser Art."""

    async def send(self, target: str, title: str, message: str) -> None:
        """Wartet, bis der Dienst fertig ist; Fehler kommen als Ausnahme."""
        ...


class EntitySender:
    """`notify.send_message` für eine `notify`-Entität."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Merkt sich Home Assistant."""
        self._hass = hass

    async def send(self, target: str, title: str, message: str) -> None:
        """Ruft `notify.send_message` mit `entity_id` auf."""
        await self._hass.services.async_call(
            NOTIFY_DOMAIN,
            NOTIFY_SEND_MESSAGE,
            {NOTIFY_FIELD_ENTITY: target, NOTIFY_FIELD_TITLE: title, NOTIFY_FIELD_MESSAGE: message},
            blocking=True,
        )


class ServiceSender:
    """Legacy-Dienst `notify.<name>`."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Merkt sich Home Assistant."""
        self._hass = hass

    async def send(self, target: str, title: str, message: str) -> None:
        """Ruft den Dienst `notify.<name>` auf."""
        await self._hass.services.async_call(
            NOTIFY_DOMAIN,
            service_name(target),
            {NOTIFY_FIELD_TITLE: title, NOTIFY_FIELD_MESSAGE: message},
            blocking=True,
        )


class NoSender:
    """Für unbekannte Ziele: sendet nichts und meldet das Ziel als ungültig."""

    async def send(self, target: str, title: str, message: str) -> None:  # noqa: ARG002
        """Lehnt ab."""
        raise InvalidNotifyTargetError(target)
