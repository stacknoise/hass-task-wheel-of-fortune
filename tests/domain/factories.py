"""Hilfsfunktionen zum Erzeugen gültiger Modelle in Tests."""

import datetime as dt

from custom_components.task_wheel.domain.enums import (
    AssignmentStatus,
    EntryMode,
    IntervalUnit,
    Load,
    RoundOrigin,
    WeightingKind,
)
from custom_components.task_wheel.domain.models import (
    Assignment,
    Interval,
    OnceAbsence,
    Person,
    Round,
    Schedule,
    ScheduleEntry,
    Settings,
    Swap,
    Task,
    WeeklyDaysAbsence,
    WeekRhythmAbsence,
)

TZ = dt.UTC
NOW = dt.datetime(2026, 11, 3, 10, 0, tzinfo=TZ)
TODAY = NOW.date()


def person(**overrides: object) -> Person:
    values: dict[str, object] = {
        "id": "p1",
        "name": "Anna",
        "slug": "anna",
        "absences": (
            OnceAbsence(start=TODAY, end=TODAY + dt.timedelta(days=3)),
            WeeklyDaysAbsence(weekdays=frozenset({5, 6})),
            WeekRhythmAbsence(
                present_weeks=frozenset({0}), cycle_weeks=2, change_weekday=4, anchor=TODAY
            ),
        ),
        "load": Load.HALF,
        "notify_target": "notify.anna",
    }
    return Person(**{**values, **overrides})  # type: ignore[arg-type]


def task(**overrides: object) -> Task:
    values: dict[str, object] = {
        "id": "t1",
        "name": "Müll",
        "allowed": frozenset({"p1", "p2"}),
        "points": 3,
    }
    return Task(**{**values, **overrides})  # type: ignore[arg-type]


def entries(
    *task_ids: str, every_draw: bool = True, min_count: int = 1
) -> tuple[ScheduleEntry, ...]:
    """Einträge für die Aufgaben (Standard: „jede Auslosung“)."""
    mode = EntryMode.EVERY_DRAW if every_draw else EntryMode.MIN_COUNT
    return tuple(ScheduleEntry(task_id=i, mode=mode, min_count=min_count) for i in task_ids)


def schedule(**overrides: object) -> Schedule:
    """Zeitplan; `task_ids` ist eine Abkürzung für Einträge „jede Auslosung“."""
    task_ids = overrides.pop("task_ids", ("t1", "t2"))
    values: dict[str, object] = {
        "id": "s1",
        "name": "Wochenrunde",
        "slug": "wochenrunde",
        "start": NOW,
        "interval": Interval(unit=IntervalUnit.DAY, every=1),
        "entries": entries(*task_ids),  # type: ignore[arg-type]
    }
    return Schedule(**{**values, **overrides})  # type: ignore[arg-type]


def swap() -> Swap:
    return Swap(from_person_id="p1", to_person_id="p2", at=NOW)


def assignment(**overrides: object) -> Assignment:
    values: dict[str, object] = {
        "id": "a1",
        "round_id": "r1",
        "schedule_id": "s1",
        "task_id": "t1",
        "person_id": "p1",
        "chance": 0.25,
        "points": 3,
        "due_at": NOW + dt.timedelta(days=7),
    }
    return Assignment(**{**values, **overrides})  # type: ignore[arg-type]


def finished_round(**overrides: object) -> Round:
    schedule_id = overrides.get("schedule_id", "s1")
    values: dict[str, object] = {
        "id": "r1",
        "schedule_id": schedule_id,
        "origin": RoundOrigin.MANUAL,
        "started_at": NOW,
        "finished_at": NOW + dt.timedelta(minutes=2),
        "assignments": (
            assignment(schedule_id=schedule_id),
            assignment(
                id="a2",
                schedule_id=schedule_id,
                status=AssignmentStatus.SWAPPED,
                swap=swap(),
                person_id="p2",
            ),
            assignment(id="a3", schedule_id=schedule_id, status=AssignmentStatus.LATE, done_at=NOW),
        ),
    }
    return Round(**{**values, **overrides})  # type: ignore[arg-type]


def settings(**overrides: object) -> Settings:
    return Settings(**{"weighting": WeightingKind.UNIFORM, **overrides})  # type: ignore[arg-type]
