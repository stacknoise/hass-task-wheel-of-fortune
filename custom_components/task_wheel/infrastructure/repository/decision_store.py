"""`DecisionStore`: das Entscheidungslog im Speicher, mit gebündeltem Sichern."""

import datetime as dt
import logging
from collections.abc import Iterator, Mapping
from types import MappingProxyType

from ...const import defaults, limits
from ...const.keys import ERR_LIMIT_REACHED, KEY_DECISIONS, STORE_DECISIONS
from ...domain.decisions import DecisionFilter, DecisionRecord
from ...domain.errors import StorageCorruptError
from ...domain.serialization import model_of, tuple_of
from .storage import StoreLike, models_by_id, read_root, read_section

_LOGGER = logging.getLogger(__name__)


class DecisionStore:
    """Implementiert `DecisionRepository`; Einträge liegen nach Entstehung geordnet vor.

    Jede Speicherung kodiert nur neue Einträge, ältere bleiben im Zwischenspeicher kodiert.
    """

    def __init__(self, store: StoreLike) -> None:
        """Startet leer; `async_load` füllt den Bestand."""
        self._store = store
        self._records: dict[str, DecisionRecord] = {}
        self._encoded: dict[str, dict[str, object]] = {}

    @property
    def records(self) -> Mapping[str, DecisionRecord]:
        """Alle Einträge nach Kennung, älteste zuerst (schreibgeschützte Sicht)."""
        return MappingProxyType(self._records)

    async def async_load(self) -> None:
        """Lädt den Bestand; ohne Datei bleibt er leer."""
        raw = await self._store.async_load()
        if raw is None:
            return
        data = read_root(STORE_DECISIONS, raw)
        records = read_section(
            STORE_DECISIONS, data, KEY_DECISIONS, tuple_of(model_of(DecisionRecord))
        )
        if len(records) > limits.MAX_STORED_DECISIONS:
            raise StorageCorruptError(STORE_DECISIONS, ERR_LIMIT_REACHED)
        self._records = dict(sorted(models_by_id(records).items(), key=_at))
        self._encoded = {}

    async def async_flush(self) -> None:
        """Sichert sofort."""
        await self._store.async_save(self._snapshot())

    def add(self, record: DecisionRecord) -> None:
        """Hängt einen Eintrag an; über der Obergrenze entfällt der älteste."""
        if record.id not in self._records and len(self._records) >= limits.MAX_STORED_DECISIONS:
            oldest = next(iter(self._records))
            _LOGGER.warning(
                "Obergrenze für das Entscheidungslog erreicht, ältester Eintrag entfällt"
            )
            self._forget(oldest)
        self._encoded.pop(record.id, None)
        newest = next(reversed(self._records.values()), None)
        self._records[record.id] = record
        if newest is not None and record.at < newest.at:
            self._records = dict(sorted(self._records.items(), key=_at))
        self._changed()

    def query(self, flt: DecisionFilter) -> Iterator[DecisionRecord]:
        """Passende Einträge, der neueste zuerst."""
        for record in reversed(self._records.values()):
            if flt.since is not None and record.at < flt.since:
                return
            if flt.matches(record):
                yield record

    def purge(self, cutoff: dt.datetime) -> int:
        """Entfernt Einträge, die vor `cutoff` entstanden sind."""
        expired = [key for key, record in self._records.items() if record.at < cutoff]
        for key in expired:
            self._forget(key)
        if expired:
            self._changed()
        return len(expired)

    def _forget(self, record_id: str) -> None:
        del self._records[record_id]
        self._encoded.pop(record_id, None)

    def _encode(self, record: DecisionRecord) -> dict[str, object]:
        encoded = self._encoded.get(record.id)
        if encoded is None:
            encoded = self._encoded[record.id] = record.to_dict()
        return encoded

    def _changed(self) -> None:
        self._store.async_delay_save(self._snapshot, defaults.STORE_SAVE_DELAY_SECONDS)

    def _snapshot(self) -> dict[str, object]:
        return {KEY_DECISIONS: [self._encode(item) for item in self._records.values()]}


def _at(entry: tuple[str, DecisionRecord]) -> dt.datetime:
    return entry[1].at
