"""Lesebefehle: Snapshot, Historie, Statistik."""

import datetime as dt

import pytest

from custom_components.task_wheel.domain.errors import ValidationError

from ..domain import factories as f
from .harness import Api

DAY = dt.timedelta(days=1)


@pytest.fixture
def api() -> Api:
    return Api()


def test_snapshot_lists_everything_the_panel_shows(api: Api) -> None:
    snap = api.result("snapshot")
    assert [p["id"] for p in snap["persons"]] == ["p1", "p2"]
    # p1 hat in Runde r1 schon einen Joker verbraucht (a2 wurde an p2 getauscht)
    assert [p["jokers_left"] for p in snap["persons"]] == [1, 2]
    assert [t["id"] for t in snap["tasks"]] == ["t1", "t2"]
    assert snap["schedules"][0]["next_run"] is None
    assert {a["id"] for a in snap["assignments"]} == {"a1", "a2"}
    assert snap["panel_rounds"] == []
    assert snap["settings"]["jokers_per_month"] == 2
    assert snap["now"] == f.NOW.isoformat()


def test_snapshot_has_no_free_text_markup(api: Api) -> None:
    names = {p["name"] for p in api.result("snapshot")["persons"]}
    assert names == {"p1", "p2"}


def test_history_list_filters_and_pages(api: Api) -> None:
    older = f.finished_round(
        id="r0",
        started_at=f.NOW - 2 * DAY,
        assignments=(f.assignment(id="o1", round_id="r0"),),
    )
    api.history.put_round(older)
    page = api.result("history/list", limit=1)
    assert page["next_offset"] == 1
    assert [e["id"] for e in page["entries"]] == ["r1"]
    rest = api.result("history/list", limit=1, offset=1)
    assert [e["id"] for e in rest["entries"]] == ["r0"]
    assert rest["next_offset"] is None
    late = api.result("history/list", status="late")
    assert [a["id"] for a in late["entries"][0]["assignments"]] == ["a3"]
    other = api.result("history/list", schedule_id="nope")
    assert other["entries"] == []


def test_history_list_entry_has_round_fields(api: Api) -> None:
    entry = api.result("history/list")["entries"][0]
    assert entry["id"] == "r1"
    assert entry["origin"] == "manual"
    assert len(entry["assignments"]) == 3


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "bogus"},
        {"since": "gestern"},
        {"since": "2026-11-03T10:00:00"},
        {"since": "2026-11-03T10:00:00+00:00", "until": "2026-11-02T10:00:00+00:00"},
        {"limit": 0},
        {"offset": -1},
    ],
)
def test_history_list_rejects_invalid_filters(api: Api, fields: dict) -> None:
    with pytest.raises(ValidationError):
        api.run("history/list", **fields)


def test_statistics_get_returns_report(api: Api) -> None:
    report = api.result("statistics/get", months=1, weeks=2)
    assert set(report) >= {"kpis", "standings", "fairness_index", "matrix", "weeks", "highlights"}
    assert len(report["weeks"]) == 2
    assert all("rate" in week for week in report["weeks"])
    assert all("difference" in standing for standing in report["standings"])


def test_statistics_get_rejects_out_of_range(api: Api) -> None:
    with pytest.raises(ValidationError):
        api.run("statistics/get", months=13)
