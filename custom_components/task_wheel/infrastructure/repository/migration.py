"""Migration gespeicherter Daten: je Versionsschritt eine eigene, getestete Funktion."""

import datetime as dt
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Final

from ...const.defaults import DEFAULT_RUN_DAYS
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
from ...const.limits import HOURS_PER_DAY, RETENTION_MIN
from ...domain.enums import INTERVAL_UNIT_HOURS, EntryMode, IntervalUnit
from ...domain.errors import StorageVersionError

type Version = tuple[int, int]
type Migration = Callable[[dict[str, object]], dict[str, object]]
type Migrations = Mapping[Version, tuple[Version, Migration]]

# Schlüssel und Werte des alten und des neuen Speicherstands (nur hier, nur für die Umstellung)
LEGACY_KIND: Final = "kind"
LEGACY_EVERY_N_WEEKS: Final = "every_n_weeks"
LEGACY_AT: Final = "at"
LEGACY_COUNT: Final = "count"
LEGACY_ONCE: Final = "once"
LEGACY_RECURRING: Final = "recurring"
LEGACY_EVERY_ROUND: Final = "every_round"
LEGACY_PERIOD: Final = "period"
LEGACY_EVERY: Final = "every"
LEGACY_DAYS: Final = "days"
LEGACY_DAY: Final = "day"
LEGACY_PERIOD_DAYS: Final = MappingProxyType({"day": 1, "week": 7, "month": 30})
NEW_START: Final = "start"
NEW_INTERVAL: Final = "interval"
NEW_AUTOMATIC: Final = "automatic"
NEW_ENTRIES: Final = "entries"
NEW_UNIT: Final = "unit"
NEW_EVERY: Final = "every"
NEW_TASK_ID: Final = "task_id"
NEW_MODE: Final = "mode"
NEW_MIN_COUNT: Final = "min_count"

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


def _interval_of(trigger: dict[str, object]) -> tuple[str, int]:
    """Einheit und Anzahl des neuen Intervalls: „alle n Wochen“ bleibt, sonst täglich."""
    weeks = trigger.get(LEGACY_EVERY_N_WEEKS)
    if isinstance(weeks, int):
        return IntervalUnit.WEEK.value, weeks
    return IntervalUnit.DAY.value, 1


def _plan_fields(
    schedule: dict[str, object], tasks: Mapping[object, dict[str, object]]
) -> dict[str, object]:
    """Beginn, Intervall, Modus und Aufgaben des neuen Zeitplans aus Auslöser und Häufigkeiten."""
    raw = schedule.get(KEY_TRIGGER)
    trigger = raw if isinstance(raw, dict) else {}
    kind = trigger.get(LEGACY_KIND)
    start = trigger.get(LEGACY_AT) if kind == LEGACY_ONCE else _default_start()
    unit, every = _interval_of(trigger)
    task_ids = schedule.get(KEY_TASK_IDS)
    ids = task_ids if isinstance(task_ids, list) else []
    draws = max(
        1, DEFAULT_RUN_DAYS * HOURS_PER_DAY // (INTERVAL_UNIT_HOURS[IntervalUnit(unit)] * every)
    )
    return {
        NEW_START: start,
        NEW_INTERVAL: {NEW_UNIT: unit, NEW_EVERY: every},
        NEW_AUTOMATIC: kind in {LEGACY_RECURRING, LEGACY_ONCE},
        NEW_ENTRIES: [_entry(task_id, tasks.get(task_id, {}), draws) for task_id in ids],
    }


