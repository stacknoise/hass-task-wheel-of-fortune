"""Ausgabe: Schema-2-Daten und Quelltexte in die unveränderte Vorlage des Leitfadens einsetzen."""

from __future__ import annotations

import hashlib
import html
import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from .constants import (
    ENCODING,
    JSON_CLOSE,
    JSON_CLOSE_ESCAPE,
    PLACEHOLDER_DATA,
    PLACEHOLDER_FILES,
    PLACEHOLDER_TITLE,
    PRODUCT_NAME,
    TEMPLATE_HASH_FILE,
)
from .schema import build_schema

if TYPE_CHECKING:
    from pathlib import Path

    from .models import Report


@dataclass(frozen=True, slots=True)
class Counts:
    """Mengen der erzeugten Seite (für die Konsolenausgabe)."""

    types: int
    methods: int
    props: int
    files: int


class TemplateError(Exception):
    """Die Vorlage weicht von der Referenz des Leitfadens ab (Prüfsumme)."""


def to_json(value: object) -> str:
    """Serialisiert für `<script type="application/json">`; `</` wird maskiert."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace(JSON_CLOSE, JSON_CLOSE_ESCAPE)


def verify_template(template: Path) -> str:
    """Liest die Vorlage und prüft sie gegen `template.sha256` (sie bleibt unverändert)."""
    raw = template.read_bytes()
    expected = template.with_name(TEMPLATE_HASH_FILE).read_text(encoding=ENCODING).split()[0]
    if hashlib.sha256(raw).hexdigest() != expected:
        raise TemplateError(f"{template}: Prüfsumme weicht von {TEMPLATE_HASH_FILE} ab")
    return raw.decode(ENCODING)


def render(template: Path, output: Path, report: Report, root: Path) -> Counts:
    """Schreibt die Explorer-Seite `output` aus `template`; liefert die Mengen für die Meldung."""
    document, files = build_schema(root, report)
    page = (
        verify_template(template)
        .replace(PLACEHOLDER_TITLE, html.escape(PRODUCT_NAME))
        .replace(PLACEHOLDER_DATA, to_json(asdict(document)))
        .replace(PLACEHOLDER_FILES, to_json(files))
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding=ENCODING)
    return Counts(
        types=len(document.types),
        methods=sum(len(item.meths) for item in document.types),
        props=sum(len(item.props) for item in document.types),
        files=len(files),
    )
