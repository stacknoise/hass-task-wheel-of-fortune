"""Datenmodell Schema 2 des Leitfadens Code-Dokumentation (Feldnamen = JSON-Schlüssel)."""

# ruff: noqa: E741
# pylint: disable=invalid-name
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SchemaMember:
    """Eigenschaft, Feld, Konstante oder Aufzählungswert (`props`)."""

    n: str
    type: str
    kind: str
    acc: str
    init: str
    vis: str
    static: bool
    l: int
    e: int
    doc: str


@dataclass(frozen=True, slots=True)
class SchemaMethod:
    """Methode, Funktion oder Konstruktor (`meths`)."""

    n: str
    kind: str
    sig: str
    l: int
    e: int
    loc: int
    cc: int
    vis: str
    static: bool
    abstract: bool
    doc: str


@dataclass(slots=True)
class SchemaType:
    """Typ (Klasse, Schnittstelle, Aufzählung oder Modul mit Funktionen)."""

    id: str
    name: str
    ns: str
    project: str
    kind: str
    file: str
    l: int
    dl: int
    e: int
    doc: str
    bases: list[str]
    vis: str
    static: bool
    loc: int
    cc: int
    mi: int
    tested: bool
    props: list[SchemaMember]
    meths: list[SchemaMethod]
    deps: list[str] = field(default_factory=list)
    ca: int = 0
    ce: int = 0
    instab: float = 0.0


@dataclass(frozen=True, slots=True)
class SchemaMeta:
    """Kopfdaten (`meta`)."""

    name: str
    version: str
    prefix: str
    layers: list[str]
    generated: str
    tests: bool


@dataclass(slots=True)
class SchemaDocument:
    """Gesamtes Datenmodell, das die Vorlage liest."""

    schema: int
    meta: SchemaMeta
    projdeps: dict[str, list[str]]
    types: list[SchemaType]
