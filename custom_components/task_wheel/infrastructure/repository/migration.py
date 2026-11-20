"""Migration gespeicherter Daten: je Versionsschritt eine eigene, getestete Funktion."""

import datetime as dt
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Final

from ...const.keys import (
    KEY_AREA_ID,
    KEY_AREA_IDS,
    KEY_ASSIGNMENTS,
    KEY_DEADLINE,
    KEY_DUE_DAYS,
    KEY_FREQUENCY,
    KEY_PERIOD_INDEX,
    KEY_REPLACES,
    KEY_ROUNDS,
    KEY_SCHEDULE_ID,
    KEY_SCHEDULES,
    KEY_SETTINGS,
    KEY_STARTED_AT,
    KEY_TASK_IDS,
    KEY_TASKS,
    KEY_TRIGGER,
    OPT_RETENTION,
    STORE_MINOR_VERSION,
    STORE_VERSION,
)
from ...const.limits import RETENTION_MIN
from ...domain.enums import EntryMode, IntervalUnit
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


def _drop_task_due_days(data: dict[str, object]) -> dict[str, object]:
    """1.4 -> 1.5: die Frist liegt am Zeitplan, `due_days` an der Aufgabe entfällt."""
    tasks = data.get(KEY_TASKS)
    if not isinstance(tasks, list):
        return data
    return {**data, KEY_TASKS: [_without_due_days(item) for item in tasks]}


def _without_due_days(task: object) -> object:
    """Aufgabe ohne `due_days`; Unlesbares bleibt für das Laden stehen."""
    if not isinstance(task, dict):
        return task
    return {key: value for key, value in task.items() if key != KEY_DUE_DAYS}


def _default_start() -> str:
    """Beginn eines umgestellten Zeitplans ohne festen Termin: jetzt, auf die Stunde gerundet."""
    return dt.datetime.now(dt.UTC).replace(minute=0, second=0, microsecond=0).isoformat()


def _plan_fields(
    schedule: dict[str, object], tasks: Mapping[object, dict[str, object]]
) -> dict[str, object]:
    """Beginn, Intervall, Modus und Aufgaben des neuen Zeitplans aus Auslöser und Häufigkeiten."""
    trigger = schedule.get(KEY_TRIGGER)
    kind = trigger.get("kind") if isinstance(trigger, dict) else None
    weeks = trigger.get("every_n_weeks") if isinstance(trigger, dict) else None
    start = trigger.get("at") if kind == "once" and isinstance(trigger, dict) else _default_start()
    unit, every = (
        (IntervalUnit.WEEK.value, weeks) if isinstance(weeks, int) else (IntervalUnit.DAY.value, 1)
    )
    task_ids = schedule.get(KEY_TASK_IDS)
    ids = task_ids if isinstance(task_ids, list) else []
    entries = [_entry(task_id, tasks.get(task_id, {})) for task_id in ids]
    return {
        "start": start,
        "interval": {"unit": unit, "every": every},
        "automatic": kind in {"recurring", "once"},
        "entries": entries,
    }


def _entry(task_id: object, task: dict[str, object]) -> dict[str, object]:
    """Eintrag einer Aufgabe: „jede Auslosung“ oder mindestens so oft, wie ihre Regel erlaubte."""
    rule = task.get(KEY_FREQUENCY)
    kind = rule.get("kind") if isinstance(rule, dict) else None
    count = rule.get("count") if isinstance(rule, dict) else None
    if kind == "every_round":
        return {"task_id": task_id, "mode": EntryMode.EVERY_DRAW.value}
    mode = {"task_id": task_id, "mode": EntryMode.MIN_COUNT.value}
    return {**mode, "min_count": count} if isinstance(count, int) and count > 0 else mode


def _schedule_plan(data: dict[str, object]) -> dict[str, object]:
    """1.5 -> 1.6: Häufigkeit, Auslöser und Frist wandern an den Zeitplan (Beginn, Intervall, Lauf).

    Die alten Felder entfallen; der Zeitplan beginnt jetzt (einmalige: zum alten Termin), die
    Aufgaben übernehmen ihre bisherige Häufigkeit als Mindestanzahl.
    """
    schedules, tasks = data.get(KEY_SCHEDULES), data.get(KEY_TASKS)
    if not isinstance(schedules, list) or not isinstance(tasks, list):
        return data
    by_id = {t.get("id"): t for t in tasks if isinstance(t, dict)}
    removed = {KEY_TRIGGER, KEY_DEADLINE, KEY_TASK_IDS}
    return {
        **data,
        KEY_SCHEDULES: [
            {k: v for k, v in item.items() if k not in removed} | _plan_fields(item, by_id)
            if isinstance(item, dict)
            else item
            for item in schedules
        ],
        KEY_TASKS: [
            {k: v for k, v in item.items() if k != KEY_FREQUENCY}
            if isinstance(item, dict)
            else item
            for item in tasks
        ],
    }


def _round_periods(data: dict[str, object]) -> dict[str, object]:
    """1.5 -> 1.6: Runden erhalten ihre Periodennummer je Zeitplan, `replaces` entfällt."""
    rounds = data.get(KEY_ROUNDS)
    if not isinstance(rounds, list):
        return data
    ordered = sorted(
        (item for item in rounds if isinstance(item, dict)),
        key=lambda item: str(item.get(KEY_STARTED_AT)),
    )
    counters: dict[object, int] = {}
    numbered: dict[int, int] = {}
    for item in ordered:
        schedule_id = item.get(KEY_SCHEDULE_ID)
        numbered[id(item)] = counters.get(schedule_id, 0)
        counters[schedule_id] = numbered[id(item)] + 1
    return {
        **data,
        KEY_ROUNDS: [
            {k: v for k, v in item.items() if k != KEY_REPLACES}
            | {KEY_PERIOD_INDEX: numbered[id(item)]}
            if isinstance(item, dict)
            else item
            for item in rounds
        ],
    }


# `von-Version -> (nach-Version, Funktion)`; bei Schemaänderungen hier ergänzen.
CONFIG_MIGRATIONS: Final[Migrations] = MappingProxyType(
    {
        (1, 1): ((1, 2), _unchanged),
        (1, 2): ((1, 3), _task_areas),
        (1, 3): ((1, 4), _retention_floor),
        (1, 4): ((1, 5), _drop_task_due_days),
        (1, 5): ((1, 6), _schedule_plan),
    }
)
HISTORY_MIGRATIONS: Final[Migrations] = MappingProxyType(
    {
        (1, 1): ((1, 2), _assignment_schedule),
        (1, 2): ((1, 3), _unchanged),
        (1, 3): ((1, 4), _unchanged),
        (1, 4): ((1, 5), _unchanged),
        (1, 5): ((1, 6), _round_periods),
    }
)
# Das Entscheidungslog entstand mit Version 1.4 und kennt keine älteren Stände
DECISION_MIGRATIONS: Final[Migrations] = MappingProxyType(
    {(1, 4): ((1, 5), _unchanged), (1, 5): ((1, 6), _unchanged)}
)


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
