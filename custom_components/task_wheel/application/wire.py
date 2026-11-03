"""Umwandlung von Ergebnissen in JSON-taugliche Daten für die Schnittstellen (KONZEPT §6.4)."""

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any, Final, cast

from ..domain.serialization import Model, encode
from ..domain.statistics.report import Standing, WeekRate

type Json = dict[str, object]

# Berechnete Eigenschaften, die ein Ergebnis zusätzlich zu seinen Feldern liefert
_COMPUTED: Final[Mapping[type, tuple[str, ...]]] = {Standing: ("difference",), WeekRate: ("rate",)}


def _dataclass(value: object) -> Json:
    """Felder des Ergebnisobjekts plus berechnete Werte."""
    names = (
        *(field.name for field in dataclasses.fields(cast("Any", value))),
        *_COMPUTED.get(type(value), ()),
    )
    return {name: to_wire(getattr(value, name)) for name in names}


def _mapping(value: Mapping[object, object]) -> Json:
    return {str(key): to_wire(item) for key, item in value.items()}


def _sequence(value: tuple[object, ...] | list[object]) -> list[object]:
    return [to_wire(item) for item in value]


# Reihenfolge zählt: `Model` ist selbst eine Dataclass; alles andere übernimmt `encode`
_RULES: Final[tuple[tuple[Callable[[object], bool], Callable[[Any], object]], ...]] = (
    (lambda value: isinstance(value, Model), lambda value: value.to_dict()),
    (lambda value: dataclasses.is_dataclass(value) and not isinstance(value, type), _dataclass),
    (lambda value: isinstance(value, Mapping), _mapping),
    (lambda value: isinstance(value, tuple | list), _sequence),
)


def to_wire(value: object) -> object:
    """Wandelt Modelle, Ergebnisobjekte, Sammlungen, Aufzählungen und Zeitangaben um."""
    for applies, convert in _RULES:
        if applies(value):
            return convert(value)
    return encode(value)


def to_json(value: object) -> Json:
    """Wie `to_wire`, für Werte, die ein Objekt ergeben."""
    return cast("Json", to_wire(value))
