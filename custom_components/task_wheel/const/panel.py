"""Bezeichner des Panels in Home Assistant (KONZEPT §6.5)."""

from typing import Final

from .defaults import DOMAIN

PANEL_ELEMENT_NAME: Final = "task-wheel-panel"
PANEL_URL_PATH: Final = "task-wheel"
PANEL_ICON: Final = "mdi:ferris-wheel"
PANEL_STATIC_URL: Final = f"/{DOMAIN}_static"
PANEL_DIST_DIRECTORY: Final = "frontend/dist"
PANEL_BUNDLE_PATTERN: Final = f"{PANEL_ELEMENT_NAME}.*.js"
PANEL_DATA_KEY: Final = f"{DOMAIN}_panel_module_url"
