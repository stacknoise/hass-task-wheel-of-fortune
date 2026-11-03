"""Lasttest an den Obergrenzen (AP-18): Laufzeit der wichtigsten Abläufe mit vollem Bestand.

Die Grenzen sind absichtlich großzügig (etwa das Fünf- bis Zehnfache der Messwerte in
`docs/CODE_DOKU.md` §3.2), damit langsame CI-Rechner nicht scheitern; sie fangen quadratisches
Verhalten und versehentliche Durchläufe über den ganzen Verlauf ab.
"""

import datetime as dt
import time
from collections.abc import Callable
from functools import partial
from typing import Final

import pytest

from custom_components.task_wheel.const import limits
from custom_components.task_wheel.domain.enums import AssignmentStatus, RoundOrigin
from custom_components.task_wheel.domain.models import EveryRound, ManualTrigger

from ..domain import factories as f
from ..websocket.harness import Api

HISTORY_ROUNDS: Final = 2000
ASSIGNMENTS_PER_ROUND: Final = 10
HISTORY_DAYS: Final = 90
BUDGET_DRAW_SECONDS: Final = 1.0
BUDGET_SNAPSHOT_SECONDS: Final = 0.1
BUDGET_STATISTICS_SECONDS: Final = 0.25
BUDGET_HISTORY_PAGE_SECONDS: Final = 0.25
BUDGET_PREVIEW_SECONDS: Final = 0.05
BUDGET_PUBLISH_SECONDS: Final = 0.1
ABSENCE_RULE: Final = {"kind": "weekly_days", "weekdays": [1]}


def _seconds(call: Callable[[], object]) -> float:
    """Beste von drei Messungen (unempfindlich gegen einzelne Ausreißer)."""
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        call()
        best = min(best, time.perf_counter() - start)
    return best


def _full_world() -> Api:
    """Höchstzahl an Personen, Aufgaben und Zeitplänen; Verlauf über 90 Tage."""
    api = Api()
    everyone = frozenset(f"p{i}" for i in range(limits.MAX_PERSONS))
    task_ids = tuple(f"t{i}" for i in range(limits.MAX_TASKS))
    for i in range(limits.MAX_PERSONS):
        api.config.put_person(f.person(id=f"p{i}", slug=f"p{i}", name=f"P{i}"))
    for ident in task_ids:
        api.config.put_task(
            f.task(id=ident, name=ident, allowed=everyone, frequency=EveryRound(), points=3)
        )
    for i in range(limits.MAX_SCHEDULES):
        api.config.put_schedule(
            f.schedule(
                id=f"s{i}", slug=f"s{i}", name=f"S{i}", trigger=ManualTrigger(), task_ids=task_ids
            )
        )
    for number in range(HISTORY_ROUNDS):
        at = api.now - dt.timedelta(days=number % HISTORY_DAYS, minutes=number)
        round_id = f"h{number}"
        assignments = tuple(
            f.assignment(
                id=f"{round_id}a{k}",
                round_id=round_id,
                task_id=f"t{(number + k) % limits.MAX_TASKS}",
                person_id=f"p{(number + k) % limits.MAX_PERSONS}",
                status=AssignmentStatus.ON_TIME,
                done_at=at,
                due_at=at + dt.timedelta(days=7),
            )
            for k in range(ASSIGNMENTS_PER_ROUND)
        )
        round_ = f.finished_round(
            id=round_id,
            schedule_id=f"s{number % limits.MAX_SCHEDULES}",
            started_at=at,
            finished_at=at,
            assignments=assignments,
        )
        api.history.put_round(round_)
        api.data.statistics.record_round(round_)
    return api


@pytest.fixture(scope="module")
def world() -> Api:
    return _full_world()


def test_draw_with_all_tasks_and_people(world: Api) -> None:
    draw = partial(world.data.draws.draw, "s0", RoundOrigin.MANUAL, world.now)
    assert _seconds(draw) < BUDGET_DRAW_SECONDS


def test_snapshot_does_not_scale_with_people_times_history(world: Api) -> None:
    assert _seconds(world.data.live.snapshot) < BUDGET_SNAPSHOT_SECONDS


def test_publish_to_all_subscribers(world: Api) -> None:
    for _ in range(limits.MAX_SUBSCRIPTIONS):
        world.data.live.subscribe(lambda _payload: None)
    assert _seconds(world.data.live.publish) < BUDGET_PUBLISH_SECONDS


def test_statistics_for_a_year(world: Api) -> None:
    report = partial(
        world.data.statistics.report,
        world.now,
        limits.STATISTICS_MONTHS_MAX,
        limits.STATISTICS_WEEKS_MAX,
    )
    assert _seconds(report) < BUDGET_STATISTICS_SECONDS


def test_largest_history_page(world: Api) -> None:
    page = partial(world.result, "history/list", limit=limits.HISTORY_PAGE_SIZE_MAX)
    assert _seconds(page) < BUDGET_HISTORY_PAGE_SECONDS


def test_availability_preview_with_most_rules_and_weeks(world: Api) -> None:
    rules = [ABSENCE_RULE] * limits.MAX_ABSENCES_PER_PERSON
    preview = partial(
        world.result, "availability/preview", absences=rules, weeks=limits.PREVIEW_WEEKS_MAX
    )
    assert _seconds(preview) < BUDGET_PREVIEW_SECONDS
