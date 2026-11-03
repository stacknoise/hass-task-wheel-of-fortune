"""Migration gespeicherter Daten: je Versionsschritt eine eigene, getestete Funktion."""

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Final

from ...const.keys import STORE_MINOR_VERSION, STORE_VERSION
from ...domain.errors import StorageVersionError

type Version = tuple[int, int]
type Migration = Callable[[dict[str, object]], dict[str, object]]
type Migrations = Mapping[Version, tuple[Version, Migration]]

CURRENT_VERSION: Final[Version] = (STORE_VERSION, STORE_MINOR_VERSION)

# `von-Version -> (nach-Version, Funktion)`; bei Schemaänderungen hier ergänzen.
CONFIG_MIGRATIONS: Final[Migrations] = MappingProxyType({})
HISTORY_MIGRATIONS: Final[Migrations] = MappingProxyType({})


def migrate(
    store: str,
    data: dict[str, object],
    found: Version,
    migrations: Migrations,
    target: Version = CURRENT_VERSION,
) -> dict[str, object]:
    """Führt `data` Schritt für Schritt von `found` nach `target`.

    Fehlt ein Schritt (zu alt, unbekannt oder neuer als `target`), bricht die Migration mit
    `StorageVersionError` ab, ohne Daten zu verändern oder zu verwerfen.
    """
    version = found
    while version != target:
        step = migrations.get(version)
        if step is None:
            raise StorageVersionError(store, ".".join(map(str, found)))
        version, function = step
        data = function(data)
    return data
