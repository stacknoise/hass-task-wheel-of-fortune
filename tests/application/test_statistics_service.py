"""StatisticsService und HistoryService gegen In-Memory-Speicher; Eigenschaftstest der Aggregate."""

import datetime as dt
import random

import pytest

from custom_components.task_wheel.application.assignment_service import AssignmentService
from custom_components.task_wheel.application.history_service import HistoryService
from custom_components.task_wheel.application.statistics_service import StatisticsService
from custom_components.task_wheel.application.swap_service import SwapService
from custom_components.task_wheel.application.wire import to_json
from custom_components.task_wheel.domain.enums import AssignmentStatus as S
from custom_components.task_wheel.domain.enums import Load, Period
from custom_components.task_wheel.domain.errors import TaskWheelError, ValidationError
from custom_components.task_wheel.domain.history import HistoryFilter
from custom_components.task_wheel.domain.models import MaxPerPeriod
from custom_components.task_wheel.domain.statistics.aggregate import recompute
from custom_components.task_wheel.infrastructure.repository.config_store import ConfigStore
from custom_components.task_wheel.infrastructure.repository.history_store import HistoryStore
from custom_components.task_wheel.infrastructure.repository.memory import MemoryStore

from ..domain import factories as f

DAY = dt.timedelta(days=1)
PEOPLE = ("p1", "p2", "p3")
TASKS = ("t1", "t2", "t3")


class World:
    """Drei Personen, drei Aufgaben, alle Dienste auf denselben Repositories."""

    def __init__(self, **settings: object) -> None:
        self.history_data = MemoryStore()
        self.config = ConfigStore(MemoryStore())
        self.history = HistoryStore(self.history_data)
        for ident in PEOPLE:
            self.config.put_person(
                f.person(id=ident, slug=ident, name=ident, absences=(), load=Load.FULL)
            )
        for ident in TASKS:
            self.config.put_task(f.task(id=ident, allowed=frozenset(PEOPLE)))
        self.config.set_settings(f.settings(**settings))
        self.statistics = StatisticsService(self.config, self.history)
        self.assignments = AssignmentService(self.config, self.history, self.statistics)
        self.swaps = SwapService(self.config, self.history, self.statistics)

    def add_round(self, ident: str, started: dt.datetime, *assignments: object) -> None:
        round_ = f.finished_round(
            id=ident, started_at=started, finished_at=started, assignments=assignments
        )  # type: ignore[arg-type]
        self.history.put_round(round_)
        self.statistics.record_round(round_)


def _assignment(round_id: str, ident: str, **overrides: object):
    return f.assignment(
        **{"id": ident, "round_id": round_id, "due_at": f.NOW + 7 * DAY, **overrides}
    )


def test_record_follows_complete_swap_and_miss() -> None:
    world = World()
    world.add_round(
        "r1",
        f.NOW,
        _assignment("r1", "a1"),
        _assignment("r1", "a2", person_id="p2"),
        _assignment("r1", "a3", person_id="p3"),
    )
    world.swaps.swap("a1", "p3", f.NOW)
    world.assignments.complete("a1", f.NOW + DAY)
    world.assignments.mark_missed(f.NOW + 30 * DAY)
    assert world.history.aggregates["2026-11"] == {
        "p3": {"t1": {"on_time": [1, 3], "missed": [1, 3]}},
        "p2": {"t1": {"missed": [1, 3]}},
    }


def test_rounds_are_attributed_to_the_month_of_their_start() -> None:
    world = World()
    october = f.NOW - 20 * DAY
    world.add_round("r1", october, _assignment("r1", "a1"))
    world.add_round("r2", f.NOW, _assignment("r2", "a2"))
    assert sorted(world.history.aggregates) == ["2026-10", "2026-11"]
    world.assignments.complete("a1", f.NOW + 10 * DAY)  # verspätet, bleibt im Oktober
    assert world.history.aggregates["2026-10"] == {"p1": {"t1": {"late": [1, 3]}}}


def test_report_combines_months_weeks_and_fair_share() -> None:
    world = World()
    world.add_round("r1", f.NOW - 20 * DAY, _assignment("r1", "a1"))
    world.add_round("r2", f.NOW, _assignment("r2", "a2"), _assignment("r2", "a3", person_id="p2"))
    world.assignments.complete("a2", f.NOW)
    one = world.statistics.report(f.NOW, months=1, weeks=2)
    two = world.statistics.report(f.NOW, months=2, weeks=2)
    assert one.months == ("2026-11",)
    assert (one.kpis.assigned, one.kpis.on_time, one.kpis.pending) == (2, 1, 1)
    assert two.months == ("2026-10", "2026-11")
    assert two.kpis.assigned == 3
    assert [w.week_start for w in one.weeks] == [dt.date(2026, 10, 26), dt.date(2026, 11, 2)]
    assert (one.weeks[1].done, one.weeks[1].rate) == (1, 1.0)
    shares = {s.person_id: s.fair_points for s in one.standings}
    assert shares == {"p1": pytest.approx(1.0), "p2": pytest.approx(1.0), "p3": pytest.approx(1.0)}
    assert one.matrix == {"t1": {"p1": 1, "p2": 1}}


def test_report_ignores_absent_days_and_load_in_fair_share() -> None:
    world = World()
    world.config.put_person(f.person(id="p2", slug="p2", name="p2", absences=(), load=Load.HALF))
    world.add_round("r1", f.NOW, _assignment("r1", "a1"))
    world.assignments.complete("a1", f.NOW)
    standing = {s.person_id: s for s in world.statistics.report(f.NOW).standings}
    assert standing["p1"].points == 3
    assert standing["p1"].fair_points == pytest.approx(3 * 2 / 5)
    assert standing["p2"].fair_points == pytest.approx(3 * 1 / 5)


