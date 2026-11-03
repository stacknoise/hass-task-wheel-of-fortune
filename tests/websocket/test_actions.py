"""Erledigen, Tauschen und die Panel-Ziehung."""

import pytest

from custom_components.task_wheel.domain.errors import (
    DrawRejectedError,
    InvalidTransitionError,
    NotFoundError,
)

from .harness import Api


@pytest.fixture
def api() -> Api:
    return Api(0.1, 0.9)


def test_complete_marks_assignment_done(api: Api) -> None:
    done = api.result("assignment/complete", assignment_id="a1")
    assert done["status"] == "on_time"
    assert api.history.get_assignment("a1").status == "on_time"
    assert len(api.events.completed) == 1


def test_complete_twice_is_rejected(api: Api) -> None:
    api.run("assignment/complete", assignment_id="a1")
    with pytest.raises(InvalidTransitionError):
        api.run("assignment/complete", assignment_id="a1")


def test_complete_unknown_assignment(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("assignment/complete", assignment_id="nope")


def test_swap_passes_assignment_to_other_person(api: Api) -> None:
    swapped = api.result("assignment/swap", assignment_id="a1", to_person_id="p2")
    assert swapped["person_id"] == "p2"
    assert swapped["status"] == "swapped"
    assert swapped["swap"]["from_person_id"] == "p1"


def test_swap_to_unknown_person(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("assignment/swap", assignment_id="a1", to_person_id="nope")


def test_panel_round_runs_step_by_step(api: Api) -> None:
    begun = api.result("draw/begin", schedule_id="s1")
    rid = begun["id"]
    assert begun["pending_task_ids"] == ["t1", "t2"]
    assert begun["results"] == []
    first = api.result("draw/spin", panel_round_id=rid)
    assert first["result"]["task_id"] == "t1"
    assert first["result"]["winner_id"] in {"p1", "p2"}
    assert {s["person_id"] for s in first["result"]["segments"]} == {"p1", "p2"}
    assert first["panel_round"]["pending_task_ids"] == ["t2"]
    rest = api.result("draw/spin_rest", panel_round_id=rid)
    assert [r["task_id"] for r in rest["results"]] == ["t2"]
    committed = api.result("draw/commit", panel_round_id=rid)
    assert committed["origin"] == "manual"
    assert len(committed["assignments"]) == 2
    assert len(api.events.drawn) == 1
    assert api.result("snapshot")["panel_rounds"] == []


def test_commit_before_all_drawn_is_rejected_and_round_stays(api: Api) -> None:
    rid = api.result("draw/begin", schedule_id="s1")["id"]
    with pytest.raises(DrawRejectedError):
        api.run("draw/commit", panel_round_id=rid)
    assert [r["id"] for r in api.result("snapshot")["panel_rounds"]] == [rid]


def test_cancel_discards_round_without_effect(api: Api) -> None:
    rid = api.result("draw/begin", schedule_id="s1")["id"]
    api.run("draw/cancel", panel_round_id=rid)
    with pytest.raises(NotFoundError):
        api.run("draw/spin", panel_round_id=rid)
    assert api.events.drawn == []


def test_begin_unknown_schedule(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("draw/begin", schedule_id="nope")
