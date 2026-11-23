"""Domänenmodelle (KONZEPT §4): unveränderlich, mit Invarianten und Serialisierung."""

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, Final

from ..const import defaults, limits
from ..const.keys import ERR_INCONSISTENT, ERR_ORDER, ERR_REQUIRED
from .enums import (
    DONE_STATUSES,
    INTERVAL_UNIT_HOURS,
    WITHOUT_DONE_AT_STATUSES,
    AbsenceKind,
    AnimationKind,
    AssignmentStatus,
    EntryMode,
    IntervalUnit,
    Load,
    RoundOrigin,
    WeightingKind,
)
from .serialization import (
    Decoder,
    KindModel,
    Model,
    enum_of,
    frozenset_of,
    kind_model,
    model_of,
    optional,
    registry_of,
    spec,
    to_bool,
    to_date,
    to_datetime,
    to_float,
    to_int,
    to_str,
    tuple_of,
    unique_tuple_of,
)
from .types import AssignmentId, PersonId, RoundId, ScheduleId, TaskId, Weekday
from .validation import (
    ensure,
    ensure_aware,
    ensure_id,
    ensure_length,
    ensure_name,
    ensure_pattern,
    ensure_range,
    ensure_size,
    ensure_unique,
    ensure_weekdays,
)

# --- Anwesenheit --------------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class OnceAbsence(KindModel):
    """Einmalige Abwesenheit von `start` bis `end` (einschließlich)."""

    kind: ClassVar[AbsenceKind] = AbsenceKind.ONCE
    start: dt.date = spec(to_date)
    end: dt.date = spec(to_date)

    def __post_init__(self) -> None:
        """Prüft, dass das Ende nicht vor dem Beginn liegt."""
        ensure(self.start <= self.end, "end", ERR_ORDER)


@dataclass(slots=True, frozen=True, kw_only=True)
class WeeklyDaysAbsence(KindModel):
    """Abwesenheit an festen Wochentagen (Montag = 0)."""

    kind: ClassVar[AbsenceKind] = AbsenceKind.WEEKLY_DAYS
    weekdays: frozenset[Weekday] = spec(frozenset_of(to_int))

    def __post_init__(self) -> None:
        """Prüft die Wochentage."""
        ensure_weekdays("weekdays", self.weekdays)


