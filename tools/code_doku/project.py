"""Projekt einlesen: Quelldateien finden, scannen, Kopplung berechnen, Bericht bauen."""

from __future__ import annotations

import ast
import json
from typing import TYPE_CHECKING

from .constants import (
    ENCODING,
    LANG_PYTHON,
    LAYER_ORDER,
    MANIFEST_PATH,
    MANIFEST_VERSION_KEY,
    SRC_PYTHON,
    SRC_TS,
    SUFFIX_PYTHON,
    SUFFIX_TS,
    SUFFIX_TS_TEST,
    TESTS_PYTHON,
    UNKNOWN_VERSION,
)
from .dependencies import build_edges, couple_types, resolve_modules
from .layers import layer_of
from .models import Report
from .python_scanner import scan_python
from .ts_scanner import scan_typescript
from .ts_tokens import tokenize_typescript

if TYPE_CHECKING:
    from pathlib import Path

    from .models import ModuleInfo


class ScanError(Exception):
    """Eine Quelldatei konnte nicht gelesen oder analysiert werden."""


def _files(root: Path, folder: str, suffix: str) -> list[Path]:
    """Sortierte Dateien unter `folder` mit der Endung `suffix`."""
    base = root / folder
    return sorted(base.rglob(f"*{suffix}")) if base.is_dir() else []


def _relative(root: Path, file: Path) -> str:
    return file.relative_to(root).as_posix()


def _scan(root: Path, file: Path) -> ModuleInfo:
    """Analysiert eine Quelldatei; Syntaxfehler werden zu `ScanError`."""
    path = _relative(root, file)
    text = file.read_text(encoding=ENCODING)
    try:
        if file.suffix == SUFFIX_PYTHON:
            return scan_python(path, text, layer_of(path))
        return scan_typescript(path, text, layer_of(path))
    except (SyntaxError, ValueError) as error:
        raise ScanError(f"{path}: {error}") from error


def discover(root: Path) -> list[ModuleInfo]:
    """Alle Quellmodule (Python-Integration und Frontend, ohne Tests)."""
    files = _files(root, SRC_PYTHON, SUFFIX_PYTHON) + [
        file for file in _files(root, SRC_TS, SUFFIX_TS) if not file.name.endswith(SUFFIX_TS_TEST)
    ]
    return [_scan(root, file) for file in files]


def tested_names(root: Path) -> frozenset[str]:
    """Bezeichner, die in Tests vorkommen (Python: Namen/Attribute/Importe; TS: Namen)."""
    names: set[str] = set()
    for file in _files(root, TESTS_PYTHON, SUFFIX_PYTHON):
        tree = ast.parse(file.read_text(encoding=ENCODING))
        for node in ast.walk(tree):
            names.update(_python_names(node))
    for file in _files(root, SRC_TS, SUFFIX_TS_TEST):
        tokens, _ = tokenize_typescript(file.read_text(encoding=ENCODING))
        names.update(token.text for token in tokens)
    return frozenset(names)


def _python_names(node: ast.AST) -> set[str]:
    """Bezeichner, die ein einzelner Knoten nennt."""
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.ImportFrom):
        return {alias.name for alias in node.names} | set((node.module or "").split("."))
    if isinstance(node, ast.alias):
        return set(node.name.split("."))
    return set()


def read_version(root: Path) -> str:
    """Version aus dem Integrations-Manifest."""
    manifest = root / MANIFEST_PATH
    if not manifest.is_file():
        return UNKNOWN_VERSION
    return str(
        json.loads(manifest.read_text(encoding=ENCODING)).get(MANIFEST_VERSION_KEY, UNKNOWN_VERSION)
    )


def summarize_layers(modules: tuple[ModuleInfo, ...]) -> tuple[dict[str, object], ...]:
    """Kennzahlen je Schicht (nur Schichten mit Modulen)."""
    summary: list[dict[str, object]] = []
    for layer, label in LAYER_ORDER:
        members = [module for module in modules if module.layer == layer]
        if members:
            summary.append(
                {
                    "id": layer,
                    "label": label,
                    "modules": len(members),
                    "loc": sum(m.metrics.loc for m in members),
                    "cc": sum(m.metrics.cc for m in members),
                    "mi": round(sum(m.metrics.mi for m in members) / len(members), 1),
                }
            )
    return tuple(summary)


def build_report(root: Path) -> Report:
    """Erzeugt den vollständigen Bericht für das Projekt unter `root`."""
    modules = couple_types(resolve_modules(discover(root)), tested_names(root))
    return Report(
        version=read_version(root),
        modules=modules,
        edges=build_edges(modules),
        layers=summarize_layers(modules),
    )


def is_python(module: ModuleInfo) -> bool:
    """Wahr für Python-Module."""
    return module.language == LANG_PYTHON
