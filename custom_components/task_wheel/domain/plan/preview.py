"""Vorschau eines Zeitplans: Platz, Belegung, Abstände und Warnungen (Editor, ohne Speichern).

Die Vorschau legt für jede Aufgabe die Auslosungen eines Laufs gleichmäßig verteilt fest (Phase so
gewählt, dass die Auslosungen möglichst gleich belegt sind). Die echte Auslosung rechnet dynamisch
mit demselben Zielabstand (`domain/plan/due.py`); die Vorschau zeigt, was sich im Mittel ergibt.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise

from ..models import ScheduleEntry
from ..types import PersonId, TaskId

ISSUE_NO_TASKS = "no_tasks"
ISSUE_INTERVAL_TOO_LONG = "interval_too_long"
ISSUE_NO_PERSON = "no_person"
ISSUE_TOO_OFTEN = "too_often"
ISSUE_OVERLOAD = "overload"
ISSUE_GAPS = "gaps"

PARAM_TASK_ID = "task_id"
PARAM_WANTED = "wanted"
PARAM_DRAWS = "draws"
PARAM_COUNT = "count"
PARAM_PEAK = "peak"
PARAM_PERSONS = "persons"


@dataclass(slots=True, frozen=True)
class PlanIssue:
    """Ein Hinweis zur Planung: `blocking` verhindert das Speichern, sonst nur eine Warnung."""

    code: str
    blocking: bool
    params: Mapping[str, int | str] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class PlanTrack:
    """Abstände einer Aufgabe: die Auslosungen eines Laufs und kleinster/größter Abstand."""

    task_id: TaskId
    every_draw: bool
    wanted: int
    positions: tuple[int, ...]
    gap_min: int
    gap_max: int


@dataclass(slots=True, frozen=True)
class PlanPreview:
    """Ergebnis der Vorschau."""

    draws_per_run: int
    interval_hours: int
    persons: Mapping[PersonId, int]
    planned: int
    capacity: int
    empty_draws: int
    overloaded_draws: int
    peak: int
    tracks: tuple[PlanTrack, ...]
    issues: tuple[PlanIssue, ...]

    @property
    def savable(self) -> bool:
        """Der Zeitplan darf gespeichert werden (nur Warnungen, nichts Sperrendes)."""
        return not any(issue.blocking for issue in self.issues)


def _positions(loads: list[int], count: int, draws: int) -> tuple[int, ...]:
    """Auslosungen einer Aufgabe: gleichmäßig verteilt, Phase mit der geringsten Belegung."""
    gap = draws / count
    best_offset, best_key = 0, (math.inf, math.inf)
    for offset in range(max(1, math.ceil(gap))):
        slots = [min(draws - 1, math.floor(offset + k * gap)) for k in range(count)]
        key = (max(loads[p] + 1 for p in slots), sum(loads[p] for p in slots))
        if key < best_key:
            best_offset, best_key = offset, key
    slots = [min(draws - 1, math.floor(best_offset + k * gap)) for k in range(count)]
    return tuple(dict.fromkeys(slots))


def _gaps(positions: Sequence[int], draws: int) -> tuple[int, int]:
    """Kleinster und größter Abstand (in Auslosungen), auch über die Grenze zum nächsten Lauf."""
    if not positions:
        return draws, draws
    gaps = [b - a for a, b in pairwise(positions)]
    gaps.append(positions[0] + draws - positions[-1])
    return min(gaps), max(gaps)


def _place(
    entries: Sequence[ScheduleEntry], draws: int
) -> tuple[list[int], dict[TaskId, tuple[int, ...]], dict[TaskId, int]]:
    """Belegung je Auslosung, Auslosungen je Aufgabe und gewünschte Anzahl (höchstens `draws`)."""
    loads = [0] * draws
    placed: dict[TaskId, tuple[int, ...]] = {}
    counts = {e.task_id: draws if e.every_draw else min(e.min_count, draws) for e in entries}
    ordered = sorted(entries, key=lambda e: (not e.every_draw, -counts[e.task_id]))
    for entry in ordered:
        if entry.every_draw:
            positions = tuple(range(draws))
        else:
            positions = _positions(loads, counts[entry.task_id], draws)
        for position in positions:
            loads[position] += 1
        placed[entry.task_id] = positions
    return loads, placed, counts


def _blocking_issues(
    entries: Sequence[ScheduleEntry], draws: int, person_tasks: Mapping[PersonId, int]
) -> list[PlanIssue]:
    """Probleme, die das Speichern verhindern: keine Aufgabe, Intervall zu lang, keine Person."""
    checks = (
        (not entries, ISSUE_NO_TASKS),
        (draws < 1, ISSUE_INTERVAL_TOO_LONG),
        (bool(entries) and not person_tasks, ISSUE_NO_PERSON),
    )
    return [PlanIssue(code, blocking=True) for failed, code in checks if failed]


def _warnings(
    entries: Sequence[ScheduleEntry], draws: int, loads: Sequence[int], persons: int
) -> list[PlanIssue]:
    """Warnungen: Aufgaben zu oft gewünscht, Überlast und Auslosungen ohne fällige Aufgabe."""
    issues = [
        PlanIssue(
            ISSUE_TOO_OFTEN,
            blocking=False,
            params={PARAM_TASK_ID: e.task_id, PARAM_WANTED: e.min_count, PARAM_DRAWS: draws},
        )
        for e in entries
        if not e.every_draw and e.min_count > draws
    ]
    over = sum(load > persons for load in loads)
    empty = loads.count(0)
    if over:
        params = {
            PARAM_COUNT: over,
            PARAM_DRAWS: draws,
            PARAM_PEAK: max(loads),
            PARAM_PERSONS: persons,
        }
        issues.append(PlanIssue(ISSUE_OVERLOAD, blocking=False, params=params))
    if empty:
        params = {PARAM_COUNT: empty, PARAM_DRAWS: draws}
        issues.append(PlanIssue(ISSUE_GAPS, blocking=False, params=params))
    return issues


def evaluate_plan(
    entries: Sequence[ScheduleEntry],
    draws: int,
    interval_hours: int,
    reach: Mapping[TaskId, frozenset[PersonId]],
) -> PlanPreview:
    """Bewertet einen Zeitplan: `reach` nennt je Aufgabe die Personen, die sie übernehmen dürfen."""
    person_tasks: dict[PersonId, int] = {}
    for entry in entries:
        for person_id in reach.get(entry.task_id, frozenset()):
            person_tasks[person_id] = person_tasks.get(person_id, 0) + 1
    blocking = _blocking_issues(entries, draws, person_tasks)
    if blocking:
        return PlanPreview(
            max(draws, 0), interval_hours, person_tasks, 0, 0, 0, 0, 0, (), tuple(blocking)
        )
    loads, placed, counts = _place(entries, draws)
    persons = len(person_tasks)
    tracks = tuple(
        PlanTrack(
            e.task_id,
            e.every_draw,
            e.min_count,
            placed[e.task_id],
            *_gaps(placed[e.task_id], draws),
        )
        for e in entries
    )
    return PlanPreview(
        draws,
        interval_hours,
        person_tasks,
        sum(counts.values()),
        draws * min(persons, len(entries)),
        loads.count(0),
        sum(load > persons for load in loads),
        max(loads),
        tracks,
        tuple(_warnings(entries, draws, loads, persons)),
    )
