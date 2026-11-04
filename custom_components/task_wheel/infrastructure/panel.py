"""Meldet das Panel „Glücksrad“ in der Seitenleiste von Home Assistant an (KONZEPT §6.5)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig

from ..const.defaults import GERMAN_LANGUAGE_PREFIX, INTEGRATION_NAME, INTEGRATION_NAME_DE
from ..const.panel import (
    PANEL_DATA_KEY,
    PANEL_DIST_DIRECTORY,
    PANEL_ELEMENT_NAME,
    PANEL_ICON,
    PANEL_STATIC_URL,
    PANEL_URL_PATH,
)
from .panel_bundle import find_bundle_name

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER: Final = logging.getLogger(__name__)
DIST_DIRECTORY: Final = Path(__file__).parent.parent / PANEL_DIST_DIRECTORY


async def async_register_static(hass: HomeAssistant, directory: Path = DIST_DIRECTORY) -> None:
    """Stellt das gebaute Bundle unter einer festen Adresse bereit (einmal je Start).

    Fehlt das Bundle (nicht gebaut), bleibt die Integration nutzbar, nur das Panel fehlt.
    """
    bundle = await hass.async_add_executor_job(find_bundle_name, directory)
    if bundle is None:
        _LOGGER.warning("Panel-Bundle fehlt in %s; bitte das Frontend bauen", directory)
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_STATIC_URL, str(directory), cache_headers=True)]
    )
    hass.data[PANEL_DATA_KEY] = f"{PANEL_STATIC_URL}/{bundle}"


def sidebar_title(language: str) -> str:
    """Titel der Seitenleiste: Home Assistant übersetzt Panel-Titel nicht, daher je Systemsprache."""
    return INTEGRATION_NAME_DE if language.startswith(GERMAN_LANGUAGE_PREFIX) else INTEGRATION_NAME


async def async_register_panel(hass: HomeAssistant, *, require_admin: bool) -> None:
    """Zeigt das Panel in der Seitenleiste; ohne Bundle geschieht nichts."""
    module_url = hass.data.get(PANEL_DATA_KEY)
    if module_url is None:
        return
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_ELEMENT_NAME,
        frontend_url_path=PANEL_URL_PATH,
        module_url=module_url,
        sidebar_title=sidebar_title(hass.config.language),
        sidebar_icon=PANEL_ICON,
        require_admin=require_admin,
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    """Entfernt das Panel aus der Seitenleiste (beim Entladen)."""
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
