"""Schema-Tests: zu lange oder zusätzliche Felder werden abgewiesen (KONZEPT §8)."""

import pytest
import voluptuous as vol

from custom_components.task_wheel.const.limits import (
    WS_LIST_MAX_ITEMS,
    WS_MAX_DEPTH,
    WS_OBJECT_MAX_KEYS,
    WS_STRING_MAX_LENGTH,
)
from custom_components.task_wheel.websocket.registry import COMMANDS

from .harness import Api

LONG = "x" * (WS_STRING_MAX_LENGTH + 1)


@pytest.fixture
def api() -> Api:
    return Api()


@pytest.mark.parametrize(
    ("name", "fields"),
    [
        ("snapshot", {"extra": 1}),
        ("history/list", {"limit": "5"}),
        ("history/list", {"limit": True}),
        ("history/list", {"person_id": LONG}),
        ("history/list", {"since": LONG}),
        ("statistics/get", {"months": 1.5}),
        ("assignment/complete", {}),
        ("assignment/complete", {"assignment_id": 5}),
        ("assignment/complete", {"assignment_id": ""}),
        ("assignment/swap", {"assignment_id": "a1"}),
        ("assignment/skip", {}),
        ("draw/begin", {"schedule_id": "s1", "extra": "x"}),
        ("round/delete", {}),
        ("round/delete", {"round_id": ""}),
        ("person/create", {}),
        ("person/create", {"person": {"name": "Neu", "extra": 1}}),
        ("person/create", {"person": {"name": LONG}}),
        ("person/create", {"person": {"name": "Neu", "id": "p9"}}),
        ("person/create", {"person": {"name": "Neu"}, "extra": 1}),
        ("person/create", {"person": {"name": ["a"] * (WS_LIST_MAX_ITEMS + 1)}}),
        (
            "person/create",
            {"person": {"name": {f"k{i}": 1 for i in range(WS_OBJECT_MAX_KEYS + 1)}}},
        ),
        ("person/create", {"person": {"name": object()}}),
        ("person/update", {"person": {"name": "Neu"}}),
        ("task/create", {"task": {"allowed": ["p1"]}}),
        ("schedule/create", {"schedule": {"name": "Neu", "task_ids": ["t1"]}}),
        ("schedule/delete", {"schedule_id": "s1", "extra": 1}),
        ("settings/update", {"settings": {"unknown": 1}}),
        ("settings/update", {}),
    ],
)
def test_rejects_invalid_messages(api: Api, name: str, fields: dict) -> None:
    with pytest.raises(vol.Invalid):
        api.run(name, **fields)


def test_rejects_too_deep_nesting(api: Api) -> None:
    nested: object = 1
    for _ in range(WS_MAX_DEPTH + 1):
        nested = {"a": nested}
    with pytest.raises(vol.Invalid):
        api.run("person/create", person={"name": "Neu", "absences": nested})


def test_rejects_missing_or_bad_message_id(api: Api) -> None:
    schema = COMMANDS[0].schema()
    with pytest.raises(vol.Invalid):
        schema({"type": COMMANDS[0].name})
    with pytest.raises(vol.Invalid):
        schema({"id": 0, "type": COMMANDS[0].name})
    with pytest.raises(vol.Invalid):
        schema({"id": True, "type": COMMANDS[0].name})


def test_update_allows_partial_object(api: Api) -> None:
    api.run("person/update", person_id="p1", person={})