@dataclass(slots=True, frozen=True, kw_only=True)
class WeekRhythmAbsence(KindModel):
    """Wochenrhythmus: anwesend in `present_weeks` eines Zyklus ab `anchor`."""

    kind: ClassVar[AbsenceKind] = AbsenceKind.WEEK_RHYTHM
    present_weeks: frozenset[int] = spec(frozenset_of(to_int))
    cycle_weeks: int = spec(to_int)
    change_weekday: Weekday = spec(to_int)
    anchor: dt.date = spec(to_date)

    def __post_init__(self) -> None:
        """Prüft Zykluslänge, Wechseltag und die Wochenindizes."""
        ensure_range(
            "cycle_weeks", self.cycle_weeks, limits.RHYTHM_CYCLE_MIN, limits.RHYTHM_CYCLE_MAX
        )
        ensure_range("change_weekday", self.change_weekday, limits.WEEKDAY_MIN, limits.WEEKDAY_MAX)
        ensure_size("present_weeks", self.present_weeks, 1, self.cycle_weeks)
        ensure(
            all(0 <= week < self.cycle_weeks for week in self.present_weeks),
            "present_weeks",
            ERR_INCONSISTENT,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class RecurringAbsence(KindModel):
    """Wiederkehrende Abwesenheit: an `weekdays` jeder `interval_weeks`-ten Woche ab `start`.

    Die Zählung beginnt mit der Woche (Montag bis Sonntag) von `start`; vor `start` und nach
    `end` (falls gesetzt, einschließlich) ist die Person anwesend.
    """

    kind: ClassVar[AbsenceKind] = AbsenceKind.RECURRING
    weekdays: frozenset[Weekday] = spec(frozenset_of(to_int))
    interval_weeks: int = spec(to_int)
    start: dt.date = spec(to_date)
    end: dt.date | None = spec(optional(to_date), default=None)

    def __post_init__(self) -> None:
        """Prüft Wochentage, Intervall und die Reihenfolge von Beginn und Ende."""
        ensure_weekdays("weekdays", self.weekdays)
        ensure_range(
            "interval_weeks",
            self.interval_weeks,
            limits.RECURRENCE_INTERVAL_MIN,
            limits.RECURRENCE_INTERVAL_MAX,
        )
        ensure(self.end is None or self.start <= self.end, "end", ERR_ORDER)


type AbsenceConfig = OnceAbsence | WeeklyDaysAbsence | WeekRhythmAbsence | RecurringAbsence

ABSENCE_REGISTRY: Mapping[str, type[AbsenceConfig]] = registry_of(
    OnceAbsence, WeeklyDaysAbsence, WeekRhythmAbsence, RecurringAbsence
)
decode_absence: Decoder[AbsenceConfig] = kind_model(ABSENCE_REGISTRY)

# --- Intervall und Aufgaben im Zeitplan ----------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class Interval(Model):
    """Abstand zwischen zwei Auslosungen: alle `every` Stunden, Tage oder Wochen."""

    unit: IntervalUnit = spec(enum_of(IntervalUnit), default=IntervalUnit.DAY)
    every: int = spec(to_int, default=defaults.DEFAULT_INTERVAL_EVERY)

    def __post_init__(self) -> None:
        """Prüft die Anzahl der Einheiten."""
        ensure_range("every", self.every, limits.INTERVAL_EVERY_MIN, limits.INTERVAL_EVERY_MAX)

    @property
    def hours(self) -> int:
        """Nennlänge des Intervalls in Stunden (Tag = 24, Woche = 168)."""
        return self.every * INTERVAL_UNIT_HOURS[self.unit]


@dataclass(slots=True, frozen=True, kw_only=True)
class ScheduleEntry(Model):
    """Eine Aufgabe im Zeitplan: „mindestens n-mal je Lauf“ oder „in jeder Auslosung“."""

    task_id: TaskId = spec(to_str)
    mode: EntryMode = spec(enum_of(EntryMode), default=EntryMode.MIN_COUNT)
    min_count: int = spec(to_int, default=defaults.DEFAULT_MIN_COUNT)

    def __post_init__(self) -> None:
        """Prüft Kennung und Mindestanzahl."""
        ensure_id("task_id", self.task_id)
        ensure_range("min_count", self.min_count, limits.MIN_COUNT_MIN, limits.MIN_COUNT_MAX)

    @property
    def every_draw(self) -> bool:
        """Die Aufgabe ist in jeder Auslosung dabei (Ausnahme vom Abstandsausgleich)."""
        return self.mode is EntryMode.EVERY_DRAW


# --- Personen, Aufgaben, Zeitpläne --------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class Person(Model):
    """Person im Rad (kein HA-Benutzer)."""

    id: PersonId = spec(to_str)
    name: str = spec(to_str)
    slug: str = spec(to_str)
    color: str = spec(to_str, default=defaults.DEFAULT_PERSON_COLOR)
    load: Load = spec(enum_of(Load), default=Load.FULL)
    absences: tuple[AbsenceConfig, ...] = spec(tuple_of(decode_absence), default=())
    notify_target: str | None = spec(optional(to_str), default=None)

    def __post_init__(self) -> None:
        """Prüft Kennung, Namen, Farbe, Abwesenheiten und Benachrichtigungsziel."""
        ensure_id("id", self.id)
        ensure_name("name", self.name)
        ensure_length("slug", self.slug, 1, limits.SLUG_MAX_LENGTH)
        ensure_pattern("slug", self.slug, limits.SLUG_PATTERN)
        ensure_pattern("color", self.color, limits.COLOR_PATTERN)
        ensure_size("absences", self.absences, 0, limits.MAX_ABSENCES_PER_PERSON)
        if self.notify_target is not None:
            ensure_length("notify_target", self.notify_target, 1, limits.NOTIFY_TARGET_MAX_LENGTH)


@dataclass(slots=True, frozen=True, kw_only=True)
class Task(Model):
    """Aufgabe mit Aufwand, erlaubten Personen und Regeln (die Häufigkeit gibt der Zeitplan vor).

    Ohne erlaubte Personen (leere Menge) gilt die Aufgabe für alle.
    """

    id: TaskId = spec(to_str)
    name: str = spec(to_str)
    allowed: frozenset[PersonId] = spec(frozenset_of(to_str), default=frozenset())
    points: int = spec(to_int, default=defaults.DEFAULT_TASK_POINTS)
    no_repeat: bool = spec(to_bool, default=False)
    respect_absence: bool = spec(to_bool, default=True)
    swap_allowed: bool = spec(to_bool, default=True)
    min_load: Load = spec(enum_of(Load), default=Load.PAUSED)
    area_ids: tuple[str, ...] = spec(unique_tuple_of(to_str), default=())

    def __post_init__(self) -> None:
        """Prüft Kennung, Namen, Punkte, erlaubte Personen und Räume."""
        ensure_id("id", self.id)
        ensure_name("name", self.name)
        ensure_range("points", self.points, limits.POINTS_MIN, limits.POINTS_MAX)
        ensure_size("allowed", self.allowed, 0, limits.MAX_PERSONS)
        for person_id in self.allowed:
            ensure_id("allowed", person_id)
        ensure_size("area_ids", self.area_ids, 0, limits.MAX_AREAS_PER_TASK)
        for area_id in self.area_ids:
            ensure_length("area_ids", area_id, 1, limits.AREA_ID_MAX_LENGTH)

    def allows(self, person_id: PersonId) -> bool:
        """Ob die Person die Aufgabe bekommen darf (ohne erlaubte Personen: jede)."""
        return not self.allowed or person_id in self.allowed

    def accepts_load(self, load: Load) -> bool:
        """Ob die Belastbarkeit für die Aufgabe reicht (Standard `paused`: jede)."""
        return load.factor >= self.min_load.factor


DEFAULT_ANIMATIONS: Final = (AnimationKind.WHEEL,)


@dataclass(slots=True, frozen=True, kw_only=True)
class Schedule(Model):
    """Zeitplan: Beginn, Intervall, Lauf und die Aufgaben mit ihrer Häufigkeit.

    Die Auslosungen („Perioden“) liegen im Raster `start + n · interval`; eine Zuteilung gilt bis
    zur nächsten. Ein Lauf umfasst `run_days` Tage: so oft soll jede Aufgabe mindestens
    vorkommen, wie ihr Eintrag verlangt. `automatic` steuert, ob zu jedem Termin von selbst
    ausgelost wird.
    """

    id: ScheduleId = spec(to_str)
    name: str = spec(to_str)
    slug: str = spec(to_str)
    start: dt.datetime = spec(to_datetime)
    interval: Interval = spec(model_of(Interval), default=Interval())
    automatic: bool = spec(to_bool, default=True)
    run_days: int = spec(to_int, default=defaults.DEFAULT_RUN_DAYS)
    entries: tuple[ScheduleEntry, ...] = spec(tuple_of(model_of(ScheduleEntry)))
    enabled: bool = spec(to_bool, default=True)
    notify: bool = spec(to_bool, default=True)
    skip_absent: bool = spec(to_bool, default=True)
    assign_everyone: bool = spec(to_bool, default=True)
    archived: bool = spec(to_bool, default=False)
    animations: tuple[AnimationKind, ...] = spec(
        tuple_of(enum_of(AnimationKind)), default=DEFAULT_ANIMATIONS
    )

    def __post_init__(self) -> None:
        """Prüft Kennung, Namen, Slug, Beginn, Lauf, Aufgaben, Animationen und Archivierung."""
        ensure_id("id", self.id)
        ensure_name("name", self.name)
        ensure_length("slug", self.slug, 1, limits.SLUG_MAX_LENGTH)
        ensure_pattern("slug", self.slug, limits.SLUG_PATTERN)
        ensure_aware("start", self.start)
        ensure_range("run_days", self.run_days, limits.RUN_DAYS_MIN, limits.RUN_DAYS_MAX)
        ensure(
            self.run_days * limits.HOURS_PER_DAY >= self.interval.hours,
            "run_days",
            ERR_INCONSISTENT,
        )
        ensure_size("entries", self.entries, 1, limits.MAX_TASKS_PER_SCHEDULE)
        ensure_unique("entries", self.task_ids)
        ensure_size("animations", self.animations, 0, len(AnimationKind))
        ensure_unique("animations", self.animations)
        ensure(not (self.archived and self.enabled), "archived", ERR_INCONSISTENT)

    @property
    def task_ids(self) -> tuple[TaskId, ...]:
        """Die Aufgaben des Zeitplans in der Reihenfolge der Einträge."""
        return tuple(entry.task_id for entry in self.entries)

    @property
    def draws_per_run(self) -> int:
        """Anzahl der Auslosungen je Lauf: Laufdauer geteilt durch das Intervall (abgerundet)."""
        return self.run_days * limits.HOURS_PER_DAY // self.interval.hours

    def entry_for(self, task_id: TaskId) -> ScheduleEntry | None:
        """Der Eintrag der Aufgabe (`None`, wenn sie nicht zum Zeitplan gehört)."""
        return next((entry for entry in self.entries if entry.task_id == task_id), None)


# --- Runden und Zuteilungen ---------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class Swap(Model):
    """Tausch einer Zuteilung auf eine andere Person."""

    from_person_id: PersonId = spec(to_str)
    to_person_id: PersonId = spec(to_str)
    at: dt.datetime = spec(to_datetime)

    def __post_init__(self) -> None:
        """Prüft, dass wirklich zwischen zwei Personen getauscht wird."""
        ensure(self.from_person_id != self.to_person_id, "to_person_id", ERR_INCONSISTENT)
        ensure_aware("at", self.at)


@dataclass(slots=True, frozen=True, kw_only=True)
class Assignment(Model):
    """Zuteilung einer Aufgabe an eine Person innerhalb einer Runde des auslosenden Zeitplans."""

    id: AssignmentId = spec(to_str)
    round_id: RoundId = spec(to_str)
    schedule_id: ScheduleId = spec(to_str)
    task_id: TaskId = spec(to_str)
    person_id: PersonId = spec(to_str)
    chance: float = spec(to_float)
    points: int = spec(to_int)
    due_at: dt.datetime = spec(to_datetime)
    starts_at: dt.datetime | None = spec(optional(to_datetime), default=None)
    status: AssignmentStatus = spec(enum_of(AssignmentStatus), default=AssignmentStatus.OPEN)
    done_at: dt.datetime | None = spec(optional(to_datetime), default=None)
    swap: Swap | None = spec(optional(model_of(Swap)), default=None)

    def __post_init__(self) -> None:
        """Prüft Kennungen, Chance, Zeitzonen und die Zuordnung von Status und Erledigungszeit."""
        for name in ("id", "round_id", "schedule_id", "task_id", "person_id"):
            ensure_id(name, getattr(self, name))
        ensure_range("chance", self.chance, limits.CHANCE_MIN, limits.CHANCE_MAX)
        ensure_aware("due_at", self.due_at)
        if self.starts_at is not None:
            ensure_aware("starts_at", self.starts_at)
            ensure(self.starts_at <= self.due_at, "starts_at", ERR_ORDER)
        if self.done_at is not None:
            ensure_aware("done_at", self.done_at)
        ensure(
            self.status not in DONE_STATUSES or self.done_at is not None, "done_at", ERR_REQUIRED
        )
        ensure(
            self.status not in WITHOUT_DONE_AT_STATUSES or self.done_at is None,
            "done_at",
            ERR_INCONSISTENT,
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class Round(Model):
    """Eine Auslosung eines Zeitplans mit ihren Zuteilungen.

    `period_index` ist die Nummer der Periode im Raster des Zeitplans (0 = Beginn).
    """

    id: RoundId = spec(to_str)
    schedule_id: ScheduleId = spec(to_str)
    origin: RoundOrigin = spec(enum_of(RoundOrigin))
    started_at: dt.datetime = spec(to_datetime)
    finished_at: dt.datetime | None = spec(optional(to_datetime), default=None)
    period_index: int = spec(to_int, default=limits.PERIOD_INDEX_MIN)
    assignments: tuple[Assignment, ...] = spec(tuple_of(model_of(Assignment)), default=())

    def __post_init__(self) -> None:
        """Prüft Kennungen, Zeitfolge und die Zugehörigkeit der Zuteilungen."""
        ensure_id("id", self.id)
        ensure_id("schedule_id", self.schedule_id)
        ensure_aware("started_at", self.started_at)
        if self.finished_at is not None:
            ensure_aware("finished_at", self.finished_at)
            ensure(self.started_at <= self.finished_at, "finished_at", ERR_ORDER)
        ensure_range(
            "period_index", self.period_index, limits.PERIOD_INDEX_MIN, limits.PERIOD_INDEX_MAX
        )
        ensure_size("assignments", self.assignments, 0, limits.MAX_ASSIGNMENTS_PER_ROUND)
        ensure_unique("assignments", (item.id for item in self.assignments))
        ensure(
            all(
                item.round_id == self.id and item.schedule_id == self.schedule_id
                for item in self.assignments
            ),
            "assignments",
            ERR_INCONSISTENT,
        )


# --- Einstellungen ------------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class Settings(Model):
    """Globale Einstellungen (Options Flow)."""

    jokers_per_month: int = spec(to_int, default=defaults.DEFAULT_JOKERS_PER_MONTH)
    fairness_window_days: int = spec(to_int, default=defaults.DEFAULT_FAIRNESS_WINDOW_DAYS)
    history_retention_days: int = spec(to_int, default=defaults.DEFAULT_HISTORY_RETENTION_DAYS)
    weighting: WeightingKind = spec(enum_of(WeightingKind), default=WeightingKind.FAIRNESS)
    late_points_factor: float = spec(to_float, default=defaults.DEFAULT_LATE_POINTS_FACTOR)
    missed_points_factor: float = spec(to_float, default=defaults.DEFAULT_MISSED_POINTS_FACTOR)
    missed_grace_hours: int = spec(to_int, default=defaults.DEFAULT_MISSED_GRACE_HOURS)
    panel_admin_only: bool = spec(to_bool, default=defaults.DEFAULT_PANEL_ADMIN_ONLY)
    decision_retention_days: int = spec(to_int, default=defaults.DEFAULT_DECISION_RETENTION_DAYS)

    def __post_init__(self) -> None:
        """Prüft alle Grenzen aus `const/limits.py`."""
        ensure_range(
            "jokers_per_month", self.jokers_per_month, limits.JOKERS_MIN, limits.JOKERS_MAX
        )
        ensure_range(
            "fairness_window_days",
            self.fairness_window_days,
            limits.FAIRNESS_WINDOW_MIN,
            limits.FAIRNESS_WINDOW_MAX,
        )
        ensure_range(
            "history_retention_days",
            self.history_retention_days,
            limits.RETENTION_MIN,
            limits.RETENTION_MAX,
        )
        ensure_range(
            "decision_retention_days",
            self.decision_retention_days,
            limits.DECISION_RETENTION_MIN,
            limits.DECISION_RETENTION_MAX,
        )
        ensure_range(
            "late_points_factor",
            self.late_points_factor,
            limits.LATE_FACTOR_MIN,
            limits.LATE_FACTOR_MAX,
        )
        ensure_range(
            "missed_points_factor",
            self.missed_points_factor,
            limits.MISSED_FACTOR_MIN,
            limits.MISSED_FACTOR_MAX,
        )
        ensure_range(
            "missed_grace_hours",
            self.missed_grace_hours,
            limits.GRACE_HOURS_MIN,
            limits.GRACE_HOURS_MAX,
        )
