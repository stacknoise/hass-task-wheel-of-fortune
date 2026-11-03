"""`HistoryStore`: Runden, Zuteilungen und Monatsaggregate samt Indizes im Speicher."""

import datetime as dt
from collections.abc import Iterator, Mapping
from types import MappingProxyType

from ...const import defaults, limits
from ...const.keys import ERR_LIMIT_REACHED, KEY_AGGREGATES, KEY_ROUNDS, STORE_HISTORY
from ...domain.errors import LimitReachedError, StorageCorruptError
from ...domain.models import Assignment, Round
from ...domain.serialization import as_mapping, model_of, tuple_of
from ...domain.status import PENDING_STATUSES
from ...domain.types import AssignmentId, PersonId, RoundId, TaskId
from .storage import StoreLike, models_by_id, read_root, read_section

_RESOURCE_ROUND = "round"


def _decode_aggregates(value: object) -> dict[str, object]:
    """Aggregate sind ein Objekt; die Struktur darin gehört dem Statistik-Service."""
    return dict(as_mapping(value))


class HistoryStore:
    """Implementiert `HistoryRepository`.

    Indizes (`Zuteilung -> Runde`, offene Zuteilungen je Person, Zuteilungen je Aufgabe)
    werden bei jeder Änderung einer Runde nachgeführt statt die Historie zu durchlaufen.
    """

    def __init__(self, store: StoreLike) -> None:
        """Startet leer; `async_load` füllt Bestand und Indizes."""
        self._store = store
        self._rounds: dict[RoundId, Round] = {}
        self._aggregates: dict[str, object] = {}
        self._assignments: dict[AssignmentId, tuple[Round, Assignment]] = {}
        self._open: dict[PersonId, dict[AssignmentId, Assignment]] = {}
        self._by_task: dict[TaskId, dict[AssignmentId, tuple[Round, Assignment]]] = {}

    @property
    def rounds(self) -> Mapping[RoundId, Round]:
        """Alle Runden nach Kennung, älteste zuerst (schreibgeschützte Sicht)."""
        return MappingProxyType(self._rounds)

    @property
    def aggregates(self) -> Mapping[str, object]:
        """Monatsaggregate (schreibgeschützte Sicht)."""
        return MappingProxyType(self._aggregates)

    async def async_load(self) -> None:
        """Lädt den Bestand und baut die Indizes; ohne Datei bleibt er leer."""
        raw = await self._store.async_load()
        if raw is None:
            return
        data = read_root(STORE_HISTORY, raw)
        rounds = read_section(STORE_HISTORY, data, KEY_ROUNDS, tuple_of(model_of(Round)))
        self._aggregates = read_section(STORE_HISTORY, data, KEY_AGGREGATES, _decode_aggregates)
        if len(rounds) > limits.MAX_STORED_ROUNDS:
            raise StorageCorruptError(STORE_HISTORY, ERR_LIMIT_REACHED)
        self._rounds = dict(sorted(models_by_id(rounds).items(), key=_started))
        self._assignments, self._open, self._by_task = {}, {}, {}
        for round_ in self._rounds.values():
            self._index(round_)

    async def async_flush(self) -> None:
        """Sichert sofort."""
        await self._store.async_save(self._snapshot())

    def put_round(self, round_: Round) -> None:
        """Legt eine Runde an oder ersetzt sie samt Zuteilungen und führt die Indizes nach."""
        previous = self._rounds.get(round_.id)
        if previous is None and len(self._rounds) >= limits.MAX_STORED_ROUNDS:
            raise LimitReachedError(_RESOURCE_ROUND, limits.MAX_STORED_ROUNDS)
        if previous is not None:
            self._unindex(previous)
        needs_sort = self._breaks_order(round_, previous)
        self._rounds[round_.id] = round_
        if needs_sort:
            self._rounds = dict(sorted(self._rounds.items(), key=_started))
        self._index(round_)
        self._changed()

    def remove_round(self, round_id: RoundId) -> Round | None:
        """Entfernt eine Runde samt Zuteilungen und Indizes; liefert sie oder `None`."""
        round_ = self._rounds.pop(round_id, None)
        if round_ is not None:
            self._unindex(round_)
            self._changed()
        return round_

    def set_aggregates(self, aggregates: Mapping[str, object]) -> None:
        """Ersetzt die Monatsaggregate."""
        self._aggregates = dict(aggregates)
        self._changed()

    def get_assignment(self, assignment_id: AssignmentId) -> Assignment | None:
        """Sucht eine Zuteilung über den Index."""
        entry = self._assignments.get(assignment_id)
        return None if entry is None else entry[1]

    def open_assignments(self, person_id: PersonId) -> tuple[Assignment, ...]:
        """Offene Zuteilungen einer Person über den Index."""
        return tuple(self._open.get(person_id, {}).values())

    def last_assignment(self, task_id: TaskId) -> Assignment | None:
        """Jüngste Zuteilung einer Aufgabe (nach Rundenbeginn)."""
        entries = self._by_task.get(task_id)
        if not entries:
            return None
        return max(entries.values(), key=lambda entry: entry[0].started_at)[1]

    def rounds_since(self, since: dt.datetime) -> Iterator[Round]:
        """Runden, die ab `since` begonnen haben, die neueste zuerst."""
        for round_ in reversed(self._rounds.values()):
            if round_.started_at < since:
                return
            yield round_

    def assignments_since(self, since: dt.datetime) -> tuple[Assignment, ...]:
        """Zuteilungen aus Runden, die ab `since` begonnen haben (neueste Runde zuerst)."""
        return tuple(
            assignment for round_ in self.rounds_since(since) for assignment in round_.assignments
        )

    async def async_purge(self, cutoff: dt.datetime) -> int:
        """Entfernt Runden, die vor `cutoff` begonnen haben, und sichert bei Änderungen."""
        expired = [r for r in self._rounds.values() if r.started_at < cutoff]
        for round_ in expired:
            self._unindex(round_)
            del self._rounds[round_.id]
        if expired:
            self._changed()
        return len(expired)

    def _breaks_order(self, round_: Round, previous: Round | None) -> bool:
        """Prüft, ob das Einfügen die Sortierung nach Rundenbeginn stören würde."""
        if previous is not None:
            return previous.started_at != round_.started_at
        newest = next(reversed(self._rounds.values()), None)
        return newest is not None and round_.started_at < newest.started_at

    def _index(self, round_: Round) -> None:
        for assignment in round_.assignments:
            self._assignments[assignment.id] = (round_, assignment)
            self._by_task.setdefault(assignment.task_id, {})[assignment.id] = (round_, assignment)
            if assignment.status in PENDING_STATUSES:
                self._open.setdefault(assignment.person_id, {})[assignment.id] = assignment

    def _unindex(self, round_: Round) -> None:
        for assignment in round_.assignments:
            self._assignments.pop(assignment.id, None)
            self._by_task.get(assignment.task_id, {}).pop(assignment.id, None)
            self._open.get(assignment.person_id, {}).pop(assignment.id, None)

    def _changed(self) -> None:
        self._store.async_delay_save(self._snapshot, defaults.STORE_SAVE_DELAY_SECONDS)

    def _snapshot(self) -> dict[str, object]:
        return {
            KEY_ROUNDS: [item.to_dict() for item in self._rounds.values()],
            KEY_AGGREGATES: self._aggregates,
        }


def _started(entry: tuple[RoundId, Round]) -> dt.datetime:
    return entry[1].started_at
