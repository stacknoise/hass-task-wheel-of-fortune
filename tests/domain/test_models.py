"""Rundreise der Serialisierung und Invarianten aller Modelle."""

import datetime as dt
import json

import pytest

from custom_components.task_wheel.const import defaults, limits
from custom_components.task_wheel.const.keys import KEY_KIND
from custom_components.task_wheel.domain.enums import AnimationKind, AssignmentStatus, Load, Period
from custom_components.task_wheel.domain.errors import (
    TaskWheelError,
    UnknownKindError,
    ValidationError,
)
from custom_components.task_wheel.domain.models import (
    Assignment,
    EveryRound,
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
    decode_trigger,
)

from . import factories as f

ROUNDTRIP = [
    f.person(),
    f.task(),
    f.interval_task(),
    f.task(frequency=EveryRound()),
    f.schedule(),
    f.schedule(trigger=f.once_trigger()),
    f.schedule(trigger=f.manual_trigger()),
    f.swap(),
    f.assignment(),
    f.finished_round(),
    f.settings(),
    Settings(),
    OnceAbsence(start=f.TODAY, end=f.TODAY),
]


@pytest.mark.parametrize("model", ROUNDTRIP, ids=lambda m: type(m).__name__)
def test_roundtrip_through_json(model):
    data = json.loads(json.dumps(model.to_dict()))
    assert type(model).from_dict(data) == model


def test_kind_models_carry_kind():
    assert f.task().to_dict()["frequency"][KEY_KIND] == "max_per_period"
    assert f.person().to_dict()["absences"][0][KEY_KIND] == "once"


def test_defaults_applied_when_fields_missing():
    person = Person.from_dict({"id": "p", "name": "Bo", "slug": "bo"})
    assert person.load is Load.FULL
    assert person.color == defaults.DEFAULT_PERSON_COLOR
    assert Settings.from_dict({}) == Settings()


def test_models_are_frozen_and_slotted():
    person = f.person()
    with pytest.raises(AttributeError):
        person.name = "x"  # type: ignore[misc]
    assert not hasattr(person, "__dict__")


def test_load_factors():
    assert [load.factor for load in Load] == [
        defaults.LOAD_FACTOR_FULL,
        defaults.LOAD_FACTOR_HALF,
        defaults.LOAD_FACTOR_PAUSED,
    ]


