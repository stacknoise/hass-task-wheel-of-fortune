"""Wiederverwendbare Prüfungen für Invarianten (werfen `ValidationError`)."""

from collections.abc import Collection, Hashable, Iterable
from datetime import datetime
from re import Pattern

from ..const.keys import (
    ERR_DUPLICATE,
    ERR_EMPTY,
    ERR_INCONSISTENT,
    ERR_LENGTH,
    ERR_NAIVE_DATETIME,
    ERR_ORDER,
    ERR_PATTERN,
    ERR_RANGE,
)
from ..const.limits import ID_MAX_LENGTH, NAME_MAX_LENGTH, NAME_MIN_LENGTH, WEEKDAY_MAX, WEEKDAY_MIN
from .errors import ValidationError


def ensure(condition: bool, field: str, key: str, **placeholders: object) -> None:
    """Wirft `ValidationError`, wenn `condition` nicht gilt."""
    if not condition:
        raise ValidationError(field, key, placeholders)


def ensure_range[N: (int, float)](field: str, value: N, low: N, high: N) -> None:
    """Prüft `low <= value <= high`."""
    ensure(low <= value <= high, field, ERR_RANGE, low=low, high=high)


def ensure_length(field: str, value: str, low: int, high: int) -> None:
    """Prüft die Länge einer Zeichenkette."""
    ensure(low <= len(value) <= high, field, ERR_LENGTH, low=low, high=high)


def ensure_size(field: str, value: Collection[object], low: int, high: int) -> None:
    """Prüft die Anzahl der Elemente einer Sammlung."""
    ensure(low <= len(value) <= high, field, ERR_LENGTH, low=low, high=high)


def ensure_pattern(field: str, value: str, pattern: Pattern[str]) -> None:
    """Prüft, dass die Zeichenkette vollständig dem Muster entspricht."""
    ensure(pattern.fullmatch(value) is not None, field, ERR_PATTERN)


def ensure_unique(field: str, values: Iterable[Hashable]) -> None:
    """Prüft, dass keine Werte doppelt vorkommen."""
    items = list(values)
    ensure(len(items) == len(set(items)), field, ERR_DUPLICATE)


def ensure_aware(field: str, value: datetime) -> None:
    """Prüft, dass ein Zeitpunkt eine Zeitzone trägt."""
    ensure(value.utcoffset() is not None, field, ERR_NAIVE_DATETIME)


def ensure_weekdays(field: str, weekdays: Collection[int]) -> None:
    """Prüft eine nicht leere Menge gültiger Wochentage (Montag = 0)."""
    ensure(bool(weekdays), field, ERR_EMPTY)
    ensure(
        all(WEEKDAY_MIN <= day <= WEEKDAY_MAX for day in weekdays),
        field,
        ERR_RANGE,
        low=WEEKDAY_MIN,
        high=WEEKDAY_MAX,
    )


def ensure_id(field: str, value: str) -> None:
    """Prüft eine nicht leere Kennung mit Längengrenze."""
    ensure_length(field, value, NAME_MIN_LENGTH, ID_MAX_LENGTH)


def ensure_name(field: str, value: str) -> None:
    """Prüft einen angezeigten Namen (nicht leer, begrenzt, ohne Rand-Leerzeichen)."""
    ensure_length(field, value, NAME_MIN_LENGTH, NAME_MAX_LENGTH)
    ensure(value == value.strip(), field, ERR_INCONSISTENT)


def ensure_time_range(since: datetime | None, until: datetime | None) -> None:
    """Prüft einen optionalen Zeitraum: beide Grenzen mit Zeitzone, `since` vor `until`."""
    if since is not None:
        ensure_aware("since", since)
    if until is not None:
        ensure_aware("until", until)
    if since is not None and until is not None:
        ensure(since < until, "until", ERR_ORDER)
