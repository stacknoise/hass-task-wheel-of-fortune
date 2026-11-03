"""Config Flow: Einzelinstanz ohne Eingaben (Optionen folgen in AP-09)."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, INTEGRATION_NAME

STEP_USER = "user"


class TaskWheelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Legt die Integration mit einem Klick an."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Erster Schritt: Hinweis anzeigen, nach Bestätigung Einzelinstanz anlegen."""
        if user_input is None:
            return self.async_show_form(step_id=STEP_USER)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=INTEGRATION_NAME, data={})
