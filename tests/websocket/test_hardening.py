"""Härtung (AP-18): fehlerhafte und übergroße Eingaben führen nur zu Schema- oder Fachfehlern."""

import contextlib
import dataclasses
from collections.abc import Callable
from typing import Any, Final

import pytest
import voluptuous as vol

from custom_components.task_wheel.const.limits import MAX_ABSENCES_PER_PERSON, WS_LIST_MAX_ITEMS
from custom_components.task_wheel.domain.errors import TaskWheelError
from custom_components.task_wheel.domain.models import Person, Schedule, Settings, Task

from .harness import BY_NAME, PREFIX, Api

REJECTED: Final = (vol.Invalid, TaskWheelError)
HUGE: Final = 10**30
SHAPES: Final = (
    None,
    True,
    -1,
    HUGE,
    1.5,
    float("nan"),
    "",
    "x" * 1000,
    "2026-13-45",
    "\x00",
    [],
    {},
    [[]],
    ["x"] * (WS_LIST_MAX_ITEMS + 1),
    {"a": {"b": {"c": {"d": {"e": 1}}}}},
    {"kind": "unbekannt"},
    {"kind": "every_n_weeks", "weeks": HUGE},
    {"kind": "max_per_period", "count": HUGE, "period": "day"},
)
RESOURCES: Final = (
    ("person", Person, "p1"),
    ("task", Task, "t1"),
    ("schedule", Schedule, "s1"),
    ("settings", Settings, None),
)


def _field_names(model: type) -> list[str]:
    return [item.name for item in dataclasses.fields(model) if item.name not in ("id", "slug")]


def _update(api: Api, resource: str, ident: str | None, changes: dict[str, Any]) -> None:
    if ident is None:
        api.run("settings/update", settings=changes)
    else:
        api.run(f"{resource}/update", **{f"{resource}_id": ident, resource: changes})


def _run_tolerating_rejection(call: Callable[[], object]) -> None:
    """Ein Wert darf angenommen oder sauber abgelehnt werden; jeder andere Fehler ist ein Befund."""
    with contextlib.suppress(*REJECTED):
        call()


@pytest.mark.parametrize("value", SHAPES, ids=repr)
@pytest.mark.parametrize(("resource", "model", "ident"), RESOURCES)
def test_malformed_field_values_never_crash(
    resource: str, model: type, ident: str | None, value: object
) -> None:
    for name in _field_names(model):
        _run_tolerating_rejection(lambda name=name: _update(Api(), resource, ident, {name: value}))


@pytest.mark.parametrize("value", SHAPES, ids=repr)
@pytest.mark.parametrize("name", sorted(BY_NAME))
def test_malformed_top_level_fields_never_crash(name: str, value: object) -> None:
    command = BY_NAME[name]
    required = {
        getattr(key, "schema", key): "p1" for key in command.fields if isinstance(key, vol.Required)
    }
    for key in command.fields:
        field = getattr(key, "schema", key)
        _run_tolerating_rejection(
            lambda field=field: Api().run(name.removeprefix(PREFIX), **{**required, field: value})
        )


@pytest.mark.parametrize("value", [None, 1, "x", [1], {"a": 1}, [{"kind": 1}], ["x"] * 3])
def test_non_object_values_for_objects_are_rejected(value: object) -> None:
    with pytest.raises(REJECTED):
        Api().run("person/create", person=value)


def test_unknown_fields_are_not_allowed() -> None:
    with pytest.raises(vol.Invalid):
        Api().run("snapshot", extra="x")


def test_preview_accepts_no_more_rules_than_a_person_may_have() -> None:
    rule = {"kind": "weekly_days", "weekdays": [1]}
    with pytest.raises(vol.Invalid):
        Api().run("availability/preview", absences=[rule] * (MAX_ABSENCES_PER_PERSON + 1))
    assert Api().result("availability/preview", absences=[rule] * MAX_ABSENCES_PER_PERSON)
