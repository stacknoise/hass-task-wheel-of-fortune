"""Datenmodell des Generators: Token, Metriken, Methoden, Typen, Module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Token:
    """Lexikalisches Element (sprachunabhängig)."""

    kind: str
    text: str
    line: int
    end_line: int
    start: int = 0
    end: int = 0


@dataclass(frozen=True, slots=True)
class Metrics:
    """Messwerte eines Elements."""

    loc: int
    cc: int
    mi: float


@dataclass(frozen=True, slots=True)
class MethodInfo:
    """Methode oder Funktion."""

    name: str
    kind: str
    signature: str
    doc: str
    line_start: int
    line_end: int
    metrics: Metrics
    source: str


@dataclass(frozen=True, slots=True)
class TypeInfo:
    """Klasse, Interface oder Enum."""

    name: str
    kind: str
    doc: str
    line_start: int
    line_end: int
    metrics: Metrics
    methods: tuple[MethodInfo, ...]
    refs: frozenset[str] = frozenset()
    uses: tuple[str, ...] = ()
    tested: bool = False
    ca: int = 0
    ce: int = 0
    instability: float = 0.0


@dataclass(frozen=True, slots=True)
class ModuleInfo:
    """Quelldatei mit ihren Typen, Funktionen und Abhängigkeiten."""

    path: str
    language: str
    layer: str
    doc: str
    metrics: Metrics
    types: tuple[TypeInfo, ...]
    functions: tuple[MethodInfo, ...]
    imports: tuple[str, ...] = ()
    deps: tuple[str, ...] = ()
    tested: bool = False
    ca: int = 0
    ce: int = 0
    instability: float = 0.0


@dataclass(frozen=True, slots=True)
class Edge:
    """Abhängigkeit zwischen zwei Modulen."""

    source: str
    target: str
    allowed: bool


@dataclass(frozen=True, slots=True)
class Finding:
    """Verletzung eines Schwellwerts."""

    location: str
    scope: str
    value: float
    limit: float


@dataclass(frozen=True, slots=True)
class Report:
    """Gesamtergebnis eines Generatorlaufs."""

    version: str
    modules: tuple[ModuleInfo, ...]
    edges: tuple[Edge, ...]
    layers: tuple[dict[str, object], ...] = field(default=())