def _per_run(rule: dict[str, object], draws: int) -> int:
    """Wie oft die alte Regel eine Aufgabe in einem Lauf erlaubte (mindestens 1, höchstens `draws`).

    „Höchstens n-mal je x Tage/Wochen/Monate“ und „alle d Tage“ werden auf die Läufe der
    Standardlänge umgerechnet (Monat = 30 Tage); ohne lesbare Angaben zählt die Regel als einmal.
    """
    period_days = LEGACY_PERIOD_DAYS.get(str(rule.get(LEGACY_PERIOD)))
    every, count, days = (rule.get(k) for k in (LEGACY_EVERY, LEGACY_COUNT, LEGACY_DAYS))
    if isinstance(days, int) and days > 0:
        wanted = DEFAULT_RUN_DAYS // days
    elif isinstance(count, int) and isinstance(every, int | None) and period_days:
        wanted = DEFAULT_RUN_DAYS * count // (period_days * (every or 1))
    else:
        wanted = 1
    return max(1, min(wanted, draws))


def _is_daily(rule: dict[str, object]) -> bool:
    """Die alte Regel „höchstens n-mal in 1 Tag“: die Aufgabe kam in jeder Runde vor."""
    return rule.get(LEGACY_PERIOD) == LEGACY_DAY and rule.get(LEGACY_EVERY, 1) == 1


def _entry(task_id: object, task: dict[str, object], draws: int) -> dict[str, object]:
    """Eintrag einer Aufgabe: „jede Auslosung“ oder so oft je Lauf, wie ihre Regel erlaubte."""
    raw = task.get(KEY_FREQUENCY)
    rule = raw if isinstance(raw, dict) else {}
    if rule.get(LEGACY_KIND) == LEGACY_EVERY_ROUND or _is_daily(rule):
        return {NEW_TASK_ID: task_id, NEW_MODE: EntryMode.EVERY_DRAW.value}
    return {
        NEW_TASK_ID: task_id,
        NEW_MODE: EntryMode.MIN_COUNT.value,
        NEW_MIN_COUNT: _per_run(rule, draws),
    }


def _without(
    item: object, removed: set[str], extra: Callable[[dict[str, object]], dict[str, object]]
) -> object:
    """Eintrag ohne die entfernten Felder, ergänzt um `extra(item)`; Fremdes bleibt unverändert."""
    if not isinstance(item, dict):
        return item
    return {k: v for k, v in item.items() if k not in removed} | extra(item)


def _schedule_plan(data: dict[str, object]) -> dict[str, object]:
    """1.5 -> 1.6: Häufigkeit, Auslöser und Frist wandern an den Zeitplan (Beginn, Intervall, Lauf).

    Die alten Felder entfallen; der Zeitplan beginnt jetzt (einmalige: zum alten Termin), die
    Aufgaben übernehmen ihre bisherige Häufigkeit als Mindestanzahl.
    """
    schedules, tasks = data.get(KEY_SCHEDULES), data.get(KEY_TASKS)
    if not isinstance(schedules, list) or not isinstance(tasks, list):
        return data
    by_id = {t.get("id"): t for t in tasks if isinstance(t, dict)}
    return {
        **data,
        KEY_SCHEDULES: [
            _without(
                item, {KEY_TRIGGER, KEY_DEADLINE, KEY_TASK_IDS}, lambda i: _plan_fields(i, by_id)
            )
            for item in schedules
        ],
        KEY_TASKS: [_without(item, {KEY_FREQUENCY}, lambda _: {}) for item in tasks],
    }


def _period_numbers(rounds: list[object]) -> dict[int, int]:
    """Periodennummer je Runde (nach `id()`): Reihenfolge des Starts innerhalb des Zeitplans."""
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
    return numbered


def _round_periods(data: dict[str, object]) -> dict[str, object]:
    """1.5 -> 1.6: Runden erhalten ihre Periodennummer je Zeitplan, `replaces` entfällt."""
    rounds = data.get(KEY_ROUNDS)
    if not isinstance(rounds, list):
        return data
    numbered = _period_numbers(rounds)
    return {
        **data,
        KEY_ROUNDS: [
            _without(item, {KEY_REPLACES}, lambda i: {KEY_PERIOD_INDEX: numbered[id(i)]})
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
