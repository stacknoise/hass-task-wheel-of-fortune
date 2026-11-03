"""Fachliche Ausnahmen der Domäne. Die Schlüssel werden in der Schnittstelle übersetzt."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from ..const.keys import ERR_UNKNOWN_KIND

_NO_PLACEHOLDERS: Final[Mapping[str, object]] = MappingProxyType({})


class TaskWheelError(Exception):
    """Basis aller fachlichen Fehler; trägt einen Übersetzungsschlüssel."""

    def __init__(self, key: str, placeholders: Mapping[str, object] = _NO_PLACEHOLDERS) -> None:
        """Speichert Schlüssel und Platzhalter für die Übersetzung."""
        super().__init__(key)
        self.key = key
        self.placeholders = MappingProxyType(dict(placeholders))


class ValidationError(TaskWheelError):
    """Eine Eingabe oder ein Modell verletzt eine Invariante."""

    def __init__(
        self, field: str, key: str, placeholders: Mapping[str, object] = _NO_PLACEHOLDERS
    ) -> None:
        """Speichert zusätzlich den (verschachtelten) Feldpfad."""
        super().__init__(key, placeholders)
        self.field = field

    def with_parent(self, parent: str) -> "ValidationError":
        """Liefert denselben Fehler mit vorangestelltem Feldnamen."""
        path = f"{parent}.{self.field}" if self.field else parent
        return ValidationError(path, self.key, self.placeholders)

    def __str__(self) -> str:
        """Lesbare Kurzform für Protokolle."""
        return f"{self.field}: {self.key}"


class UnknownKindError(ValidationError):
    """Eine Regel- oder Triggerart ist nicht registriert."""

    def __init__(self, field: str, kind: object) -> None:
        """Merkt sich die unbekannte Art als Platzhalter."""
        super().__init__(field, ERR_UNKNOWN_KIND, {"kind": str(kind)})
