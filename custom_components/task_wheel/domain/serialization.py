"""Gemeinsame Serialisierung: `to_dict`/`from_dict` für alle Modelle an einer Stelle.

Jedes Feld trägt seinen Decoder in den Feld-Metadaten (`spec`). `to_dict` kodiert über eine
Tabelle nach Typ, `from_dict` lehnt unbekannte Felder und falsche Typen ab.
"""

import dataclasses
import datetime as dt
from collections.abc import Callable, Mapping
from enum import StrEnum
from functools import cache
from types import MappingProxyType
from typing import Any, ClassVar, Final, Self, cast, overload

from ..const.keys import ERR_REQUIRED, ERR_TYPE, ERR_UNKNOWN_FIELD, KEY_KIND
from .errors import UnknownKindError, ValidationError

type Decoder[T] = Callable[[object], T]

DECODER_KEY = "decoder"
MISSING: Final = dataclasses.MISSING


# --- Dekodierer ---------------------------------------------------------------------------------


def _typed[T](expected: type[T], value: object) -> T:
    """Liefert `value`, wenn es genau vom erwarteten Typ ist (`bool` zählt nicht als Zahl)."""
    if type(value) is not expected and not (expected is float and type(value) is int):
        raise ValidationError("", ERR_TYPE, {"expected": expected.__name__})
    return cast("T", value)


def to_str(value: object) -> str:
    """Dekodiert eine Zeichenkette."""
    return _typed(str, value)


def to_int(value: object) -> int:
    """Dekodiert eine ganze Zahl (kein `bool`, kein `float`)."""
    return _typed(int, value)


def to_float(value: object) -> float:
    """Dekodiert eine Zahl; ganze Zahlen werden zu `float`."""
    return float(_typed(float, value))


def to_bool(value: object) -> bool:
    """Dekodiert einen Wahrheitswert."""
    return _typed(bool, value)


def _iso[T](parser: Callable[[str], T], value: object) -> T:
    """Dekodiert eine ISO-8601-Zeichenkette mit dem angegebenen Parser."""
    try:
        return parser(to_str(value))
    except ValueError as err:
        raise ValidationError("", ERR_TYPE, {"expected": "iso8601"}) from err


def to_date(value: object) -> dt.date:
    """Dekodiert ein ISO-Datum."""
    return _iso(dt.date.fromisoformat, value)


def to_time(value: object) -> dt.time:
    """Dekodiert eine ISO-Uhrzeit."""
    return _iso(dt.time.fromisoformat, value)


def to_datetime(value: object) -> dt.datetime:
    """Dekodiert einen ISO-Zeitpunkt."""
    return _iso(dt.datetime.fromisoformat, value)


def as_mapping(value: object) -> Mapping[str, object]:
    """Prüft, dass der Wert ein Objekt mit Zeichenketten-Schlüsseln ist."""
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValidationError("", ERR_TYPE, {"expected": "object"})
    return cast("Mapping[str, object]", value)


def enum_of[E: StrEnum](enum_type: type[E]) -> Decoder[E]:
    """Erzeugt einen Decoder für eine StrEnum."""

    def decode(value: object) -> E:
        try:
            return enum_type(to_str(value))
        except ValueError as err:
            raise ValidationError("", ERR_TYPE, {"expected": enum_type.__name__}) from err

    return decode


def _sequence(value: object) -> list[object]:
    """Prüft, dass der Wert eine Liste ist."""
    if not isinstance(value, list | tuple):
        raise ValidationError("", ERR_TYPE, {"expected": "array"})
    return list(value)


def tuple_of[T](item: Decoder[T]) -> Decoder[tuple[T, ...]]:
    """Dekodiert eine Liste zu einem Tupel."""
    return lambda value: tuple(item(entry) for entry in _sequence(value))


def frozenset_of[T](item: Decoder[T]) -> Decoder[frozenset[T]]:
    """Dekodiert eine Liste zu einer unveränderlichen Menge."""
    return lambda value: frozenset(item(entry) for entry in _sequence(value))


def unique_tuple_of[T](item: Decoder[T]) -> Decoder[tuple[T, ...]]:
    """Dekodiert eine Liste zu einem Tupel ohne Doppelte (Reihenfolge der Erstnennung)."""
    return lambda value: tuple(dict.fromkeys(item(entry) for entry in _sequence(value)))


def optional[T](item: Decoder[T]) -> Decoder[T | None]:
    """Erlaubt `None` zusätzlich zum Wert."""
    return lambda value: None if value is None else item(value)


