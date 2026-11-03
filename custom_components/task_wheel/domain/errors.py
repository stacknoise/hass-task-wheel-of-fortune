"""Fachliche Ausnahmen der Domäne. Die Schlüssel werden in der Schnittstelle übersetzt."""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from ..const.keys import (
    ERR_LIMIT_REACHED,
    ERR_NOT_FOUND,
    ERR_STORAGE_CORRUPT,
    ERR_STORAGE_VERSION,
    ERR_UNKNOWN_KIND,
)

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


class LimitReachedError(TaskWheelError):
    """Eine Ressourcengrenze (z. B. Anzahl Personen) ist erreicht."""

    def __init__(self, resource: str, limit: int) -> None:
        """Merkt sich Ressource und Grenze als Platzhalter."""
        super().__init__(ERR_LIMIT_REACHED, {"resource": resource, "limit": limit})


class NotFoundError(TaskWheelError):
    """Ein Element mit dieser Kennung gibt es nicht."""

    def __init__(self, resource: str, item_id: str) -> None:
        """Merkt sich Ressource und Kennung als Platzhalter."""
        super().__init__(ERR_NOT_FOUND, {"resource": resource, "id": item_id})


class StorageCorruptError(TaskWheelError):
    """Gespeicherte Daten sind unlesbar oder verletzen das Modell."""

    def __init__(self, store: str, reason: str) -> None:
        """Merkt sich Speicher und Ursache als Platzhalter."""
        super().__init__(ERR_STORAGE_CORRUPT, {"store": store, "reason": reason})


class StorageVersionError(TaskWheelError):
    """Der Speicher stammt von einer neueren oder unbekannten Version."""

    def __init__(self, store: str, version: str) -> None:
        """Merkt sich Speicher und Version als Platzhalter."""
        super().__init__(ERR_STORAGE_VERSION, {"store": store, "version": version})
