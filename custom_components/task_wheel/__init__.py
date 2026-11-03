"""Aufgaben-Glücksrad: Aufgaben per Glücksrad fair an Personen verteilen (Schicht 1: Einstieg)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Richtet die Config Entry ein. Das Gerüst (AP-00) hat noch keine Plattformen."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entlädt die Config Entry."""
    return True