def model_of[M: "Model"](model_type: type[M]) -> Decoder[M]:
    """Dekodiert ein verschachteltes Modell."""
    return lambda value: model_type.from_dict(as_mapping(value))


def kind_model[M: "KindModel"](registry: Mapping[str, type[M]]) -> Decoder[M]:
    """Dekodiert ein Modell, dessen Klasse über `kind` aus der Registry gewählt wird."""

    def decode(value: object) -> M:
        raw = as_mapping(value)
        kind = raw.get(KEY_KIND)
        model_type = registry.get(kind) if isinstance(kind, str) else None
        if model_type is None:
            raise UnknownKindError(KEY_KIND, kind)
        return model_type.from_dict(raw)

    return decode


def registry_of[M: "KindModel"](*model_types: type[M]) -> Mapping[str, type[M]]:
    """Baut die unveränderliche Zuordnung `Art -> Modellklasse`."""
    return MappingProxyType({model_type.kind.value: model_type for model_type in model_types})


# --- Basisklassen -------------------------------------------------------------------------------


@overload
def spec[T](decoder: Decoder[T]) -> T: ...
@overload
def spec[T](decoder: Decoder[T], *, default: T) -> T: ...
def spec[T](decoder: Decoder[T], *, default: object = MISSING) -> T:
    """Deklariert ein Feld samt Decoder (und optionalem Standardwert)."""
    metadata = {DECODER_KEY: decoder}
    return cast("T", dataclasses.field(default=default, metadata=metadata))


@cache
def _field_names(model: type) -> tuple[str, ...]:
    """Feldnamen einer Datenklasse (einmal je Klasse ermittelt, nicht je Aufruf)."""
    return tuple(field.name for field in dataclasses.fields(cast("Any", model)))


class Model:
    """Basis der Datenklassen: einheitliche Serialisierung."""

    __slots__ = ()

    def to_dict(self) -> dict[str, object]:
        """Gibt das Modell als JSON-taugliches Wörterbuch zurück."""
        names = _field_names(cast("type", type(self)))
        return {name: encode(getattr(self, name)) for name in names}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Erzeugt das Modell aus Daten; unbekannte oder fehlende Felder sind Fehler."""
        fields = dataclasses.fields(cast("Any", cls))
        unknown = set(data) - {field.name for field in fields}
        if unknown:
            raise ValidationError(min(unknown), ERR_UNKNOWN_FIELD)
        return cls(
            **{
                field.name: cls._decode_field(field, data)
                for field in fields
                if _present(field, data)
            }
        )

    @classmethod
    def _decode_field(cls, field: dataclasses.Field[Any], data: Mapping[str, object]) -> object:
        if field.name not in data:
            raise ValidationError(field.name, ERR_REQUIRED)
        try:
            return field.metadata[DECODER_KEY](data[field.name])
        except ValidationError as err:
            raise err.with_parent(field.name) from err


def _present(field: dataclasses.Field[Any], data: Mapping[str, object]) -> bool:
    """Felder mit Standardwert dürfen fehlen und werden dann nicht übergeben."""
    return field.name in data or field.default is dataclasses.MISSING


class KindModel(Model):
    """Modell einer Art (`kind`); `to_dict` ergänzt das Unterscheidungsmerkmal."""

    __slots__ = ()
    kind: ClassVar[StrEnum]

    def to_dict(self) -> dict[str, object]:
        """Wie `Model.to_dict`, zusätzlich mit `kind`."""
        return {KEY_KIND: self.kind.value, **super().to_dict()}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Self:
        """Wie `Model.from_dict`; `kind` ist optional, muss aber zur Klasse passen."""
        kind = data.get(KEY_KIND, cls.kind.value)
        if kind != cls.kind.value:
            raise UnknownKindError(KEY_KIND, kind)
        return super().from_dict({key: item for key, item in data.items() if key != KEY_KIND})


# --- Kodierer -----------------------------------------------------------------------------------

# Reihenfolge zählt: `datetime` ist eine Unterklasse von `date`.
_ENCODERS: tuple[tuple[type | tuple[type, ...], Callable[[Any], object]], ...] = (
    (Model, lambda value: value.to_dict()),
    (StrEnum, lambda value: value.value),
    ((dt.date, dt.time), lambda value: value.isoformat()),
    ((frozenset, set), lambda value: sorted((encode(item) for item in value), key=str)),
    ((tuple, list), lambda value: [encode(item) for item in value]),
)


def encode(value: object) -> object:
    """Wandelt einen Feldwert in JSON-taugliche Daten um."""
    for kinds, encoder in _ENCODERS:
        if isinstance(value, kinds):
            return encoder(value)
    return value
