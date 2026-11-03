"""Abhängigkeiten: Modul-Graph, Kopplung (Ca/Ce/I) und Testabdeckung nach Namen."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING

from .constants import DOT, LANG_PYTHON, SLASH
from .layers import is_allowed
from .metrics import instability
from .models import Edge, ModuleInfo, TypeInfo
from .python_scanner import dotted_name

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping


def module_keys(module: ModuleInfo) -> str:
    """Schlüssel, unter dem andere Module dieses importieren (Modulname bzw. Pfad)."""
    return dotted_name(module.path) if module.language == LANG_PYTHON else module.path


def resolve_modules(modules: Iterable[ModuleInfo]) -> tuple[ModuleInfo, ...]:
    """Löst Importkandidaten auf bekannte Module auf und berechnet Ca, Ce und I je Modul."""
    items = tuple(modules)
    index = {module_keys(module): module.path for module in items}
    targets = {
        module.path: tuple(
            sorted({index[c] for c in _specific(module.imports, index)} - {module.path})
        )
        for module in items
    }
    importers = Counter(target for deps in targets.values() for target in deps)
    return tuple(
        replace(
            module,
            imports=(),
            deps=targets[module.path],
            ca=importers[module.path],
            ce=len(targets[module.path]),
            instability=instability(importers[module.path], len(targets[module.path])),
        )
        for module in items
    )


def _specific(candidates: Iterable[str], index: Mapping[str, str]) -> list[str]:
    """Bekannte Kandidaten ohne Pakete, deren Untermodul ebenfalls importiert wird."""
    known = [name for name in candidates if name in index]
    return [name for name in known if not any(other.startswith(f"{name}{DOT}") for other in known)]


def build_edges(modules: Iterable[ModuleInfo]) -> tuple[Edge, ...]:
    """Kanten des Modul-Graphen, markiert nach erlaubter Schichtrichtung."""
    items = tuple(modules)
    layers = {module.path: module.layer for module in items}
    return tuple(
        Edge(module.path, target, is_allowed(module.layer, layers[target]))
        for module in items
        for target in module.deps
    )


def couple_types(modules: Iterable[ModuleInfo], tested: frozenset[str]) -> tuple[ModuleInfo, ...]:
    """Berechnet Ca, Ce, I und „Test nennt Typ“ je Typ über eindeutige Typnamen."""
    items = tuple(modules)
    owners: dict[str, list[str]] = defaultdict(list)
    for module in items:
        for type_info in module.types:
            owners[type_info.name].append(module.path)
    unique = {name for name, paths in owners.items() if len(paths) == 1}
    used = {
        (module.path, t.name): sorted((t.refs & unique) - {t.name})
        for module in items
        for t in module.types
    }
    dependents = Counter(name for names in used.values() for name in names)
    return tuple(_with_types(module, used, dependents, tested) for module in items)


def _with_types(
    module: ModuleInfo,
    used: Mapping[tuple[str, str], list[str]],
    dependents: Counter[str],
    tested: frozenset[str],
) -> ModuleInfo:
    """Ersetzt die Typen eines Moduls durch Varianten mit Kopplungswerten."""
    types = tuple(
        replace(
            t,
            uses=tuple(used[module.path, t.name]),
            ce=len(used[module.path, t.name]),
            ca=dependents[t.name],
            instability=instability(dependents[t.name], len(used[module.path, t.name])),
            tested=t.name in tested,
        )
        for t in module.types
    )
    return replace(module, types=types, tested=_module_tested(module, types, tested))


def _module_tested(module: ModuleInfo, types: tuple[TypeInfo, ...], tested: frozenset[str]) -> bool:
    """Ein Modul gilt als getestet, wenn ein Test sein Modul, einen Typ oder eine Funktion nennt."""
    stem = module.path.rsplit(SLASH, 1)[-1].split(DOT, 1)[0]
    names = {stem, *(t.name for t in types), *(f.name for f in module.functions)}
    return bool(names & tested)
