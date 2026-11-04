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
    assert all("jokers_left" not in p for p in snap["persons"])
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


WEEKDAYS_OFF = {"kind": "weekly_days", "weekdays": [5, 6]}


def test_availability_preview_starts_on_monday_of_the_current_week(api: Api) -> None:
    # NOW ist Dienstag, 2026-11-03: die Vorschau beginnt am Montag davor
    result = api.result("availability/preview", absences=[WEEKDAYS_OFF], weeks=2)
    assert result["present"] == [True] * 5 + [False] * 2 + [True] * 5 + [False] * 2


def test_availability_preview_without_rules_is_all_present(api: Api) -> None:
    assert api.result("availability/preview", absences=[])["present"] == [True] * 28


def test_availability_preview_combines_rules(api: Api) -> None:
    once = {"kind": "once", "start": "2026-11-02", "end": "2026-11-03"}
    present = api.result("availability/preview", absences=[WEEKDAYS_OFF, once], weeks=1)["present"]
    assert present == [False, False, True, True, True, False, False]


@pytest.mark.parametrize(
    "fields",
    [
        {"absences": [{"kind": "unbekannt"}]},
        {"absences": [{"kind": "once", "start": "2026-11-05", "end": "2026-11-01"}]},
        {"absences": [], "weeks": 0},
        {"absences": [], "weeks": 13},
    ],
)
def test_availability_preview_rejects_invalid_rules(api: Api, fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        api.run("availability/preview", **fields)
