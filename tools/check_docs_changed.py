"""CI-Prüfung: Code geändert ⇒ Änderungsprotokoll in CODE_DOKU.md geändert."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Final

CODE_PREFIXES: Final = ("custom_components/", "frontend/src/")
DOC_FILE: Final = "docs/CODE_DOKU.md"
ENV_BASE_REF: Final = "GITHUB_BASE_REF"
FALLBACK_BASE: Final = "HEAD~1"
EXIT_OK: Final = 0
EXIT_FAIL: Final = 1
MESSAGE_FAIL: Final = f"Code wurde geändert, aber {DOC_FILE} (Änderungsprotokoll) nicht."
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


def docs_missing(files: list[str]) -> bool:
    """Wahr, wenn Code geändert wurde, die Code-Doku aber nicht."""
    code_changed = any(name.startswith(CODE_PREFIXES) for name in files)
    return code_changed and DOC_FILE not in files


def main() -> int:
    """Einstiegspunkt für CI."""
    if docs_missing(changed_files(base_ref(dict(os.environ)))):
        sys.stderr.write(f"{MESSAGE_FAIL}\n")
        return EXIT_FAIL
    sys.stdout.write(f"{MESSAGE_OK}\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
