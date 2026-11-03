"""Erkennt, was hinter einem Benachrichtigungsziel steckt (Entität oder Legacy-Dienst)."""

from homeassistant.core import HomeAssistant

from ...const.notification import (
    NOTIFY_DOMAIN,
    NOTIFY_SEND_MESSAGE,
    NOTIFY_TARGET_PATTERN,
    NOTIFY_TARGET_SEPARATOR,
)
from ...domain.enums import NotifyTargetKind


def service_name(target: str) -> str:
    """Name des Legacy-Dienstes (`notify.<name>`) zu einem Ziel."""
    return target.partition(NOTIFY_TARGET_SEPARATOR)[2]


def classify(hass: HomeAssistant, target: str) -> NotifyTargetKind:
    """Art des Ziels jetzt: nur `notify.*`; vorhandene Entität vor Dienst, sonst `none`.

    Der Dienst `notify.send_message` ist kein Ziel, sondern der Weg zu den Entitäten.
    """
    if NOTIFY_TARGET_PATTERN.fullmatch(target) is None:
        return NotifyTargetKind.NONE
    if hass.states.get(target) is not None:
        return NotifyTargetKind.NOTIFY_ENTITY
    name = service_name(target)
    if name != NOTIFY_SEND_MESSAGE and hass.services.has_service(NOTIFY_DOMAIN, name):
        return NotifyTargetKind.NOTIFY_SERVICE
    return NotifyTargetKind.NONE
