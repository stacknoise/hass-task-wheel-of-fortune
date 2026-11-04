"""Übersetzungs- und Textdateien sind gültiges JSON und in beiden Sprachen deckungsgleich."""

import json
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent / "custom_components" / "task_wheel"
LANGUAGES = ("de", "en")
FOLDERS = ("translations", "texts")


def _keys(node: object, prefix: str = "") -> set[str]:
    """Liefert alle Blattpfade eines JSON-Baums."""
    if not isinstance(node, dict):
        return {prefix}
    return {key for name, child in node.items() for key in _keys(child, f"{prefix}/{name}")}


@pytest.mark.parametrize("folder", FOLDERS)
def test_files_are_valid_json_with_matching_keys(folder: str) -> None:
    """Beide Sprachdateien lassen sich laden und haben dieselben Schlüssel."""
    loaded = {
        lang: json.loads((COMPONENT / folder / f"{lang}.json").read_text(encoding="utf-8"))
        for lang in LANGUAGES
    }
    assert _keys(loaded["de"]) == _keys(loaded["en"])
