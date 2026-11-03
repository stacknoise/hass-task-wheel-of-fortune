"""Schwellwerte aus CODE_DOKU.md §1.1 lesen und auswerten."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .constants import (
    CELL_SEPARATOR,
    COLUMN_GREEN,
    COLUMN_LABEL,
    COLUMN_RED,
    DECIMAL_COMMA,
    DIRECTION_MAX,
    DIRECTION_MIN,
    DOT,
    ENCODING,
    NEWLINE,
    OP_MAX,
    OP_MIN,
    STATUS_GREEN,
    STATUS_RED,
    STATUS_YELLOW,
    THRESHOLD_CELL,
    THRESHOLD_COLUMNS,
    THRESHOLD_LABELS,
    THRESHOLD_ROW_PREFIX,
    THRESHOLD_SECTION,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Threshold:
    """Grenzen einer Messgröße: grün bis `green`, rot jenseits von `red`."""

    scope: str
    direction: str
    green: float
    red: float

    def status(self, value: float) -> str:
        """Ampelfarbe für `value`."""
        if self.direction == DIRECTION_MAX:
            return _ampel(value <= self.green, value > self.red)
        return _ampel(value >= self.green, value < self.red)


def _ampel(is_green: bool, is_red: bool) -> str:
    """Wählt die Ampelfarbe aus den beiden Bedingungen (rot gewinnt nicht vor grün)."""
    if is_green:
        return STATUS_GREEN
    return STATUS_RED if is_red else STATUS_YELLOW


def _cell(text: str) -> tuple[str, float] | None:
    """Liest Operator und Zahl aus einer Tabellenzelle wie `≤ 0,5`."""
    match = THRESHOLD_CELL.match(text)
    if not match:
        return None
    return match.group(1), float(match.group(2).replace(DECIMAL_COMMA, DOT))


def _row(line: str) -> Threshold | None:
    """Liest eine Tabellenzeile; unbekannte oder nicht messbare Zeilen ergeben `None`."""
    cells = [cell.strip() for cell in line.strip().strip(CELL_SEPARATOR).split(CELL_SEPARATOR)]
    if len(cells) < THRESHOLD_COLUMNS or cells[COLUMN_LABEL] not in THRESHOLD_LABELS:
        return None
    green, red = _cell(cells[COLUMN_GREEN]), _cell(cells[COLUMN_RED])
    if green is None or red is None:
        return None
    direction = DIRECTION_MAX if green[0] == OP_MAX else DIRECTION_MIN
    if green[0] not in (OP_MAX, OP_MIN):
        return None
    return Threshold(THRESHOLD_LABELS[cells[COLUMN_LABEL]], direction, green[1], red[1])


def parse_thresholds(markdown: str) -> tuple[Threshold, ...]:
    """Liest die Tabelle im Abschnitt „1.1 Schwellwerte“."""
    lines = markdown.split(NEWLINE)
    start = next((i for i, line in enumerate(lines) if line.startswith(THRESHOLD_SECTION)), None)
    if start is None:
        return ()
    rows = (_row(line) for line in lines[start + 1 :] if line.startswith(THRESHOLD_ROW_PREFIX))
    return tuple(row for row in rows if row)


def load_thresholds(path: Path) -> tuple[Threshold, ...]:
    """Liest die Schwellwerte aus der Datei `path`."""
    return parse_thresholds(path.read_text(encoding=ENCODING))
