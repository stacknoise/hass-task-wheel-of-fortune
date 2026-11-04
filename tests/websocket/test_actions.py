"""Erledigen, Tauschen und die Panel-Ziehung."""

import pytest

from custom_components.task_wheel.domain.errors import (
    DrawRejectedError,
    InvalidTransitionError,
    NotFoundError,
    RoundHasDoneError,
    SwapRejectedError,
)

from ..domain import factories as f
from .harness import BEGIN, Api


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


def test_swap_exchanges_assignments_of_both_persons(api: Api) -> None:
    api.open_partner()
    swapped = api.result("assignment/swap", assignment_id="a1", to_person_id="p2")
    assert swapped["person_id"] == "p2"
    assert swapped["status"] == "swapped"
    assert swapped["swap"]["from_person_id"] == "p1"
    other = api.history.get_assignment("a2")
    assert (other.person_id, other.status.value) == ("p1", "swapped")  # type: ignore[union-attr]


def test_swap_without_open_counterpart_is_rejected(api: Api) -> None:
    with pytest.raises(SwapRejectedError) as caught:
        api.run("assignment/swap", assignment_id="a1", to_person_id="p2")
    assert caught.value.key == "swap_person_has_no_open_assignment"


def test_swap_to_unknown_person(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("assignment/swap", assignment_id="a1", to_person_id="nope")


def test_panel_round_runs_step_by_step(api: Api) -> None:
    api.advance(minutes=1)
    begun = api.result("draw/begin", schedule_id="s1", **BEGIN)
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
    rid = api.result("draw/begin", schedule_id="s1", **BEGIN)["id"]
    with pytest.raises(DrawRejectedError):
        api.run("draw/commit", panel_round_id=rid)
    assert [r["id"] for r in api.result("snapshot")["panel_rounds"]] == [rid]


def test_cancel_discards_round_without_effect(api: Api) -> None:
    rid = api.result("draw/begin", schedule_id="s1", **BEGIN)["id"]
    api.run("draw/cancel", panel_round_id=rid)
    with pytest.raises(NotFoundError):
        api.run("draw/spin", panel_round_id=rid)
    assert api.events.drawn == []


def test_begin_unknown_schedule(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("draw/begin", schedule_id="nope", **BEGIN)


def _undone_round(api: Api) -> None:
    api.history.put_round(
        f.finished_round(id="r2", assignments=(f.assignment(id="x1", round_id="r2"),))
    )


def test_round_delete_removes_round_and_updates_snapshot(api: Api) -> None:
    _undone_round(api)
    _, unsubscribe = api.data.live.subscribe(api.pushed.append)
    api.run("round/delete", round_id="r2")
    assert "r2" not in api.history.rounds
    assert api.history.get_assignment("x1") is None
    assert api.pushed[-1]["rounds"]["remove"] == ["r2"]
    assert len(api.events.deleted) == 1
    unsubscribe()


def test_round_delete_is_rejected_when_a_task_is_done(api: Api) -> None:
    with pytest.raises(RoundHasDoneError):
        api.run("round/delete", round_id="r1")
    assert "r1" in api.history.rounds
    assert api.events.deleted == []


def test_round_delete_unknown_round(api: Api) -> None:
    with pytest.raises(NotFoundError):
        api.run("round/delete", round_id="nope")


def test_snapshot_lists_rounds_with_open_assignments(api: Api) -> None:
    head = api.data.live.snapshot().collections["rounds"]["r1"]
    assert head["schedule_id"] == "s1"
    assert head["total"] == 3
    assert head["done"] == 1


def test_preview_shows_the_wheel_of_the_next_task_without_drawing(api: Api) -> None:
    rid = api.result("draw/begin", schedule_id="s1", **BEGIN)["id"]
    preview = api.result("draw/preview", panel_round_id=rid)["result"]
    assert preview["task_id"] == "t1"
    assert preview["winner_id"] is None
    assert {s["person_id"] for s in preview["segments"]} == {"p1", "p2"}
    # nichts wurde gezogen, und die Ziehung zeigt dasselbe Rad
    assert api.result("snapshot")["panel_rounds"][0]["results"] == []
    spun = api.result("draw/spin", panel_round_id=rid)["result"]
    assert spun["segments"] == preview["segments"]


def test_preview_of_a_finished_round_is_rejected(api: Api) -> None:
    rid = api.result("draw/begin", schedule_id="s1", **BEGIN)["id"]
    api.run("draw/spin_rest", panel_round_id=rid)
    with pytest.raises(DrawRejectedError):
        api.run("draw/preview", panel_round_id=rid)


def test_skip_marks_assignment_and_notifies(api: Api) -> None:
    skipped = api.result("assignment/skip", assignment_id="a1")
    assert skipped["status"] == "skipped"
    assert api.history.get_assignment("a1").status == "skipped"
    assert [item.id for item in api.events.skipped] == ["a1"]


def test_skip_twice_is_rejected(api: Api) -> None:
    api.run("assignment/skip", assignment_id="a1")
    with pytest.raises(InvalidTransitionError):
        api.run("assignment/skip", assignment_id="a1")


def _spare_task(api: Api) -> None:
    """Fügt dem Zeitplan eine dritte Aufgabe hinzu, die nicht in der laufenden Runde ist."""
    api.config.put_task(f.task(id="t3", allowed=frozenset({"p1", "p2"})))
    api.config.put_schedule(f.schedule(id="s1", task_ids=("t1", "t2", "t3")))


def test_replace_task_swaps_before_the_start_and_is_admin_only(api: Api) -> None:
    rid = api.result("draw/begin", schedule_id="s1", **BEGIN)["id"]
    _spare_task(api)
    options = api.result("draw/replacements", panel_round_id=rid)["replacements"]
    assert options == [{"task_id": "t3", "doable": True}]
    view = api.result("draw/replace_task", panel_round_id=rid, task_id="t1", new_task_id="t3")
    assert "t3" in view["panel_round"]["pending_task_ids"]
    assert "t1" not in view["panel_round"]["pending_task_ids"]
    api.run("draw/spin", panel_round_id=rid)
    with pytest.raises(DrawRejectedError):
        api.run("draw/replace_task", panel_round_id=rid, task_id="t2", new_task_id="t1")
