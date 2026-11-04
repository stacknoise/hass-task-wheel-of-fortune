"""Ansichten für das Panel: Gesamtbild (Snapshot), Delta je Objekt und Historieneinträge (§6.4)."""

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from ..const.keys import (
    WIRE_ASSIGNMENTS,
    WIRE_DONE,
    WIRE_EXPIRES_AT,
    WIRE_JOKERS_LEFT,
    WIRE_NEXT_RUN,
    WIRE_NOW,
    WIRE_ORIGIN,
    WIRE_PANEL_ROUNDS,
    WIRE_PENDING,
    WIRE_PERSON_IDS,
    WIRE_PERSONS,
    WIRE_REMOVE,
    WIRE_RESULTS,
    WIRE_ROUNDS,
    WIRE_SCHEDULES,
    WIRE_SETTINGS,
    WIRE_STARTED_AT,
    WIRE_TASKS,
    WIRE_TOTAL,
    WIRE_UPSERT,
    WS_FIELD_SCHEDULE_ID,
)
from ..domain.enums import DONE_STATUSES
from ..domain.models import Assignment, Round, Schedule
from .draw_service import DrawService, PanelRound
from .history_service import HistoryEntry
from .protocols import ConfigRepository, HistoryRepository
from .schedule_service import ScheduleService
from .swap_service import SwapService
from .wire import Json, to_json, to_wire

KEY_ID: Final = "id"
KEY_ASSIGNMENTS: Final = "assignments"
COLLECTIONS: Final = (
    WIRE_PERSONS,
    WIRE_TASKS,
    WIRE_SCHEDULES,
    WIRE_ASSIGNMENTS,
    WIRE_ROUNDS,
    WIRE_PANEL_ROUNDS,
)

type Collection = Mapping[str, Json]


@dataclass(slots=True, frozen=True)
class Snapshot:
    """Stand, den das Panel anzeigt: Sammlungen nach Kennung plus die Einstellungen."""

    collections: Mapping[str, Collection]
    settings: Json
    now: dt.datetime

    def to_wire(self) -> Json:
        """Als Antwort: Listen je Sammlung (Reihenfolge wie im Bestand)."""
        lists = {name: list(items.values()) for name, items in self.collections.items()}
        return {**lists, WIRE_SETTINGS: self.settings, WIRE_NOW: self.now.isoformat()}


def _by_id(items: list[Json]) -> Collection:
    return {str(item[KEY_ID]): item for item in items}


def panel_round_view(panel_round: PanelRound) -> Json:
    """Panel-Runde: bisherige Ziehungen und noch offene Aufgaben (ohne internen Zustand)."""
    draft = panel_round.draft
    return {
        KEY_ID: panel_round.id,
        WS_FIELD_SCHEDULE_ID: draft.schedule_id,
        WIRE_EXPIRES_AT: panel_round.expires_at.isoformat(),
        WIRE_RESULTS: to_wire(draft.results),
        WIRE_PENDING: [task.id for task in draft.pending],
    }


def round_head(round_: Round) -> Json:
    """Kopf einer Runde für die Übersicht: Zeitplan, Beginn, Zahl der erledigten."""
    return {
        KEY_ID: round_.id,
        WS_FIELD_SCHEDULE_ID: round_.schedule_id,
        WIRE_ORIGIN: round_.origin.value,
        WIRE_STARTED_AT: round_.started_at.isoformat(),
        WIRE_TOTAL: len(round_.assignments),
        WIRE_PERSON_IDS: sorted({item.person_id for item in round_.assignments}),
        WIRE_DONE: sum(item.status in DONE_STATUSES for item in round_.assignments),
    }


class SnapshotBuilder:
    """Baut den Snapshot aus Konfiguration, Verlauf und offenen Panel-Runden."""

    def __init__(
        self,
        config: ConfigRepository,
        history: HistoryRepository,
        draws: DrawService,
        swaps: SwapService,
        schedules: ScheduleService,
    ) -> None:
        """Hält die Quellen der Ansicht."""
        self._config = config
        self._history = history
        self._draws = draws
        self._swaps = swaps
        self._schedules = schedules

    def build(self, now: dt.datetime) -> Snapshot:
        """Liest den aktuellen Stand; nur offene Zuteilungen, nicht die ganze Historie."""
        config = self._config
        open_items = self._open_assignments()
        collections = {
            WIRE_PERSONS: _by_id(self._persons(now)),
            WIRE_TASKS: _by_id([to_json(item) for item in config.tasks.values()]),
            WIRE_SCHEDULES: _by_id(
                [self._schedule(item, now) for item in config.schedules.values()]
            ),
            WIRE_ASSIGNMENTS: _by_id([to_json(item) for item in open_items]),
            WIRE_ROUNDS: _by_id(self._open_rounds({item.round_id for item in open_items})),
            WIRE_PANEL_ROUNDS: _by_id(
                [panel_round_view(item) for item in self._draws.open_rounds(now)]
            ),
        }
        return Snapshot(collections, to_json(config.settings), now)

    def _open_assignments(self) -> list[Assignment]:
        """Offene Zuteilungen der bekannten Personen (einmal gelesen für Zuteilungen und Runden)."""
        return [
            item
            for person_id in self._config.persons
            for item in self._history.open_assignments(person_id)
        ]

    def _open_rounds(self, open_ids: set[str]) -> list[Json]:
        """Kopf der Runden mit offenen Zuteilungen (Zeitplan, Beginn, Zahl der erledigten)."""
        return [
            round_head(round_) for round_ in self._history.rounds.values() if round_.id in open_ids
        ]

    def _persons(self, now: dt.datetime) -> list[Json]:
        """Die Personen samt verbleibenden Jokern im laufenden Monat (Zähler einmal für alle)."""
        persons = self._config.persons
        left = self._swaps.jokers_left_for(persons, now)
        return [
            {**to_json(person), WIRE_JOKERS_LEFT: left[person.id]} for person in persons.values()
        ]

    def _schedule(self, schedule: Schedule, now: dt.datetime) -> Json:
        """Der Zeitplan samt nächster automatischer Auslosung (leer bei manuell/pausiert)."""
        upcoming = self._schedules.next_run(schedule, now)
        return {**to_json(schedule), WIRE_NEXT_RUN: upcoming.isoformat() if upcoming else None}


def _collection_delta(before: Collection, after: Collection) -> Json | None:
    """Geänderte und entfernte Objekte einer Sammlung; `None`, wenn alles gleich ist."""
    upsert = [item for key, item in after.items() if before.get(key) != item]
    remove = [key for key in before if key not in after]
    return {WIRE_UPSERT: upsert, WIRE_REMOVE: remove} if upsert or remove else None


def diff(old: Snapshot, new: Snapshot) -> Json:
    """Änderungen von `old` nach `new` je Objekt-Kennung; leer, wenn nichts anders ist."""
    deltas = {
        name: _collection_delta(old.collections[name], new.collections[name])
        for name in COLLECTIONS
    }
    delta: Json = {name: change for name, change in deltas.items() if change is not None}
    if old.settings != new.settings:
        delta[WIRE_SETTINGS] = new.settings
    return delta


def history_entry_view(entry: HistoryEntry) -> Json:
    """Runde mit den Zuteilungen, die zum Filter passen."""
    round_: Round = entry.round
    head = {key: value for key, value in round_.to_dict().items() if key != KEY_ASSIGNMENTS}
    return {**head, KEY_ASSIGNMENTS: [item.to_dict() for item in entry.assignments]}
