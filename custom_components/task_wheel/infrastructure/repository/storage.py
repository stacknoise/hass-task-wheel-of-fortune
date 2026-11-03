"""Schmale Sicht auf `homeassistant.helpers.storage.Store` und gemeinsame Speicherlogik."""

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Protocol

from ...const.keys import ERR_REQUIRED, ERR_TYPE
from ...domain.errors import (
    LimitReachedError,
    NotFoundError,
    StorageCorruptError,
    ValidationError,
)
from ...domain.serialization import Decoder, Model, as_mapping


class StoreLike(Protocol):
    """Der von den Repositories genutzte Teil von `Store` (in Tests ersetzbar)."""

    async def async_load(self) -> Any:  # noqa: ANN401 - Store liefert untypisierte JSON-Daten
        """Lädt die gespeicherten Daten (oder `None`)."""
        ...

    async def async_save(self, data: Any) -> None:  # noqa: ANN401
        """Schreibt sofort."""
        ...

    def async_delay_save(self, data_func: Callable[[], Any], delay: float = 0) -> None:
        """Plant gebündeltes Schreiben."""
        ...


def read_section[T](store: str, data: Mapping[str, object], key: str, decode: Decoder[T]) -> T:
    """Liest einen Abschnitt; Fehler werden zu `StorageCorruptError` mit Feldpfad."""
    try:
        if key not in data:
            raise ValidationError("", ERR_REQUIRED)
        return decode(data[key])
    except ValidationError as err:
        raise StorageCorruptError(store, str(err.with_parent(key))) from err


def read_root(store: str, raw: object) -> Mapping[str, object]:
    """Prüft, dass die Wurzel ein Objekt ist."""
    try:
        return as_mapping(raw)
    except ValidationError as err:
        raise StorageCorruptError(store, ERR_TYPE) from err


def models_by_id[M: Model](items: Iterable[M]) -> dict[str, M]:
    """Indiziert Modelle nach `id` (Reihenfolge bleibt erhalten)."""
    return {item.id: item for item in items}  # type: ignore[attr-defined]


def put_limited[M](items: dict[str, M], item_id: str, item: M, resource: str, limit: int) -> None:
    """Legt an oder ersetzt; neue Elemente über der Grenze werden abgelehnt."""
    if item_id not in items and len(items) >= limit:
        raise LimitReachedError(resource, limit)
    items[item_id] = item


def remove_existing[M](items: dict[str, M], item_id: str, resource: str) -> None:
    """Entfernt ein Element; unbekannte Kennungen sind ein Fehler."""
    if items.pop(item_id, None) is None:
        raise NotFoundError(resource, item_id)