@pytest.mark.parametrize(
    ("build", "field"),
    [
        (lambda: OnceAbsence(start=f.TODAY, end=f.TODAY - dt.timedelta(days=1)), "end"),
        (lambda: WeeklyDaysAbsence(weekdays=frozenset()), "weekdays"),
        (lambda: WeeklyDaysAbsence(weekdays=frozenset({7})), "weekdays"),
        (
            lambda: WeekRhythmAbsence(
                present_weeks=frozenset({2}), cycle_weeks=2, change_weekday=0, anchor=f.TODAY
            ),
            "present_weeks",
        ),
        (
            lambda: WeekRhythmAbsence(
                present_weeks=frozenset({0}), cycle_weeks=9, change_weekday=0, anchor=f.TODAY
            ),
            "cycle_weeks",
        ),
        (
            lambda: WeekRhythmAbsence(
                present_weeks=frozenset({0}), cycle_weeks=2, change_weekday=7, anchor=f.TODAY
            ),
            "change_weekday",
        ),
        (lambda: MaxPerPeriod(count=0, period=Period.DAY), "count"),
        (lambda: Interval(days=0), "days"),
        (lambda: Interval(days=3, tolerance=3), "tolerance"),
        (lambda: Recurring(weekdays=frozenset(), time=dt.time(8)), "weekdays"),
        (
            lambda: Recurring(weekdays=frozenset({1}), time=dt.time(8), every_n_weeks=0),
            "every_n_weeks",
        ),
        (
            lambda: Recurring(
                weekdays=frozenset({1}),
                time=dt.time(8),
                every_n_weeks=2,
                monthly=True,
                anchor=f.TODAY,
            ),
            "monthly",
        ),
        (lambda: Recurring(weekdays=frozenset({1}), time=dt.time(8), every_n_weeks=2), "anchor"),
        (lambda: OnceTrigger(at=dt.datetime(2026, 1, 1)), "at"),
        (lambda: ManualTrigger(remind_after_days=0), "remind_after_days"),
        (lambda: f.person(id=""), "id"),
        (lambda: f.person(name=" Anna"), "name"),
        (lambda: f.person(name="x" * (limits.NAME_MAX_LENGTH + 1)), "name"),
        (lambda: f.person(slug="Not Valid"), "slug"),
        (lambda: f.person(color="red"), "color"),
        (lambda: f.person(color="#ABCDEF"), "color"),
        (lambda: f.person(notify_target=""), "notify_target"),
        (lambda: f.person(absences=(OnceAbsence(start=f.TODAY, end=f.TODAY),) * 21), "absences"),
        (lambda: f.task(points=0), "points"),
        (lambda: f.task(due_days=366), "due_days"),
        (lambda: f.task(allowed=frozenset({""})), "allowed"),
        (lambda: f.task(area_id=""), "area_id"),
        (lambda: f.task(area_id="x" * (limits.AREA_ID_MAX_LENGTH + 1)), "area_id"),
        (lambda: f.schedule(task_ids=()), "task_ids"),
        (lambda: f.schedule(task_ids=("t1", "t1")), "task_ids"),
        (lambda: f.schedule(slug=""), "slug"),
        (lambda: f.schedule(animations=()), "animations"),
        (lambda: f.schedule(animations=(AnimationKind.DRUM, AnimationKind.DRUM)), "animations"),
        (lambda: Swap(from_person_id="p1", to_person_id="p1", at=f.NOW), "to_person_id"),
        (lambda: Swap(from_person_id="p1", to_person_id="p2", at=dt.datetime(2026, 1, 1)), "at"),
        (lambda: f.assignment(chance=1.5), "chance"),
        (lambda: f.assignment(due_at=dt.datetime(2026, 1, 1)), "due_at"),
        (lambda: f.assignment(status=AssignmentStatus.ON_TIME), "done_at"),
        (lambda: f.assignment(status=AssignmentStatus.MISSED, done_at=f.NOW), "done_at"),
        (
            lambda: f.assignment(done_at=dt.datetime(2026, 1, 1), status=AssignmentStatus.LATE),
            "done_at",
        ),
        (lambda: f.finished_round(finished_at=f.NOW - dt.timedelta(seconds=1)), "finished_at"),
        (lambda: f.finished_round(started_at=dt.datetime(2026, 1, 1)), "started_at"),
        (lambda: f.finished_round(finished_at=dt.datetime(2026, 1, 2)), "finished_at"),
        (lambda: f.finished_round(assignments=(f.assignment(), f.assignment())), "assignments"),
        (lambda: f.finished_round(assignments=(f.assignment(round_id="other"),)), "assignments"),
        (lambda: Settings(jokers_per_month=-1), "jokers_per_month"),
        (lambda: Settings(fairness_window_days=0), "fairness_window_days"),
        (lambda: Settings(history_retention_days=1), "history_retention_days"),
        (lambda: Settings(late_points_factor=1.1), "late_points_factor"),
        (lambda: Settings(missed_points_factor=0.1), "missed_points_factor"),
        (lambda: Settings(missed_grace_hours=-1), "missed_grace_hours"),
    ],
)
def test_invariants_reject(build, field):
    with pytest.raises(ValidationError) as caught:
        build()
    assert caught.value.field == field
    assert isinstance(caught.value, TaskWheelError)


def test_open_round_and_unfinished_assignment_are_valid():
    assert f.finished_round(finished_at=None).finished_at is None
    assert Assignment.from_dict(f.assignment().to_dict()).status is AssignmentStatus.OPEN


def test_schedule_animations_default_to_wheel_and_roundtrip():
    legacy = {key: value for key, value in f.schedule().to_dict().items() if key != "animations"}
    assert Schedule.from_dict(legacy).animations == (AnimationKind.WHEEL,)
    chosen = f.schedule(animations=(AnimationKind.SLOT, AnimationKind.PLINKO))
    assert Schedule.from_dict(chosen.to_dict()) == chosen
    assert chosen.to_dict()["animations"] == ["slot", "plinko"]


