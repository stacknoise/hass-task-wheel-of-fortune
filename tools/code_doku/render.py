"""Ausgabe: Bericht als JSON in die HTML-Vorlage einsetzen."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from .constants import DATA_PLACEHOLDER, ENCODING, JSON_LT_ESCAPE

if TYPE_CHECKING:
    from pathlib import Path

    from .models import Report
    from .thresholds import Threshold


def to_json(report: Report, thresholds: tuple[Threshold, ...]) -> str:
    """Serialisiert den Bericht; `<` wird maskiert, damit der Text sicher in `<script>` passt."""
    payload = {**asdict(report), "thresholds": [asdict(threshold) for threshold in thresholds]}
    text = json.dumps(payload, ensure_ascii=False, default=sorted, separators=(",", ":"))
    return text.replace("<", JSON_LT_ESCAPE)


def render(template: Path, output: Path, report: Report, thresholds: tuple[Threshold, ...]) -> None:
    """Schreibt die Explorer-Seite `output` aus `template`."""
    html = template.read_text(encoding=ENCODING).replace(
        DATA_PLACEHOLDER, to_json(report, thresholds)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding=ENCODING)
