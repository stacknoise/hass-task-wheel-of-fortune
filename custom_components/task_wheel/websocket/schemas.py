"""Bausteine der Nachrichtenschemas: begrenzte Zeichenketten, Listen und Objekte (KONZEPT §8)."""

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any, Final

import voluptuous as vol

from ..const.keys import ERR_LENGTH, ERR_TOO_DEEP, ERR_TYPE
from ..const.limits import (
    ID_MAX_LENGTH,
    NAME_MIN_LENGTH,
    WS_ISO_MAX_LENGTH,
    WS_LIST_MAX_ITEMS,
    WS_MAX_DEPTH,
    WS_MESSAGE_ID_MIN,
    WS_OBJECT_MAX_KEYS,
    WS_STRING_MAX_LENGTH,
)
from ..domain.serialization import Model

# Vom Dienst vergeben bzw. beim Anlegen ableitbar
AUTO_FIELDS: Final = ("id",)
DERIVED_FIELDS: Final = ("slug",)

ID = vol.All(str, vol.Length(min=NAME_MIN_LENGTH, max=ID_MAX_LENGTH))


def _integer(value: object) -> int:
    """Eine ganze Zahl (`bool` zählt nicht)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise vol.Invalid(ERR_TYPE)
    return value


INTEGER = _integer
MESSAGE_ID = vol.All(_integer, vol.Range(min=WS_MESSAGE_ID_MIN))
ISO_TEXT = vol.All(str, vol.Length(min=NAME_MIN_LENGTH, max=WS_ISO_MAX_LENGTH))


def _check_string(value: str, _depth: int) -> None:
    if len(value) > WS_STRING_MAX_LENGTH:
        raise vol.Invalid(ERR_LENGTH)


def _check_object(value: Mapping[object, object], depth: int) -> None:
    if len(value) > WS_OBJECT_MAX_KEYS:
        raise vol.Invalid(ERR_LENGTH)
    for key, item in value.items():
        _bounded(key, depth - 1)
        _bounded(item, depth - 1)


def _check_list(value: list[object], depth: int) -> None:
    if len(value) > WS_LIST_MAX_ITEMS:
        raise vol.Invalid(ERR_LENGTH)
    for item in value:
        _bounded(item, depth - 1)


def _check_scalar(value: bool | int | float | None, _depth: int) -> None:
    """Zahlen, Wahrheitswerte und `None` sind immer klein."""


# Erlaubte Arten von Werten und ihre Prüfung (alles andere ist ein Typfehler)
_CHECKS: Final[tuple[tuple[type | tuple[type, ...], Callable[[Any, int], None]], ...]] = (
    (str, _check_string),
    (Mapping, _check_object),
    (list, _check_list),
    ((bool, int, float, type(None)), _check_scalar),
)


def _bounded(value: object, depth: int) -> object:
    """Prüft Größe und Tiefe eines Werts; die Bedeutung prüfen die Modelle (`from_dict`)."""
    if depth < 0:
        raise vol.Invalid(ERR_TOO_DEEP)
    for kinds, check in _CHECKS:
        if isinstance(value, kinds):
            check(value, depth)
            return value
    raise vol.Invalid(ERR_TYPE)


def bounded(value: object) -> object:
    """Voluptuous-Prüfung: Zeichenketten, Listen und Objekte bleiben klein und flach."""
    return _bounded(value, WS_MAX_DEPTH)


def model_fields(model_type: type[Model], *, required: bool) -> dict[Any, Any]:
    """Liefert das Schema der Felder eines Modells, abgeleitet aus seinen Datenfeldern.

    Die Kennung vergibt der Dienst, den Kurznamen leitet er bei Bedarf vom Namen ab. Beim Anlegen
    sind die übrigen Felder ohne Standardwert Pflicht, beim Ändern ist alles optional. Ob ein Wert
    fachlich stimmt, prüft das Modell; das Schema begrenzt nur Form und Größe.
    """
    fields: dict[Any, Any] = {}
    for field in dataclasses.fields(model_type):  # type: ignore[arg-type]
        if field.name in AUTO_FIELDS:
            continue
        needed = (
            required and field.default is dataclasses.MISSING and field.name not in DERIVED_FIELDS
        )
        marker = vol.Required if needed else vol.Optional
        fields[marker(field.name)] = bounded
    return fields


def required_fields(*pairs: tuple[str, object]) -> dict[Any, Any]:
    """Pflichtfelder `(Name, Prüfung)`."""
    return {vol.Required(name): check for name, check in pairs}


def optional_fields(*pairs: tuple[str, object]) -> dict[Any, Any]:
    """Optionale Felder `(Name, Prüfung)`."""
    return {vol.Optional(name): check for name, check in pairs}
