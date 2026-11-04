"""Domänenmodelle (KONZEPT §4): unveränderlich, mit Invarianten und Serialisierung."""

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, Final, cast

from ..const import defaults, limits
from ..const.keys import ERR_INCONSISTENT, ERR_ORDER, ERR_REQUIRED
from .enums import (
    AbsenceKind,
    AfterOnce,
    AnimationKind,
    AssignmentStatus,
    FrequencyKind,
    Load,
    Period,
    RoundOrigin,
    TriggerKind,
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
    to_time,
    tuple_of,
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


type AbsenceConfig = OnceAbsence | WeeklyDaysAbsence | WeekRhythmAbsence

ABSENCE_REGISTRY: Mapping[str, type[AbsenceConfig]] = registry_of(
    OnceAbsence, WeeklyDaysAbsence, WeekRhythmAbsence
)
decode_absence: Decoder[AbsenceConfig] = kind_model(ABSENCE_REGISTRY)

# --- Häufigkeit ---------------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class EveryRound(KindModel):
    """Aufgabe kommt in jeder Runde dran."""

    kind: ClassVar[FrequencyKind] = FrequencyKind.EVERY_ROUND


@dataclass(slots=True, frozen=True, kw_only=True)
class MaxPerPeriod(KindModel):
    """Höchstens `count` Zuteilungen je Tag, Woche oder Monat."""

    kind: ClassVar[FrequencyKind] = FrequencyKind.MAX_PER_PERIOD
    count: int = spec(to_int)
    period: Period = spec(enum_of(Period))

    def __post_init__(self) -> None:
        """Prüft die Anzahl."""
        ensure_range("count", self.count, limits.PERIOD_COUNT_MIN, limits.PERIOD_COUNT_MAX)


@dataclass(slots=True, frozen=True, kw_only=True)
class Interval(KindModel):
    """Frühestens nach `days` Tagen (abzüglich `tolerance`) erneut."""

    kind: ClassVar[FrequencyKind] = FrequencyKind.INTERVAL
    days: int = spec(to_int)
    tolerance: int = spec(to_int, default=defaults.DEFAULT_INTERVAL_TOLERANCE)

    def __post_init__(self) -> None:
        """Prüft Abstand und Toleranz (Toleranz kleiner als der Abstand)."""
        ensure_range("days", self.days, limits.INTERVAL_DAYS_MIN, limits.INTERVAL_DAYS_MAX)
        ensure_range("tolerance", self.tolerance, limits.INTERVAL_TOLERANCE_MIN, self.days - 1)


type FrequencyConfig = EveryRound | MaxPerPeriod | Interval

FREQUENCY_REGISTRY: Mapping[str, type[FrequencyConfig]] = registry_of(
    EveryRound, MaxPerPeriod, Interval
)
decode_frequency: Decoder[FrequencyConfig] = kind_model(FREQUENCY_REGISTRY)
DEFAULT_FREQUENCY: Final = cast("FrequencyConfig", EveryRound())

# --- Auslöser -----------------------------------------------------------------------------------


@dataclass(slots=True, frozen=True, kw_only=True)
class Recurring(KindModel):
    """Wiederkehrend an Wochentagen zu einer Uhrzeit, alle n Wochen (Ankerdatum) oder monatlich."""

    kind: ClassVar[TriggerKind] = TriggerKind.RECURRING
    weekdays: frozenset[Weekday] = spec(frozenset_of(to_int))
    time: dt.time = spec(to_time)
    every_n_weeks: int = spec(to_int, default=defaults.DEFAULT_EVERY_N_WEEKS)
    monthly: bool = spec(to_bool, default=False)
    anchor: dt.date | None = spec(optional(to_date), default=None)

    def __post_init__(self) -> None:
        """Prüft Wochentage, Rhythmus und Ankerdatum."""
        ensure_weekdays("weekdays", self.weekdays)
        ensure_range(
            "every_n_weeks", self.every_n_weeks, limits.EVERY_N_WEEKS_MIN, limits.EVERY_N_WEEKS_MAX
        )
        ensure(
            not self.monthly or self.every_n_weeks == defaults.DEFAULT_EVERY_N_WEEKS,
            "monthly",
            ERR_INCONSISTENT,
        )
        needs_anchor = self.every_n_weeks > defaults.DEFAULT_EVERY_N_WEEKS
        ensure(not needs_anchor or self.anchor is not None, "anchor", ERR_REQUIRED)


@dataclass(slots=True, frozen=True, kw_only=True)
class OnceTrigger(KindModel):
    """Einmalig zu einem Zeitpunkt; danach behalten (nur manuell), archivieren oder löschen."""

    kind: ClassVar[TriggerKind] = TriggerKind.ONCE
    at: dt.datetime = spec(to_datetime)
    after: AfterOnce = spec(enum_of(AfterOnce), default=AfterOnce.KEEP_MANUAL)

    def __post_init__(self) -> None:
        """Prüft die Zeitzone."""
        ensure_aware("at", self.at)


@dataclass(slots=True, frozen=True, kw_only=True)
class ManualTrigger(KindModel):
    """Nur manuell; optional Erinnerung nach `remind_after_days` Tagen ohne Auslosung."""

    kind: ClassVar[TriggerKind] = TriggerKind.MANUAL
    remind_after_days: int | None = spec(optional(to_int), default=None)

    def __post_init__(self) -> None:
        """Prüft die Erinnerungsfrist."""
        if self.remind_after_days is not None:
            ensure_range(
                "remind_after_days",
                self.remind_after_days,
                limits.REMIND_AFTER_DAYS_MIN,
                limits.REMIND_AFTER_DAYS_MAX,
            )


type TriggerConfig = Recurring | OnceTrigger | ManualTrigger

TRIGGER_REGISTRY: Mapping[str, type[TriggerConfig]] = registry_of(
    Recurring, OnceTrigger, ManualTrigger
)
decode_trigger: Decoder[TriggerConfig] = kind_model(TRIGGER_REGISTRY)

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
    """Aufgabe mit Aufwand, Frist, erlaubten Personen und Regeln.

    Ohne erlaubte Personen (leere Menge) gilt die Aufgabe für alle.
    """

    id: TaskId = spec(to_str)
    name: str = spec(to_str)
    allowed: frozenset[PersonId] = spec(frozenset_of(to_str), default=frozenset())
    frequency: FrequencyConfig = spec(decode_frequency, default=DEFAULT_FREQUENCY)
    points: int = spec(to_int, default=defaults.DEFAULT_TASK_POINTS)
    due_days: int = spec(to_int, default=defaults.DEFAULT_TASK_DUE_DAYS)
    no_repeat: bool = spec(to_bool, default=False)
    respect_absence: bool = spec(to_bool, default=True)
    swap_allowed: bool = spec(to_bool, default=True)
    min_load: Load = spec(enum_of(Load), default=Load.PAUSED)
    area_id: str | None = spec(optional(to_str), default=None)

    def __post_init__(self) -> None:
        """Prüft Kennung, Namen, Punkte, Frist, erlaubte Personen und Bereich."""
        ensure_id("id", self.id)
        ensure_name("name", self.name)
        ensure_range("points", self.points, limits.POINTS_MIN, limits.POINTS_MAX)
        ensure_range("due_days", self.due_days, limits.DUE_DAYS_MIN, limits.DUE_DAYS_MAX)
        ensure_size("allowed", self.allowed, 0, limits.MAX_PERSONS)
        for person_id in self.allowed:
            ensure_id("allowed", person_id)
        if self.area_id is not None:
            ensure_length("area_id", self.area_id, 1, limits.AREA_ID_MAX_LENGTH)

    def allows(self, person_id: PersonId) -> bool:
        """Ob die Person die Aufgabe bekommen darf (ohne erlaubte Personen: jede)."""
        return not self.allowed or person_id in self.allowed

    def accepts_load(self, load: Load) -> bool:
        """Ob die Belastbarkeit für die Aufgabe reicht (Standard `paused`: jede)."""
        return load.factor >= self.min_load.factor


DEFAULT_ANIMATIONS: Final = (AnimationKind.WHEEL,)


@dataclass(slots=True, frozen=True, kw_only=True)
class Schedule(Model):
    """Zeitplan: Auslöser und die Aufgaben, die er verteilt."""

    id: ScheduleId = spec(to_str)
    name: str = spec(to_str)
    slug: str = spec(to_str)
    trigger: TriggerConfig = spec(decode_trigger)
    task_ids: tuple[TaskId, ...] = spec(tuple_of(to_str))
    enabled: bool = spec(to_bool, default=True)
    notify: bool = spec(to_bool, default=True)
    skip_absent: bool = spec(to_bool, default=True)
    archived: bool = spec(to_bool, default=False)
    animations: tuple[AnimationKind, ...] = spec(
        tuple_of(enum_of(AnimationKind)), default=DEFAULT_ANIMATIONS
    )

    def __post_init__(self) -> None:
        """Prüft Kennung, Namen, Slug, Aufgaben, Animationen und Archivierung."""
        ensure_id("id", self.id)
        ensure_name("name", self.name)
        ensure_length("slug", self.slug, 1, limits.SLUG_MAX_LENGTH)
        ensure_pattern("slug", self.slug, limits.SLUG_PATTERN)
        ensure_size("task_ids", self.task_ids, 1, limits.MAX_TASKS_PER_SCHEDULE)
        ensure_unique("task_ids", self.task_ids)
        ensure_size("animations", self.animations, 1, len(AnimationKind))
        ensure_unique("animations", self.animations)
        ensure(not (self.archived and self.enabled), "archived", ERR_INCONSISTENT)


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


_DONE_STATUSES = frozenset({AssignmentStatus.ON_TIME, AssignmentStatus.LATE})
_UNDONE_STATUSES = frozenset(
    {AssignmentStatus.OPEN, AssignmentStatus.MISSED, AssignmentStatus.SKIPPED}
)


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
    status: AssignmentStatus = spec(enum_of(AssignmentStatus), default=AssignmentStatus.OPEN)
    done_at: dt.datetime | None = spec(optional(to_datetime), default=None)
    swap: Swap | None = spec(optional(model_of(Swap)), default=None)

    def __post_init__(self) -> None:
        """Prüft Kennungen, Chance, Zeitzonen und die Zuordnung von Status und Erledigungszeit."""
        for name in ("id", "round_id", "schedule_id", "task_id", "person_id"):
            ensure_id(name, getattr(self, name))
        ensure_range("chance", self.chance, limits.CHANCE_MIN, limits.CHANCE_MAX)
        ensure_aware("due_at", self.due_at)
        if self.done_at is not None:
            ensure_aware("done_at", self.done_at)
        ensure(
            self.status not in _DONE_STATUSES or self.done_at is not None, "done_at", ERR_REQUIRED
        )
        ensure(
            self.status not in _UNDONE_STATUSES or self.done_at is None, "done_at", ERR_INCONSISTENT
        )


@dataclass(slots=True, frozen=True, kw_only=True)
class Round(Model):
    """Eine Auslosung eines Zeitplans mit ihren Zuteilungen."""

    id: RoundId = spec(to_str)
    schedule_id: ScheduleId = spec(to_str)
    origin: RoundOrigin = spec(enum_of(RoundOrigin))
    started_at: dt.datetime = spec(to_datetime)
    finished_at: dt.datetime | None = spec(optional(to_datetime), default=None)
    assignments: tuple[Assignment, ...] = spec(tuple_of(model_of(Assignment)), default=())

    def __post_init__(self) -> None:
        """Prüft Kennungen, Zeitfolge und die Zugehörigkeit der Zuteilungen."""
        ensure_id("id", self.id)
        ensure_id("schedule_id", self.schedule_id)
        ensure_aware("started_at", self.started_at)
        if self.finished_at is not None:
            ensure_aware("finished_at", self.finished_at)
            ensure(self.started_at <= self.finished_at, "finished_at", ERR_ORDER)
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
