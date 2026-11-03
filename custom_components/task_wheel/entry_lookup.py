"""Findet die geladene Config Entry (Schicht 2: gemeinsam für Dienste und WebSocket-API)."""

from homeassistant.core import HomeAssistant

from .const.defaults import DOMAIN
from .runtime import TaskWheelData


def loaded_runtime(hass: HomeAssistant) -> TaskWheelData | None:
    """Laufzeitdaten der geladenen Config Entry; `None`, wenn die Integration nicht geladen ist."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        return None
    data: TaskWheelData = entries[0].runtime_data
    return data
