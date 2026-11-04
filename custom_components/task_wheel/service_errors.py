"""Fachliche Fehler als übersetzbare Home-Assistant-Fehler (für Dienste und Entitäten)."""

from homeassistant.exceptions import ConfigEntryError, ServiceValidationError

from .const.defaults import DOMAIN
from .domain.errors import TaskWheelError


def _placeholders(err: TaskWheelError) -> dict[str, str]:
    """Platzhalter der Übersetzung als Text."""
    return {key: str(value) for key, value in err.placeholders.items()}


def to_service_error(err: TaskWheelError) -> ServiceValidationError:
    """Macht aus einem fachlichen Fehler einen übersetzbaren Dienstfehler."""
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=err.key,
        translation_placeholders=_placeholders(err),
    )


def to_setup_error(err: TaskWheelError) -> ConfigEntryError:
    """Macht aus einem fachlichen Fehler beim Laden einen übersetzbaren Einrichtungsfehler."""
    return ConfigEntryError(
        translation_domain=DOMAIN,
        translation_key=err.key,
        translation_placeholders=_placeholders(err),
    )
