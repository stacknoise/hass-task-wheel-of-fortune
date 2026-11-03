"""Config Flow (Einzelinstanz) und Options Flow (Einstellungen, KONZEPT §4, §11)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, Final

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import DOMAIN, INTEGRATION_NAME
from .const import limits as lim
from .const.keys import (
    ABORT_NOT_LOADED,
    OPT_FAIRNESS_WINDOW,
    OPT_GRACE_HOURS,
    OPT_JOKERS,
    OPT_LATE_FACTOR,
    OPT_MISSED_FACTOR,
    OPT_PANEL_ADMIN_ONLY,
    OPT_RETENTION,
    STEP_INIT,
)
from .domain.errors import ValidationError

if TYPE_CHECKING:
    from . import TaskWheelConfigEntry
    from .domain.models import Settings

STEP_USER: Final = "user"
ERROR_BASE: Final = "base"
INTEGER_STEP: Final = 1
FACTOR_STEP: Final = 0.05

type Range = tuple[float, float, float]

# Eingabefelder: Name -> (Untergrenze, Obergrenze, Schrittweite); Grenzen aus `const/limits.py`
NUMBER_FIELDS: Final[dict[str, Range]] = {
    OPT_JOKERS: (lim.JOKERS_MIN, lim.JOKERS_MAX, INTEGER_STEP),
    OPT_FAIRNESS_WINDOW: (lim.FAIRNESS_WINDOW_MIN, lim.FAIRNESS_WINDOW_MAX, INTEGER_STEP),
    OPT_RETENTION: (lim.RETENTION_MIN, lim.RETENTION_MAX, INTEGER_STEP),
    OPT_LATE_FACTOR: (lim.LATE_FACTOR_MIN, lim.LATE_FACTOR_MAX, FACTOR_STEP),
    OPT_MISSED_FACTOR: (lim.MISSED_FACTOR_MIN, lim.MISSED_FACTOR_MAX, FACTOR_STEP),
    OPT_GRACE_HOURS: (lim.GRACE_HOURS_MIN, lim.GRACE_HOURS_MAX, INTEGER_STEP),
}
INTEGER_FIELDS: Final = frozenset({OPT_JOKERS, OPT_FAIRNESS_WINDOW, OPT_RETENTION, OPT_GRACE_HOURS})


def _number(name: str, default: float) -> tuple[vol.Marker, NumberSelector]:
    """Zahlenfeld mit Grenzen und Vorgabewert."""
    low, high, step = NUMBER_FIELDS[name]
    config = NumberSelectorConfig(min=low, max=high, step=step, mode=NumberSelectorMode.BOX)
    return vol.Required(name, default=default), NumberSelector(config)


def options_schema(settings: Settings) -> vol.Schema:
    """Formular mit den aktuellen Einstellungen als Vorgabe."""
    fields = dict(_number(name, getattr(settings, name)) for name in NUMBER_FIELDS)
    fields[vol.Required(OPT_PANEL_ADMIN_ONLY, default=settings.panel_admin_only)] = (
        BooleanSelector()
    )
    return vol.Schema(fields)


def apply_options(settings: Settings, user_input: dict[str, Any]) -> Settings:
    """Übernimmt die Eingaben (Zahlen als int, wo das Modell ganze Zahlen verlangt).

    Raises:
        ValidationError: Ein Wert verletzt die Grenzen des Modells.
    """
    values: dict[str, Any] = {
        name: int(value) if name in INTEGER_FIELDS else value for name, value in user_input.items()
    }
    return replace(settings, **values)


class TaskWheelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Legt die Integration mit einem Klick an."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> TaskWheelOptionsFlow:
        """Einstellungen nach dem Anlegen."""
        return TaskWheelOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Erster Schritt: Hinweis anzeigen, nach Bestätigung Einzelinstanz anlegen."""
        if user_input is None:
            return self.async_show_form(step_id=STEP_USER)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=INTEGRATION_NAME, data={})


class TaskWheelOptionsFlow(OptionsFlow):
    """Ändert die Einstellungen im Speicher der Integration (dieselbe Quelle wie das Panel)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Zeigt die Einstellungen und speichert sie nach Prüfung der Grenzen."""
        entry: TaskWheelConfigEntry = self.config_entry
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason=ABORT_NOT_LOADED)
        config = entry.runtime_data.config
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                config.set_settings(apply_options(config.settings, user_input))
            except ValidationError as err:
                errors[ERROR_BASE] = err.key
            else:
                return self.async_create_entry(data={})
        return self.async_show_form(
            step_id=STEP_INIT, data_schema=options_schema(config.settings), errors=errors
        )
