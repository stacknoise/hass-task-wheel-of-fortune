"""CI-Prüfung: Code geändert ⇒ neue Zeile im Änderungsprotokoll von CODE_DOKU.md."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import Final

CODE_PREFIXES: Final = (
    "custom_components/",
    "frontend/src/",
    "tools/",
    "e2e/tests/",
    "e2e/screenshots/",
    ".github/workflows/",
    ".github/dependabot.yml",
)
DOC_FILE: Final = "docs/CODE_DOKU.md"
ENV_BASE_REF: Final = "GITHUB_BASE_REF"
ENV_ACTOR: Final = "GITHUB_ACTOR"
# Abhängigkeits-Bots ändern Workflows und Lockdateien, ohne das Protokoll pflegen zu können
EXEMPT_ACTORS: Final = frozenset({"dependabot[bot]"})
FALLBACK_BASE: Final = "HEAD~1"
# Neue Protokollzeile: Tabellenzeile, die mit einem Datum beginnt
NEW_ROW: Final = re.compile(r"^\+\| \d{4}-\d{2}-\d{2} \|")
EXIT_OK: Final = 0
EXIT_FAIL: Final = 1
MESSAGE_FAIL: Final = (
    f"Code wurde geändert, aber {DOC_FILE} hat keine neue Zeile im Änderungsprotokoll (§4)."
)
MESSAGE_OK: Final = "Code-Doku-Prüfung bestanden."


def base_ref(environ: dict[str, str]) -> str:
    """Bestimmt den Vergleichsstand: Ziel-Branch des PR, sonst der vorherige Commit."""
    target = environ.get(ENV_BASE_REF)
    return f"origin/{target}" if target else FALLBACK_BASE


def changed_files(base: str) -> list[str]:
    """Liefert die gegenüber `base` geänderten Dateien."""
    output = subprocess.run(  # noqa: S603
        ["git", "diff", "--name-only", f"{base}...HEAD"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return output.splitlines()


def doc_diff(base: str) -> list[str]:
    """Liefert die Diff-Zeilen der Code-Doku gegenüber `base` (ohne Kontext)."""
    output = subprocess.run(  # noqa: S603
        ["git", "diff", "--unified=0", f"{base}...HEAD", "--", DOC_FILE],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return output.splitlines()


def code_changed(files: list[str]) -> bool:
    """Wahr, wenn Code, Werkzeuge, E2E-Tests oder die Pipeline geändert wurden."""
    return any(name.startswith(CODE_PREFIXES) for name in files)


def has_new_row(diff: list[str]) -> bool:
    """Wahr, wenn der Diff mindestens eine neue Protokollzeile (Datum in Spalte 1) enthält."""
    return any(NEW_ROW.match(line) for line in diff)


def docs_missing(files: list[str], diff: list[str] | None = None) -> bool:
    """Wahr, wenn Code geändert wurde, aber die Code-Doku keine neue Protokollzeile hat.

    Ohne `diff` genügt eine beliebige Änderung der Datei (nur für Aufrufer ohne Diff).
    """
    if not code_changed(files):
        return False
    if diff is None:
        return DOC_FILE not in files
    return not has_new_row(diff)


def main() -> int:
    """Einstiegspunkt für CI."""
    environ = dict(os.environ)
    if environ.get(ENV_ACTOR) in EXEMPT_ACTORS:
        sys.stdout.write(f"{MESSAGE_OK}\n")
        return EXIT_OK
    base = base_ref(environ)
    if docs_missing(changed_files(base), doc_diff(base)):
        sys.stderr.write(f"{MESSAGE_FAIL}\n")
        return EXIT_FAIL
    sys.stdout.write(f"{MESSAGE_OK}\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
