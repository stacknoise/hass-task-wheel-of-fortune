"""Findet das gebaute Panel-Bundle (Dateiname mit Inhalts-Hash); ohne Home Assistant."""

from pathlib import Path

from ..const.panel import PANEL_BUNDLE_PATTERN


def find_bundle_name(directory: Path) -> str | None:
    """Name der Einstiegsdatei in `directory`; `None`, wenn nicht gebaut.

    Gibt es mehrere (alte Stände), gewinnt die zuletzt geänderte.
    """
    if not directory.is_dir():
        return None
    candidates = sorted(directory.glob(PANEL_BUNDLE_PATTERN), key=lambda path: path.stat().st_mtime)
    return candidates[-1].name if candidates else None
