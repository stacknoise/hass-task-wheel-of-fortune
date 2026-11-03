"""Kommandozeile des Code-Doku-Generators."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .check import find_violations
from .constants import (
    DEFAULT_DOC,
    DEFAULT_OUTPUT,
    DEFAULT_TEMPLATE,
    EXIT_ERROR,
    EXIT_OK,
    EXIT_VIOLATIONS,
    MSG_CHECK_OK,
    MSG_ERROR,
    MSG_NO_THRESHOLDS,
    MSG_VIOLATION,
    MSG_WRITTEN,
    NEWLINE,
)
from .project import ScanError, build_report
from .render import TemplateError, render
from .thresholds import load_thresholds

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .models import Report
    from .thresholds import Threshold


def parse_args(argv: Sequence[str] | None, root: Path) -> argparse.Namespace:
    """Liest die Kommandozeilenargumente."""
    parser = argparse.ArgumentParser(description="Erzeugt die Code-Dokumentation (Explorer-Seite).")
    parser.add_argument("--root", type=Path, default=root, help="Projektwurzel")
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT), help="Ausgabedatei")
    parser.add_argument(
        "--template", type=Path, default=Path(DEFAULT_TEMPLATE), help="HTML-Vorlage"
    )
    parser.add_argument(
        "--doc", type=Path, default=Path(DEFAULT_DOC), help="Datei mit Schwellwerten"
    )
    parser.add_argument("--check", action="store_true", help="Schwellwerte prüfen (CI)")
    return parser.parse_args(argv)


def _under(root: Path, path: Path) -> Path:
    """Relative Pfade beziehen sich auf die Projektwurzel."""
    return path if path.is_absolute() else root / path


def run(argv: Sequence[str] | None, root: Path) -> int:
    """Erzeugt die Seite und prüft auf Wunsch die Schwellwerte. Liefert den Exit-Code."""
    args = parse_args(argv, root)
    base: Path = args.root
    try:
        report = build_report(base)
        thresholds = load_thresholds(_under(base, args.doc))
        output = _under(base, args.output)
        counts = render(_under(base, args.template), output, report, base)
    except (ScanError, TemplateError, OSError) as error:
        sys.stderr.write(MSG_ERROR.format(error=error) + NEWLINE)
        return EXIT_ERROR
    sys.stdout.write(
        MSG_WRITTEN.format(
            path=output,
            types=counts.types,
            methods=counts.methods,
            props=counts.props,
            files=counts.files,
        )
        + NEWLINE
    )
    return _check(report, thresholds, args.doc) if args.check else EXIT_OK


def _check(report: Report, thresholds: tuple[Threshold, ...], doc: Path) -> int:
    """Meldet Verletzungen der Schwellwerte."""
    if not thresholds:
        sys.stderr.write(MSG_NO_THRESHOLDS.format(path=doc) + NEWLINE)
        return EXIT_ERROR
    findings = find_violations(report, thresholds)
    for finding in findings:
        sys.stderr.write(
            MSG_VIOLATION.format(
                location=finding.location,
                scope=finding.scope,
                value=finding.value,
                limit=finding.limit,
            )
            + NEWLINE
        )
    if findings:
        return EXIT_VIOLATIONS
    sys.stdout.write(MSG_CHECK_OK + NEWLINE)
    return EXIT_OK


def main() -> int:
    """Einstiegspunkt: Projektwurzel ist zwei Ebenen über `tools/code_doku`."""
    return run(None, Path(__file__).resolve().parents[2])
