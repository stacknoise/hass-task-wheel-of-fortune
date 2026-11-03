"""Ansichten für das Panel: Gesamtbild (Snapshot), Delta je Objekt und Historieneinträge (§6.4)."""

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from ..const.keys import (
    WIRE_ASSIGNMENTS,
    WIRE_EXPIRES_AT,
    WIRE_JOKERS_LEFT,
    WIRE_NEXT_RUN,
    WIRE_NOW,
    WIRE_PANEL_ROUNDS,
    WIRE_PENDING,
    WIRE_PERSONS,
    WIRE_REMOVE,
    WIRE_RESULTS,
    WIRE_SCHEDULES,
    WIRE_SETTINGS,
    WIRE_TASKS,
    WIRE_UPSERT,
)
from ..domain.models import Person, Round, Schedule
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
        "schedule_id": draft.schedule_id,
        WIRE_EXPIRES_AT: panel_round.expires_at.isoformat(),
        WIRE_RESULTS: to_wire(draft.results),
        WIRE_PENDING: [task.id for task in draft.pending],
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
        collections = {
            WIRE_PERSONS: _by_id([self._person(item, now) for item in config.persons.values()]),
            WIRE_TASKS: _by_id([to_json(item) for item in config.tasks.values()]),
            WIRE_SCHEDULES: _by_id(
                [self._schedule(item, now) for item in config.schedules.values()]
            ),
            WIRE_ASSIGNMENTS: _by_id(
                [
                    to_json(item)
                    for person_id in config.persons
                    for item in self._history.open_assignments(person_id)
                ]
            ),
            WIRE_PANEL_ROUNDS: _by_id(
                [panel_round_view(item) for item in self._draws.open_rounds(now)]
            ),
        }
        return Snapshot(collections, to_json(config.settings), now)

    def _person(self, person: Person, now: dt.datetime) -> Json:
        """Die Person samt verbleibenden Jokern im laufenden Monat."""
        return {**to_json(person), WIRE_JOKERS_LEFT: self._swaps.jokers_left(person.id, now)}

    def _schedule(self, schedule: Schedule, now: dt.datetime) -> Json:
        """Der Zeitplan samt nächster automatischer Auslosung (leer bei manuell/pausiert)."""
        upcoming = self._schedules.next_run(schedule, now)
        return {**to_json(schedule), WIRE_NEXT_RUN: upcoming.isoformat() if upcoming else None}


def diff(old: Snapshot, new: Snapshot) -> Json:
    """Änderungen von `old` nach `new` je Objekt-Kennung; leer, wenn nichts anders ist."""
    delta: Json = {}
    for name in COLLECTIONS:
        before, after = old.collections[name], new.collections[name]
        upsert = [item for key, item in after.items() if before.get(key) != item]
        remove = [key for key in before if key not in after]
        if upsert or remove:
            delta[name] = {WIRE_UPSERT: upsert, WIRE_REMOVE: remove}
    if old.settings != new.settings:
        delta[WIRE_SETTINGS] = new.settings
    return delta


def history_entry_view(entry: HistoryEntry) -> Json:
    """Runde mit den Zuteilungen, die zum Filter passen."""
    round_: Round = entry.round
    head = {key: value for key, value in round_.to_dict().items() if key != KEY_ASSIGNMENTS}
    return {**head, KEY_ASSIGNMENTS: [item.to_dict() for item in entry.assignments]}
