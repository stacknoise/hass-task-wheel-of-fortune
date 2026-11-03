"""Umwandlung von Ergebnissen in JSON-taugliche Daten für die Schnittstellen (KONZEPT §6.4)."""

import dataclasses
from collections.abc import Mapping
from typing import Final, cast

from ..domain.serialization import Model, encode
from ..domain.statistics.report import Standing, WeekRate

type Json = dict[str, object]

# Berechnete Eigenschaften, die ein Ergebnis zusätzlich zu seinen Feldern liefert
_COMPUTED: Final[Mapping[type, tuple[str, ...]]] = {Standing: ("difference",), WeekRate: ("rate",)}


def to_wire(value: object) -> object:
    """Wandelt Modelle, Ergebnisobjekte, Sammlungen, Aufzählungen und Zeitangaben um."""
    if isinstance(value, Model):
        return value.to_dict()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        names = (
            *(field.name for field in dataclasses.fields(value)),
            *_COMPUTED.get(type(value), ()),
        )
        return {name: to_wire(getattr(value, name)) for name in names}
    if isinstance(value, Mapping):
        return {str(key): to_wire(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [to_wire(item) for item in value]
    return encode(value)


def to_json(value: object) -> Json:
    """Wie `to_wire`, für Werte, die ein Objekt ergeben."""
    return cast("Json", to_wire(value))
