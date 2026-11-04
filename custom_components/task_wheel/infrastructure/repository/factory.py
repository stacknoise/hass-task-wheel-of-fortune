"""Fabrik der Repositories über Home-Assistant-`Store` mit Migration."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ...const.keys import (
    STORE_CONFIG,
    STORE_DECISIONS,
    STORE_HISTORY,
    STORE_MINOR_VERSION,
    STORE_VERSION,
)
from .config_store import ConfigStore
from .decision_store import DecisionStore
from .history_store import HistoryStore
from .migration import (
    CONFIG_MIGRATIONS,
    DECISION_MIGRATIONS,
    HISTORY_MIGRATIONS,
    Migrations,
    migrate,
)


class MigratingStore(Store[dict[str, object]]):
    """`Store`, der ältere Versionen über die Migrationstabelle hebt."""

    def __init__(self, hass: HomeAssistant, key: str, migrations: Migrations) -> None:
        """Legt den Speicher mit aktueller Haupt- und Nebenversion an."""
        super().__init__(hass, STORE_VERSION, key, minor_version=STORE_MINOR_VERSION)
        self._migrations = migrations

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, object]:
        """Wird von `Store` bei abweichender Version aufgerufen."""
        return migrate(self.key, old_data, (old_major_version, old_minor_version), self._migrations)


def create_config_store(hass: HomeAssistant) -> ConfigStore:
    """Erzeugt das Konfigurations-Repository."""
    return ConfigStore(MigratingStore(hass, STORE_CONFIG, CONFIG_MIGRATIONS))


def create_history_store(hass: HomeAssistant) -> HistoryStore:
    """Erzeugt das Verlaufs-Repository."""
    return HistoryStore(MigratingStore(hass, STORE_HISTORY, HISTORY_MIGRATIONS))


def create_decision_store(hass: HomeAssistant) -> DecisionStore:
    """Erzeugt das Repository des Entscheidungslogs."""
    return DecisionStore(MigratingStore(hass, STORE_DECISIONS, DECISION_MIGRATIONS))
