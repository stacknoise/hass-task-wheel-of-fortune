"""Hilfsfunktionen zum Erzeugen gültiger Modelle in Tests."""

import datetime as dt

from custom_components.task_wheel.domain.enums import (
    AfterOnce,
    AssignmentStatus,
    Load,
    Period,
    RoundOrigin,
    WeightingKind,
)
from custom_components.task_wheel.domain.models import (
    Assignment,
    Interval,
    ManualTrigger,
    MaxPerPeriod,
    OnceAbsence,
    OnceTrigger,
    Person,
    Recurring,
    Round,
    Schedule,
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
        "frequency": MaxPerPeriod(count=2, period=Period.WEEK),
        "points": 3,
    }
    return Task(**{**values, **overrides})  # type: ignore[arg-type]


def interval_task() -> Task:
    return task(frequency=Interval(days=14, tolerance=2))


def schedule(**overrides: object) -> Schedule:
    values: dict[str, object] = {
        "id": "s1",
        "name": "Wochenrunde",
        "slug": "wochenrunde",
        "trigger": Recurring(
            weekdays=frozenset({0, 3}),
            time=dt.time(18, 30),
            every_n_weeks=2,
            anchor=TODAY,
        ),
        "task_ids": ("t1", "t2"),
    }
    return Schedule(**{**values, **overrides})  # type: ignore[arg-type]


def once_trigger() -> OnceTrigger:
    return OnceTrigger(at=NOW, after=AfterOnce.ARCHIVE)


def manual_trigger() -> ManualTrigger:
    return ManualTrigger(remind_after_days=7)


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
