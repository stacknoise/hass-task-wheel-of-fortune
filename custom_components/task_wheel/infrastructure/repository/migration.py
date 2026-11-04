"""Migration gespeicherter Daten: je Versionsschritt eine eigene, getestete Funktion."""

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Final

from ...const.keys import (
    KEY_AREA_ID,
    KEY_AREA_IDS,
    KEY_ASSIGNMENTS,
    KEY_ROUNDS,
    KEY_SCHEDULE_ID,
    KEY_SETTINGS,
    KEY_TASKS,
    OPT_RETENTION,
    STORE_MINOR_VERSION,
    STORE_VERSION,
)
from ...const.limits import RETENTION_MIN
from ...domain.errors import StorageVersionError

type Version = tuple[int, int]
type Migration = Callable[[dict[str, object]], dict[str, object]]
type Migrations = Mapping[Version, tuple[Version, Migration]]

CURRENT_VERSION: Final[Version] = (STORE_VERSION, STORE_MINOR_VERSION)


def _unchanged(data: dict[str, object]) -> dict[str, object]:
    """Schritt ohne Schemaänderung (beide Stores teilen sich die Versionsnummer)."""
    return data


def _assignment_schedule(data: dict[str, object]) -> dict[str, object]:
    """1.1 -> 1.2: Zuteilungen erhalten den Zeitplan ihrer Runde (`schedule_id`)."""
    rounds = data.get(KEY_ROUNDS)
    if not isinstance(rounds, list):
        return data
    return {**data, KEY_ROUNDS: [_with_schedule(item) for item in rounds]}


def _with_schedule(round_: object) -> object:
    """Runde mit `schedule_id` an jeder Zuteilung; Unlesbares bleibt für das Laden stehen."""
    if not isinstance(round_, dict) or not isinstance(round_.get(KEY_ASSIGNMENTS), list):
        return round_
    schedule_id = round_.get(KEY_SCHEDULE_ID)
    return {
        **round_,
        KEY_ASSIGNMENTS: [
            {KEY_SCHEDULE_ID: schedule_id, **item} if isinstance(item, dict) else item
            for item in round_[KEY_ASSIGNMENTS]
        ],
    }


def _task_areas(data: dict[str, object]) -> dict[str, object]:
    """1.2 -> 1.3: der eine Raum einer Aufgabe (`area_id`) wird zur Liste `area_ids`."""
    tasks = data.get(KEY_TASKS)
    if not isinstance(tasks, list):
        return data
    return {**data, KEY_TASKS: [_with_area_list(item) for item in tasks]}


def _with_area_list(task: object) -> object:
    """Aufgabe mit `area_ids` statt `area_id`; Unlesbares bleibt für das Laden stehen."""
    if not isinstance(task, dict):
        return task
    legacy = task.get(KEY_AREA_ID)
    rest = {key: value for key, value in task.items() if key != KEY_AREA_ID}
    if KEY_AREA_IDS in rest:
        return rest
    return {**rest, KEY_AREA_IDS: [legacy] if isinstance(legacy, str) and legacy else []}


def _retention_floor(data: dict[str, object]) -> dict[str, object]:
    """1.3 -> 1.4: zu kurze Aufbewahrung wird auf das Minimum angehoben (`RETENTION_MIN`)."""
    settings = data.get(KEY_SETTINGS)
    if not isinstance(settings, dict):
        return data
    days = settings.get(OPT_RETENTION)
    if not isinstance(days, int) or isinstance(days, bool) or days >= RETENTION_MIN:
        return data
    return {**data, KEY_SETTINGS: {**settings, OPT_RETENTION: RETENTION_MIN}}


# `von-Version -> (nach-Version, Funktion)`; bei Schemaänderungen hier ergänzen.
CONFIG_MIGRATIONS: Final[Migrations] = MappingProxyType(
    {
        (1, 1): ((1, 2), _unchanged),
        (1, 2): ((1, 3), _task_areas),
        (1, 3): ((1, 4), _retention_floor),
    }
)
HISTORY_MIGRATIONS: Final[Migrations] = MappingProxyType(
    {
        (1, 1): ((1, 2), _assignment_schedule),
        (1, 2): ((1, 3), _unchanged),
        (1, 3): ((1, 4), _unchanged),
    }
)
# Das Entscheidungslog entstand mit Version 1.4 und kennt keine älteren Stände
DECISION_MIGRATIONS: Final[Migrations] = MappingProxyType({})


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