def test_report_validates_ranges() -> None:
    world = World()
    for kwargs in ({"months": 0}, {"months": 13}, {"weeks": 0}, {"weeks": 53}):
        with pytest.raises(ValidationError):
            world.statistics.report(f.NOW, **kwargs)


def test_report_for_twelve_months_fits_availability_window() -> None:
    world = World()
    end_of_leap_year = dt.datetime(2028, 12, 31, 12, tzinfo=dt.UTC)
    assert len(world.statistics.report(end_of_leap_year, months=12).months) == 12


def test_rebuild_repairs_wrong_aggregates() -> None:
    world = World()
    world.add_round("r1", f.NOW, _assignment("r1", "a1"))
    world.history.set_aggregates({"2026-11": {"p9": {"t1": {"open": [5, 5]}}}})
    world.statistics.rebuild()
    assert dict(world.history.aggregates) == recompute(world.history.rounds.values())


async def test_aggregates_survive_save_and_load() -> None:
    world = World()
    world.add_round("r1", f.NOW, _assignment("r1", "a1"))
    world.assignments.complete("a1", f.NOW)
    world.history_data.flush_pending()
    reloaded = HistoryStore(world.history_data)
    await reloaded.async_load()
    assert dict(reloaded.aggregates) == dict(world.history.aggregates)


# --- Eigenschaftstest ---------------------------------------------------------------------------


def _random_step(world: World, rng: random.Random, counter: list[int]) -> None:
    """Ein zufälliger Schritt: neue Runde, Erledigen, Tauschen oder täglicher Verpasst-Lauf."""
    now = f.NOW + rng.randint(0, 90) * DAY
    open_ids = [a.id for p in PEOPLE for a in world.history.open_assignments(p)]
    action = rng.choice(("round", "complete", "swap", "miss"))
    try:
        if action == "round" or not open_ids:
            counter[0] += 1
            round_id = f"r{counter[0]}"
            items = tuple(
                _assignment(
                    round_id,
                    f"{round_id}a{index}",
                    person_id=rng.choice(PEOPLE),
                    task_id=rng.choice(TASKS),
                    points=rng.randint(1, 9),
                    due_at=now + rng.randint(1, 20) * DAY,
                )
                for index in range(rng.randint(0, 4))
            )
            world.add_round(round_id, now, *items)
        elif action == "complete":
            world.assignments.complete(rng.choice(open_ids), now)
        elif action == "swap":
            world.swaps.swap(rng.choice(open_ids), rng.choice(PEOPLE), now)
        else:
            world.assignments.mark_missed(now)
    except TaskWheelError:
        pass  # abgelehnter Tausch o. Ä.: ändert nichts und darf die Aggregate nicht verändern


@pytest.mark.parametrize("seed", range(20))
def test_aggregates_equal_recomputation_from_raw_data(seed: int) -> None:
    rng = random.Random(seed)  # noqa: S311 - fester Startwert, kein Sicherheitsbezug
    world = World(late_points_factor=0.5, missed_points_factor=-0.5)
    counter = [0]
    for _ in range(60):
        _random_step(world, rng, counter)
        assert dict(world.history.aggregates) == recompute(world.history.rounds.values())


# --- Historie -----------------------------------------------------------------------------------


def _history_world(rounds: int = 5) -> World:
    world = World()
    for index in range(rounds):
        started = f.NOW + index * DAY
        world.add_round(
            f"r{index}",
            started,
            _assignment(f"r{index}", f"x{index}", task_id="t1", person_id="p1"),
            _assignment(f"r{index}", f"y{index}", task_id="t2", person_id="p2"),
        )
    return world


def test_history_lists_newest_first_in_pages() -> None:
    service = HistoryService(_history_world().history)
    first = service.page(limit=2)
    assert [e.round.id for e in first.entries] == ["r4", "r3"]
    assert first.next_offset == 2
    last = service.page(offset=4, limit=2)
    assert [e.round.id for e in last.entries] == ["r0"]
    assert last.next_offset is None
    assert service.page(offset=0, limit=5).next_offset is None


def test_history_filters_assignments_and_period() -> None:
    service = HistoryService(_history_world().history)
    page = service.page(HistoryFilter(task_id="t2", since=f.NOW + 2 * DAY, until=f.NOW + 4 * DAY))
    assert [e.round.id for e in page.entries] == ["r3", "r2"]
    assert [[a.id for a in e.assignments] for e in page.entries] == [["y3"], ["y2"]]
    assert service.page(HistoryFilter(status=S.LATE)).entries == ()


@pytest.mark.parametrize(
    "kwargs", [{"limit": 0}, {"limit": 201}, {"offset": -1}, {"offset": 20001}]
)
def test_history_validates_paging(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        HistoryService(_history_world().history).page(**kwargs)


def test_report_holds_target_against_drawn_per_task():
    world = World()
    rule = MaxPerPeriod(count=2, period=Period.WEEK)
    world.config.put_task(f.task(id="t1", allowed=frozenset(PEOPLE), frequency=rule))
    report = world.statistics.report(f.NOW)
    (goal,) = (g for g in report.goals if g.task_id == "t1")
    assert (goal.target, goal.windows[0].assigned) == (2, 0)
    wire = to_json(report)["goals"]
    assert wire[0]["windows"][0]["start"] == "2026-11-02"
