"""Schichten: Zuordnung von Dateien und Prüfung erlaubter Abhängigkeiten."""

from __future__ import annotations

from .constants import LAYER_ALLOWED, LAYER_OTHER, LAYER_RULES


def layer_of(path: str) -> str:
    """Schicht einer Quelldatei nach `LAYER_RULES`; unbekannte Pfade ⇒ `Other`."""
    return next((layer for prefix, layer in LAYER_RULES if path.startswith(prefix)), LAYER_OTHER)


def is_allowed(source_layer: str, target_layer: str) -> bool:
    """Wahr, wenn `source_layer` laut CODE_DOKU.md §2 `target_layer` nutzen darf."""
    return source_layer == target_layer or target_layer in LAYER_ALLOWED.get(
        source_layer, frozenset()
    )