def test_schedule_rejects_unknown_animation():
    with pytest.raises(ValidationError):
        Schedule.from_dict({**f.schedule().to_dict(), "animations": ["confetti"]})


@pytest.mark.parametrize(
    ("model", "data", "field", "key"),
    [
        (Person, {"id": "p", "name": "A", "slug": "a", "x": 1}, "x", "unknown_field"),
        (Person, {"name": "A", "slug": "a"}, "id", "required"),
        (Person, {"id": 1, "name": "A", "slug": "a"}, "id", "invalid_type"),
        (Person, {"id": "p", "name": "A", "slug": "a", "load": "huge"}, "load", "invalid_type"),
        (
            Person,
            {"id": "p", "name": "A", "slug": "a", "absences": "x"},
            "absences",
            "invalid_type",
        ),
        (
            Person,
            {"id": "p", "name": "A", "slug": "a", "absences": [{"kind": "nope"}]},
            "absences.kind",
            "unknown_kind",
        ),
        (
            Person,
            {"id": "p", "name": "A", "slug": "a", "absences": [{"kind": 3}]},
            "absences.kind",
            "unknown_kind",
        ),
        (
            Person,
            {"id": "p", "name": "A", "slug": "a", "absences": ["x"]},
            "absences",
            "invalid_type",
        ),
        (Settings, {"jokers_per_month": True}, "jokers_per_month", "invalid_type"),
        (Settings, {"jokers_per_month": 1.5}, "jokers_per_month", "invalid_type"),
        (Settings, {"late_points_factor": "1"}, "late_points_factor", "invalid_type"),
        (Schedule, {**f.schedule().to_dict(), "enabled": 1}, "enabled", "invalid_type"),
        (OnceAbsence, {"start": "gestern", "end": "2026-01-01"}, "start", "invalid_type"),
        (OnceAbsence, {"start": 5, "end": "2026-01-01"}, "start", "invalid_type"),
        (Swap, {**f.swap().to_dict(), "at": "x"}, "at", "invalid_type"),
        (Task, {**f.task().to_dict(), "frequency": 3}, "frequency", "invalid_type"),
    ],
)
def test_from_dict_rejects(model, data, field, key):
    with pytest.raises(ValidationError) as caught:
        model.from_dict(data)
    assert (caught.value.field, caught.value.key) == (field, key)


def test_unknown_kind_error_exposes_kind():
    with pytest.raises(ValidationError) as caught:
        Schedule.from_dict({**f.schedule().to_dict(), "trigger": {KEY_KIND: "daily"}})
    assert caught.value.placeholders["kind"] == "daily"
    assert str(caught.value) == "trigger.kind: unknown_kind"
    with pytest.raises(UnknownKindError):
        decode_trigger({KEY_KIND: "daily"})


def test_round_nested_error_path():
    data = f.finished_round().to_dict()
    data["assignments"][1]["chance"] = 2.0
    with pytest.raises(ValidationError) as caught:
        Round.from_dict(data)
    assert caught.value.field == "assignments.chance"


def test_task_without_allowed_persons_is_open_for_everyone():
    task = Task.from_dict({"id": "t", "name": "N"})
    assert task.allowed == frozenset()
    assert task.allows("anyone")
    assert f.task(allowed=frozenset({"p1"})).allows("p1")
    assert not f.task(allowed=frozenset({"p1"})).allows("p2")


def test_task_default_frequency_is_every_round():
    task = Task.from_dict({"id": "t", "name": "N", "allowed": ["p"]})
    assert task.frequency == EveryRound()
    assert task.points == defaults.DEFAULT_TASK_POINTS


def test_kind_must_match_class():
    with pytest.raises(UnknownKindError):
        EveryRound.from_dict({KEY_KIND: "interval"})
    assert EveryRound.from_dict({}) == EveryRound()


def test_task_area_is_optional_and_roundtrips():
    legacy = {k: v for k, v in f.task().to_dict().items() if k != "area_id"}
    assert Task.from_dict(legacy).area_id is None
    placed = f.task(area_id="kueche")
    assert Task.from_dict(placed.to_dict()).area_id == "kueche"
