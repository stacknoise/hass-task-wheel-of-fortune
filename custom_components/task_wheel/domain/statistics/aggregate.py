"""Monatsaggregate: Anzahl und Aufgabenpunkte je Person, Aufgabe und Status (KONZEPT §4.1).

Die Struktur ist JSON-tauglich (`Monat -> Person -> Aufgabe -> Status -> [Anzahl, Punkte]`) und wird
inkrementell fortgeschrieben: eine Änderung zieht den Beitrag des alten Zustands ab und addiert den
des neuen. Die Punkte sind die Aufgabenpunkte ohne Faktor, damit eine Änderung der Einstellungen
die Aggregate nicht entwertet; der Faktor kommt erst bei der Auswertung.
"""

import datetime as dt
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Final

from ...const.defaults import MONTH_KEY_FORMAT
from ...const.keys import ERR_TYPE
from ...const.limits import MONTHS_PER_YEAR
from ..enums import AssignmentStatus
from ..errors import ValidationError
from ..models import Assignment, Round
from ..serialization import as_mapping, enum_of, to_int
from ..types import PersonId, TaskId

type Cell = list[int]
type MonthData = dict[str, dict[str, dict[str, Cell]]]
type Aggregates = dict[str, MonthData]

_COUNT: Final = 0
_POINTS: Final = 1
_CELL_SIZE: Final = 2
_ADD: Final = 1
_SUBTRACT: Final = -1
_FIELD_CELL: Final = "cell"
_decode_status = enum_of(AssignmentStatus)


@dataclass(slots=True, frozen=True)
class AssignmentChange:
    """Änderung einer Zuteilung; `before` fehlt bei neuen, `after` bei entfallenden."""

    before: Assignment | None
    after: Assignment | None


@dataclass(slots=True, frozen=True)
class StatRow:
    """Eine Zelle der Aggregate in lesbarer Form."""

    person_id: PersonId
    task_id: TaskId
    status: AssignmentStatus
    count: int
    points: int


def month_key(moment: dt.datetime) -> str:
    """Schlüssel des Monats (`JJJJ-MM`) in der Zeitzone des Zeitpunkts."""
    return moment.strftime(MONTH_KEY_FORMAT)


def month_starts(today: dt.date, count: int) -> tuple[dt.date, ...]:
    """Erste Tage der letzten `count` Kalendermonate bis zum laufenden (älteste zuerst)."""
    current = today.year * MONTHS_PER_YEAR + today.month - 1
    starts = []
    for index in range(current - count + 1, current + 1):
        year, month_index = divmod(index, MONTHS_PER_YEAR)
        starts.append(dt.date(year, month_index + 1, 1))
    return tuple(starts)


def month_keys(today: dt.date, count: int) -> tuple[str, ...]:
    """Schlüssel der letzten `count` Kalendermonate (älteste zuerst)."""
    return tuple(start.strftime(MONTH_KEY_FORMAT) for start in month_starts(today, count))


def _decode_cell(value: object) -> Cell:
    if not isinstance(value, list) or len(value) != _CELL_SIZE:
        raise ValidationError(_FIELD_CELL, ERR_TYPE, {"expected": "array"})
    return [to_int(item) for item in value]


def decode_month(value: object) -> MonthData:
    """Liest einen Monat aus den Speicherdaten und liefert dabei eine unabhängige Kopie.

    Raises:
        ValidationError: Die Struktur oder ein Status stimmt nicht.
    """
    return {
        person: {
            task: {
                _decode_status(status).value: _decode_cell(cell)
                for status, cell in as_mapping(by_status).items()
            }
            for task, by_status in as_mapping(by_task).items()
        }
        for person, by_task in as_mapping(value).items()
    }


def _apply(month: MonthData, assignment: Assignment, sign: int) -> None:
    """Addiert (`+1`) oder subtrahiert (`-1`) den Beitrag; leere Zellen werden entfernt."""
    tasks = month.setdefault(assignment.person_id, {})
    statuses = tasks.setdefault(assignment.task_id, {})
    cell = statuses.setdefault(assignment.status.value, [0, 0])
    cell[_COUNT] += sign
    cell[_POINTS] += sign * assignment.points
    if cell[_COUNT] <= 0:
        del statuses[assignment.status.value]
    if not statuses:
        del tasks[assignment.task_id]
    if not tasks:
        del month[assignment.person_id]


def updated_month(
    aggregates: Mapping[str, object], key: str, changes: Iterable[AssignmentChange]
) -> MonthData:
    """Liefert eine Kopie des Monats mit den Änderungen (die Eingabe bleibt unverändert)."""
    month = decode_month(aggregates.get(key, {}))
    for change in changes:
        if change.before is not None:
            _apply(month, change.before, _SUBTRACT)
        if change.after is not None:
            _apply(month, change.after, _ADD)
    return month


def recompute(rounds: Iterable[Round]) -> Aggregates:
    """Berechnet alle Aggregate aus den Rohdaten neu (Referenz für die inkrementelle Pflege)."""
    result: Aggregates = {}
    for round_ in rounds:
        month = result.setdefault(month_key(round_.started_at), {})
        for assignment in round_.assignments:
            _apply(month, assignment, _ADD)
    return {key: month for key, month in result.items() if month}


def rows(aggregates: Mapping[str, object], keys: Iterable[str]) -> Iterator[StatRow]:
    """Liefert die Zellen der genannten Monate (fehlende Monate sind leer)."""
    for key in keys:
        month = decode_month(aggregates.get(key, {}))
        for person_id, by_task in month.items():
            for task_id, by_status in by_task.items():
                for status, cell in by_status.items():
                    yield StatRow(
                        person_id, task_id, AssignmentStatus(status), cell[_COUNT], cell[_POINTS]
                    )
