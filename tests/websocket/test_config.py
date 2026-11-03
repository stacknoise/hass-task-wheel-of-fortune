"""Konfigurationsbefehle: Anlegen, Ändern, Löschen, Verweise und Zeitgeber."""

import pytest
import voluptuous as vol

from custom_components.task_wheel.domain.errors import (
    InUseError,
    LimitReachedError,
    NotFoundError,
    ValidationError,
)

from .harness import Api

RECURRING = {"kind": "recurring", "weekdays": [0, 3], "time": "18:30:00"}


@pytest.fixture
def api() -> Api:
    return Api()


def test_create_person_derives_slug_and_id(api: Api) -> None:
    created = api.result("person/create", person={"name": "Jörg Müller"})
    assert created["slug"] == "jorg_muller"
    assert created["id"] in api.config.persons
    assert created["load"] == "full"


def test_create_person_makes_slug_unique(api: Api) -> None:
    first = api.result("person/create", person={"name": "Anna"})
    second = api.result("person/create", person={"name": "anna"})
    assert (first["slug"], second["slug"]) == ("anna", "anna_2")


def test_create_person_rejects_duplicate_explicit_slug(api: Api) -> None:
    with pytest.raises(ValidationError):
        api.run("person/create", person={"name": "Neu", "slug": "p1"})


def test_create_person_validates_values(api: Api) -> None:
    for bad in ({"name": "Neu", "color": "rot"}, {"name": ""}, {"name": 5}, {"name": " x"}):
        with pytest.raises(ValidationError):
            api.run("person/create", person=bad)


def test_create_person_stops_at_limit(api: Api) -> None:
    for number in range(28):
        api.run("person/create", person={"name": f"P{number}"})
    with pytest.raises(LimitReachedError):
        api.run("person/create", person={"name": "zu viel"})


def test_update_person_changes_only_given_fields(api: Api) -> None:
    updated = api.result("person/update", person_id="p1", person={"color": "#112233"})
    assert updated["color"] == "#112233"
    assert updated["name"] == "p1"
    assert api.config.persons["p1"].color == "#112233"


def test_update_person_keeps_own_slug_but_not_foreign(api: Api) -> None:
    api.run("person/update", person_id="p1", person={"slug": "p1"})
    with pytest.raises(ValidationError):
        api.run("person/update", person_id="p1", person={"slug": "p2"})


def test_update_unknown_person(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("person/update", person_id="nope", person={})


def test_update_cannot_change_id(api: Api) -> None:
    with pytest.raises(vol.Invalid):
        api.run("person/update", person_id="p1", person={"id": "p9"})


def test_delete_person_strips_them_from_tasks(api: Api) -> None:
    api.run("person/delete", person_id="p2")
    assert "p2" not in api.config.persons
    assert api.config.tasks["t1"].allowed == {"p1"}


def test_delete_person_rejected_when_sole_allowed(api: Api) -> None:
    api.run("task/update", task_id="t1", task={"allowed": ["p1"]})
    with pytest.raises(InUseError):
        api.run("person/delete", person_id="p1")
    assert "p1" in api.config.persons


def test_create_task_checks_allowed_persons(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("task/create", task={"name": "Neu", "allowed": ["nope"]})
    created = api.result("task/create", task={"name": "Neu", "allowed": ["p1"], "points": 4})
    assert api.config.tasks[created["id"]].points == 4


def test_create_task_with_frequency_rule(api: Api) -> None:
    created = api.result(
        "task/create",
        task={
            "name": "Selten",
            "allowed": ["p1"],
            "frequency": {"kind": "interval", "days": 14, "tolerance": 2},
        },
    )
    assert created["frequency"]["kind"] == "interval"
    with pytest.raises(ValidationError):
        api.run(
            "task/create", task={"name": "Falsch", "allowed": ["p1"], "frequency": {"kind": "x"}}
        )


def test_update_task(api: Api) -> None:
    updated = api.result("task/update", task_id="t1", task={"points": 9, "no_repeat": True})
    assert (updated["points"], updated["no_repeat"]) == (9, True)
    with pytest.raises(ValidationError):
        api.run("task/update", task_id="t1", task={"points": 1000})


def test_delete_task_strips_it_from_schedules_and_rearms(api: Api) -> None:
    api.run("task/delete", task_id="t2")
    assert api.config.schedules["s1"].task_ids == ("t1",)


def test_delete_task_rejected_when_schedule_would_be_empty(api: Api) -> None:
    api.run("task/delete", task_id="t2")
    with pytest.raises(InUseError):
        api.run("task/delete", task_id="t1")
    assert "t1" in api.config.tasks


def test_create_schedule_arms_timer(api: Api) -> None:
    created = api.result(
        "schedule/create",
        schedule={"name": "Wochenplan", "trigger": RECURRING, "task_ids": ["t1"]},
    )
    assert created["slug"] == "wochenplan"
    assert f"schedule:{created['id']}" in api.timers.timers


def test_create_schedule_checks_tasks(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run(
            "schedule/create",
            schedule={"name": "Neu", "trigger": RECURRING, "task_ids": ["nope"]},
        )


def test_update_schedule_pause_cancels_timer(api: Api) -> None:
    created = api.result(
        "schedule/create", schedule={"name": "Plan", "trigger": RECURRING, "task_ids": ["t1"]}
    )
    key = f"schedule:{created['id']}"
    assert key in api.timers.timers
    api.run("schedule/update", schedule_id=created["id"], schedule={"enabled": False})
    assert key not in api.timers.timers


def test_update_schedule_trigger_rearms(api: Api) -> None:
    created = api.result(
        "schedule/create", schedule={"name": "Plan", "trigger": RECURRING, "task_ids": ["t1"]}
    )
    key = f"schedule:{created['id']}"
    before = api.timers.timers[key][0]
    later = {**RECURRING, "weekdays": [6], "time": "07:00:00"}
    api.run("schedule/update", schedule_id=created["id"], schedule={"trigger": later})
    assert api.timers.timers[key][0] != before


def test_delete_schedule_cancels_timer_and_panel_round(api: Api) -> None:
    created = api.result(
        "schedule/create", schedule={"name": "Plan", "trigger": RECURRING, "task_ids": ["t1"]}
    )
    sid = created["id"]
    rid = api.result("draw/begin", schedule_id=sid)["id"]
    api.run("schedule/delete", schedule_id=sid)
    assert f"schedule:{sid}" not in api.timers.timers
    assert sid not in api.config.schedules
    with pytest.raises(NotFoundError):
        api.run("draw/spin", panel_round_id=rid)


def test_delete_unknown_schedule(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("schedule/delete", schedule_id="nope")


def test_update_settings(api: Api) -> None:
    updated = api.result("settings/update", settings={"jokers_per_month": 5})
    assert updated["jokers_per_month"] == 5
    assert api.config.settings.jokers_per_month == 5
    with pytest.raises(ValidationError):
        api.run("settings/update", settings={"jokers_per_month": 999})
    with pytest.raises(ValidationError):
        api.run("settings/update", settings={"weighting": "magic"})
