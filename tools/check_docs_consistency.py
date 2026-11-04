"""CI-Prüfung der Dokumentation: Versionsstände, Modultabelle und Reihenfolge des Protokolls."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent.parent
DOC_FILE: Final = "docs/CODE_DOKU.md"
PACKAGE: Final = "custom_components/task_wheel"
ENCODING: Final = "utf-8"
EXIT_OK: Final = 0
EXIT_FAIL: Final = 1
MESSAGE_OK: Final = "Dokumentationsprüfung bestanden."

# Dateien mit der Versionsnummer des Releases (Release-Anleitung in docs/DEVELOPMENT.md)
JSON_VERSION_FILES: Final = (
    f"{PACKAGE}/manifest.json",
    "frontend/package.json",
    "e2e/package.json",
)
LOCK_FILES: Final = ("frontend/package-lock.json", "e2e/package-lock.json")
PYPROJECT: Final = "pyproject.toml"
DOC_VERSION: Final = re.compile(r"Code-Version:\s*(\d+\.\d+\.\d+)")

SECTION_MODULES: Final = "## 3. Modulübersicht"
SECTION_LOG: Final = "## 4. Änderungsprotokoll"
SECTION_PREFIX: Final = "#"
TABLE_PREFIX: Final = "|"
LOG_HEADER: Final = "| Datum |"
MODULE_HEADER: Final = "| Modul |"
LOG_COLUMNS: Final = 6
MODULE_COLUMNS: Final = 5
DATE_PATTERN: Final = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERSION_PATTERN: Final = re.compile(r"^\d+\.\d+\.\d+$")
NO_VERSION: Final = "\u2013"  # Gedankenstrich: Zeile ohne Version
PATH_IN_CELL: Final = re.compile(r"`([^`]+)`")
# Zeilen der Modultabelle, die keine Datei im Paket bezeichnen
NON_PACKAGE_PREFIXES: Final = ("frontend/", "e2e/", "tests/")


def read_versions(root: Path) -> dict[str, str]:
    """Liest die Versionen aller Dateien, die bei einem Release angehoben werden."""
    versions = {
        name: json.loads((root / name).read_text(ENCODING))["version"]
        for name in JSON_VERSION_FILES
    }
    for name in LOCK_FILES:
        lock = json.loads((root / name).read_text(ENCODING))
        versions[name] = lock["version"]
        versions[f"{name} (Wurzelpaket)"] = lock["packages"][""]["version"]
    pyproject = tomllib.loads((root / PYPROJECT).read_text(ENCODING))
    versions[PYPROJECT] = pyproject["project"]["version"]
    match = DOC_VERSION.search((root / DOC_FILE).read_text(ENCODING))
    versions[f"{DOC_FILE} (Kopfzeile)"] = match.group(1) if match else "fehlt"
    return versions


def version_problems(versions: dict[str, str]) -> list[str]:
    """Meldet Dateien, deren Version von der des Manifests abweicht."""
    expected = versions[f"{PACKAGE}/manifest.json"]
    return [
        f"{name}: Version {found} statt {expected} (wie manifest.json)"
        for name, found in versions.items()
        if found != expected
    ]


def split_row(line: str) -> list[str]:
    """Zerlegt eine Markdown-Tabellenzeile in ihre Zellen."""
    return [cell.strip() for cell in line.strip().strip(TABLE_PREFIX).split(TABLE_PREFIX)]


def section_rows(markdown: str, title: str) -> list[list[str]]:
    """Alle Tabellenzeilen eines Abschnitts (ohne Kopf- und Trennzeile), je als Zellenliste."""
    inside = False
    rows: list[list[str]] = []
    for line in markdown.splitlines():
        if line.startswith(SECTION_PREFIX.strip()):
            inside = line.startswith(title)
        elif inside and line.startswith(TABLE_PREFIX):
            rows.append(split_row(line))
    return [row for row in rows if not row[0].startswith(("---", "Datum", "Modul", "JJJJ"))]


def _version_key(version: str) -> tuple[int, ...]:
    """Sortierschlüssel einer Version `x.y.z`."""
    return tuple(int(part) for part in version.split("."))


def log_problems(rows: list[list[str]]) -> list[str]:
    """Prüft Spaltenzahl, Datum, Version und die Reihenfolge „neueste oben“ des Protokolls."""
    problems: list[str] = []
    last_date = ""
    last_version: tuple[int, ...] | None = None
    for number, row in enumerate(rows, start=1):
        label = f"Protokollzeile {number} ({row[0]})"
        if len(row) != LOG_COLUMNS:
            problems.append(f"{label}: {len(row)} statt {LOG_COLUMNS} Spalten")
            continue
        if not DATE_PATTERN.match(row[0]):
            problems.append(f"{label}: kein Datum JJJJ-MM-TT")
            continue
        if last_date and row[0] > last_date:
            problems.append(f"{label}: neuer als die Zeile darüber ({last_date}), neueste oben")
        last_date = row[0]
        if row[1] == NO_VERSION:
            continue
        if not VERSION_PATTERN.match(row[1]):
            problems.append(f"{label}: Version `{row[1]}` ist weder x.y.z noch `{NO_VERSION}`")
            continue
        key = _version_key(row[1])
        if last_version is not None and key > last_version:
            problems.append(f"{label}: Version {row[1]} höher als in der Zeile darüber")
        last_version = key
    return problems


def module_table_problems(rows: list[list[str]]) -> list[str]:
    """Die Modultabelle enthält nur Modulzeilen (Pfad in Backticks in Spalte 1, feste Spalten)."""
    return [
        f"Modulübersicht enthält keine Modulzeile: {row[0][:50]}"
        for row in rows
        if len(row) != MODULE_COLUMNS or not PATH_IN_CELL.search(row[0])
    ]


def listed_paths(rows: list[list[str]]) -> set[str]:
    """Alle in Spalte 1 der Modultabelle genannten Pfade."""
    return {path for row in rows for path in PATH_IN_CELL.findall(row[0])}


def package_files(root: Path) -> list[str]:
    """Python-Dateien des Pakets relativ zum Paket (ohne `__init__.py` in Unterpaketen)."""
    base = root / PACKAGE
    files = (path.relative_to(base).as_posix() for path in base.rglob("*.py"))
    return sorted(name for name in files if "/" not in name or not name.endswith("__init__.py"))


def missing_modules(files: list[str], paths: set[str]) -> list[str]:
    """Dateien des Pakets, die weder einzeln noch über ihr Verzeichnis in der Tabelle stehen."""
    return [
        name
        for name in files
        if name not in paths and not any(p.endswith("/") and name.startswith(p) for p in paths)
    ]


def stale_modules(root: Path, paths: set[str]) -> list[str]:
    """Pfade der Tabelle (im Paket), die es nicht mehr gibt."""
    return [
        path
        for path in sorted(paths)
        if not path.startswith(NON_PACKAGE_PREFIXES) and not (root / PACKAGE / path).exists()
    ]


def problems_of(root: Path) -> list[str]:
    """Sammelt alle Befunde."""
    markdown = (root / DOC_FILE).read_text(ENCODING)
    modules = section_rows(markdown, SECTION_MODULES)
    paths = listed_paths(modules)
    return [
        *version_problems(read_versions(root)),
        *module_table_problems(modules),
        *(
            f"Modul nicht in {DOC_FILE} §3: {name}"
            for name in missing_modules(package_files(root), paths)
        ),
        *(f"Modul in §3, aber nicht mehr vorhanden: {name}" for name in stale_modules(root, paths)),
        *log_problems(section_rows(markdown, SECTION_LOG)),
    ]


def main() -> int:
    """Einstiegspunkt für CI: gibt jeden Befund aus, Rückgabe 1 bei mindestens einem."""
    problems = problems_of(ROOT)
    report = "\n".join(problems) if problems else MESSAGE_OK
    (sys.stderr if problems else sys.stdout).write(f"{report}\n")
    return EXIT_FAIL if problems else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
