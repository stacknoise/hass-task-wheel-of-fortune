"""Übersetzte Texte der Benachrichtigungen aus `texts/<Sprache>.json`."""

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from ...const.notification import (
    TEXTS_FALLBACK_LANGUAGE,
    TEXTS_FILE_SUFFIX,
    TEXTS_LANGUAGE_PATTERN,
)

type Templates = Mapping[str, Mapping[str, str]]


class TextCatalog:
    """Texte je Meldungsart und Teil; `str.format` setzt nur die übergebenen Werte ein."""

    def __init__(self, templates: Templates) -> None:
        """Hält die Vorlagen unveränderlich."""
        self._templates = MappingProxyType(dict(templates))

    def render(self, kind: str, part: str, **values: object) -> str:
        """Setzt `values` in die Vorlage ein; Werte werden nie als Vorlage gelesen."""
        return self._templates[kind][part].format(**values)


def _read(directory: Path, language: str) -> Templates:
    """Liest eine Sprachdatei; gibt es sie nicht, ist das Ergebnis leer."""
    path = directory / f"{language}{TEXTS_FILE_SUFFIX}"
    if not path.is_file():
        return {}
    templates: Templates = json.loads(path.read_text(encoding="utf-8"))
    return templates


def load_catalog(directory: Path, language: str) -> TextCatalog:
    """Lädt die Sprache über der Rückfallsprache, sodass fehlende Teile englisch bleiben.

    Liest Dateien und gehört in einen Executor, nicht in die Ereignisschleife.
    """
    base = _read(directory, TEXTS_FALLBACK_LANGUAGE)
    valid = TEXTS_LANGUAGE_PATTERN.fullmatch(language) is not None
    chosen = _read(directory, language) if valid else {}
    merged = {kind: {**parts, **chosen.get(kind, {})} for kind, parts in base.items()}
    return TextCatalog(merged)
