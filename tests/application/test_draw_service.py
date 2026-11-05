"""DrawService: automatische und schrittweise Runden gegen In-Memory-Speicher."""

import datetime as dt

import pytest

from custom_components.task_wheel.const.limits import (
    DRAW_MIN_INTERVAL,
    DRAW_MIN_INTERVAL_SECONDS,
    MAX_OPEN_PANEL_ROUNDS,
)
from custom_components.task_wheel.domain.deadline import Deadline, DeadlineWindow
from custom_components.task_wheel.domain.enums import (
    AssignmentStatus,
    DeadlineStart,
    DeadlineUnit,
    Load,
    Period,
    RoundOrigin,
    WeightingKind,
)
from custom_components.task_wheel.domain.errors import (
    DrawRejectedError,
    LimitReachedError,
    NotFoundError,
)
from custom_components.task_wheel.domain.models import (
    MaxPerPeriod,
    OnceAbsence,
    Recurring,
    WeeklyDaysAbsence,
)
from custom_components.task_wheel.domain.statistics import aggregate

from ..domain import factories as f
from .world import DAY, World

NOW = f.NOW
AUTO, MANUAL = RoundOrigin.AUTO, RoundOrigin.MANUAL
SECOND = dt.timedelta(seconds=1)
HOUR = DeadlineUnit.HOUR
HOUR_DELTA = dt.timedelta(hours=1)
WINDOW = DeadlineWindow(NOW, NOW + 3 * DAY)


def begin(world: World, schedule_id: str, now: dt.datetime = NOW, **kwargs):
    """Panel-Runde mit Frist und bestätigtem Vorziehen des nächsten Laufs."""
    return world.draws.begin(schedule_id, now, WINDOW, replace_next=True, **kwargs)


def test_automatic_round_is_drawn_stored_and_reported():
    world = World(0.1, 0.9)
    round_ = world.draws.draw("s1", AUTO, NOW)
    assert world.history.rounds[round_.id] == round_
    assert world.events.drawn == [round_]
    assert (round_.origin, round_.started_at, round_.finished_at) == (AUTO, NOW, NOW)
    assert [(a.task_id, a.person_id, a.status) for a in round_.assignments] == [
        ("t1", "p1", AssignmentStatus.OPEN),
        ("t2", "p2", AssignmentStatus.OPEN),
    ]
    assert round_.assignments[0].due_at == NOW + 7 * DAY


def test_new_round_is_added_to_the_monthly_aggregates():
    world = World(0.1, 0.9)
    round_ = world.draws.draw("s1", AUTO, NOW)
    recomputed = aggregate.recompute([round_])
    assert world.history.aggregates == recomputed and recomputed


def test_unknown_schedule_is_not_found():
    with pytest.raises(NotFoundError):
        World().draws.draw("fehlt", AUTO, NOW)


def test_archived_schedule_cannot_be_drawn_at_all():
    world = World()
    world.put_schedule(enabled=False, archived=True)
    for origin in (AUTO, MANUAL):
        with pytest.raises(DrawRejectedError):
            world.draws.draw("s1", origin, NOW)


def test_paused_schedule_is_skipped_automatically_but_can_be_drawn_by_hand():
    world = World()
    world.put_schedule(enabled=False)
    with pytest.raises(DrawRejectedError):
        world.draws.draw("s1", AUTO, NOW)
    assert world.draws.draw("s1", RoundOrigin.SERVICE, NOW).origin is RoundOrigin.SERVICE


def test_frequency_rule_removes_tasks_that_are_not_due():
    world = World(0.1)
    world.config.put_task(
        f.task(
            id="t1",
            allowed=frozenset({"p1", "p2"}),
            points=5,
            frequency=MaxPerPeriod(count=1, period=Period.DAY),
        )
    )
    world.draws.draw("s1", AUTO, NOW)
    second = world.draws.draw("s1", AUTO, NOW + dt.timedelta(hours=1))
    assert [a.task_id for a in second.assignments] == ["t2"]
    third = world.draws.draw("s1", AUTO, NOW + DAY)
    assert [a.task_id for a in third.assignments] == ["t1", "t2"]


def _exhaust_all_tasks(world: World) -> None:
    """Beide Aufgaben am Tagesmaximum: nach einer Auslosung ist heute nichts mehr fällig."""
    daily = MaxPerPeriod(count=1, period=Period.DAY)
    for task_id in ("t1", "t2"):
        world.config.put_task(f.task(id=task_id, allowed=frozenset({"p1", "p2"}), frequency=daily))
    world.draws.draw("s1", AUTO, NOW)


def test_nothing_due_rejects_the_draw_and_stores_no_empty_round():
    world = World(0.1, 0.9)
    _exhaust_all_tasks(world)
    stored = dict(world.history.rounds)
    for origin in (AUTO, MANUAL):
        with pytest.raises(DrawRejectedError, match="draw_nothing_due"):
            world.draws.draw("s1", origin, NOW + HOUR_DELTA)
    with pytest.raises(DrawRejectedError, match="draw_nothing_due"):
        begin(world, "s1", NOW + HOUR_DELTA)
    assert world.history.rounds == stored and len(world.events.drawn) == 1
    assert world.draws.open_rounds(NOW + HOUR_DELTA) == ()


def test_nothing_due_keeps_an_open_panel_round_and_ends_with_the_next_day():
    world = World(0.1, 0.9)
    _exhaust_all_tasks(world)
    with pytest.raises(DrawRejectedError, match="draw_nothing_due"):
        begin(world, "s1", NOW + HOUR_DELTA)
    assert len(world.draws.draw("s1", AUTO, NOW + DAY).assignments) == 2


def test_nobody_available_counts_as_nothing_due():
    world = World()
    for pid in ("p1", "p2"):
        world.config.put_person(f.person(id=pid, load=Load.PAUSED))
    with pytest.raises(DrawRejectedError, match="draw_nothing_due"):
        world.draws.draw("s1", AUTO, NOW)


def test_deleted_tasks_are_skipped():
    world = World()
    world.config.remove_task("t2")
    assert [a.task_id for a in world.draws.draw("s1", AUTO, NOW).assignments] == ["t1"]


def test_open_assignments_count_as_load_for_the_next_round():
    world = World(0.1)
    world.config.set_settings(f.settings(weighting=WeightingKind.FAIRNESS))
    world.config.remove_task("t2")
    first = world.draws.draw("s1", AUTO, NOW)
    assert {a.person_id for a in first.assignments} == {"p1"}
    second = world.draws.draw("s1", AUTO, NOW + DAY)
    # p1 trägt bereits offene Punkte: sein Segment im Rad ist deutlich kleiner als das von p2
    assert second.assignments[0].person_id == "p1"
    assert second.assignments[0].chance < 0.2


def test_absence_is_ignored_when_the_schedule_does_not_skip_absent():
    always = WeeklyDaysAbsence(weekdays=frozenset(range(7)))
    world = World(0.1)
    for ident in ("p1", "p2"):
        world.config.put_person(f.person(id=ident, slug=ident, name=ident, absences=(always,)))
    with pytest.raises(DrawRejectedError, match="draw_nothing_due"):
        world.draws.draw("s1", AUTO, NOW)
    world.put_schedule(skip_absent=False)
    assert len(world.draws.draw("s1", AUTO, NOW + DAY).assignments) == 2


def test_panel_round_runs_step_by_step_and_is_stored_on_commit():
    world = World(0.1, 0.9)
    panel = begin(world, "s1", NOW)
    assert world.history.rounds == {}
    first = world.draws.spin(panel.id, NOW)
    assert (first.task_id, first.winner_id) == ("t1", "p1")
    rest = world.draws.spin_rest(panel.id, NOW)
    assert [(r.task_id, r.winner_id) for r in rest] == [("t2", "p2")]
    round_ = world.draws.commit(panel.id, NOW + dt.timedelta(minutes=1))
    assert round_.origin is MANUAL and round_.finished_at == NOW + dt.timedelta(minutes=1)
    assert world.history.rounds[round_.id] == round_ and world.events.drawn == [round_]
    assert world.draws.open_rounds(NOW) == ()


def test_commit_before_the_last_spin_is_rejected_and_keeps_the_round_open():
    world = World()
    panel = begin(world, "s1", NOW)
    world.draws.spin(panel.id, NOW)
    with pytest.raises(DrawRejectedError):
        world.draws.commit(panel.id, NOW)
    assert world.draws.get(panel.id, NOW).draft.pending


def test_spin_after_the_last_task_is_rejected():
    world = World()
    panel = begin(world, "s1", NOW)
    world.draws.spin_rest(panel.id, NOW)
    with pytest.raises(DrawRejectedError):
        world.draws.spin(panel.id, NOW)


def test_cancel_discards_without_trace():
    world = World()
    panel = begin(world, "s1", NOW)
    world.draws.cancel(panel.id, NOW)
    assert world.history.rounds == {} and world.events.drawn == []
    with pytest.raises(NotFoundError):
        world.draws.get(panel.id, NOW)


def test_non_admin_may_cancel_only_before_the_first_spin():
    world = World()
    panel = begin(world, "s1", NOW)
    world.draws.cancel(panel.id, NOW, is_admin=False)
    panel = begin(world, "s1", NOW)
    world.draws.spin(panel.id, NOW)
    with pytest.raises(DrawRejectedError):
        world.draws.cancel(panel.id, NOW, is_admin=False)
    assert world.draws.get(panel.id, NOW).draft.results
    world.draws.cancel(panel.id, NOW, is_admin=True)


def test_non_admin_cannot_replace_a_drawn_round_by_restarting():
    world = World()
    panel = begin(world, "s1", NOW)
    world.draws.spin(panel.id, NOW)
    with pytest.raises(DrawRejectedError):
        begin(world, "s1", NOW, is_admin=False)
    assert world.draws.get(panel.id, NOW).draft.results
    assert begin(world, "s1", NOW, is_admin=True).id != panel.id


def test_panel_round_expires_after_the_time_limit():
    world = World()
    panel = begin(world, "s1", NOW)
    assert world.draws.get(panel.id, panel.expires_at - dt.timedelta(seconds=1))
    with pytest.raises(NotFoundError):
        world.draws.spin(panel.id, panel.expires_at)
    with pytest.raises(NotFoundError):
        world.draws.commit(panel.id, panel.expires_at)


def test_begin_replaces_an_open_round_of_the_same_schedule():
    world = World()
    first = begin(world, "s1", NOW)
    second = begin(world, "s1", NOW)
    assert [p.id for p in world.draws.open_rounds(NOW)] == [second.id]
    with pytest.raises(NotFoundError):
        world.draws.get(first.id, NOW)


def test_automatic_round_does_not_wait_for_an_open_panel_round():
    world = World()
    panel = begin(world, "s1", NOW)
    world.draws.draw("s1", AUTO, NOW)
    with pytest.raises(NotFoundError):
        world.draws.get(panel.id, NOW)


def test_number_of_open_panel_rounds_is_limited():
    world = World()
    for number in range(MAX_OPEN_PANEL_ROUNDS):
        world.put_schedule(id=f"s{number + 2}", slug=f"plan{number}", name=f"Plan {number}")
        begin(world, f"s{number + 2}", NOW)
    with pytest.raises(LimitReachedError):
        begin(world, "s1", NOW)
    assert len(world.draws.open_rounds(NOW)) == MAX_OPEN_PANEL_ROUNDS
    assert world.draws.open_rounds(NOW + dt.timedelta(hours=1)) == ()


def test_a_person_with_a_task_is_not_on_the_wheel_for_the_next_task_of_the_round():
    world = World(0.1)
    first, second = world.draws.draw("s1", AUTO, NOW).assignments
    assert (first.person_id, second.person_id) == ("p1", "p2")
    assert second.chance == 1.0


def test_surplus_tasks_stay_unassigned_instead_of_giving_a_person_a_second_one():
    world = World(0.1)
    world.config.remove_person("p2")
    round_ = world.draws.draw("s1", AUTO, NOW)
    assert [a.person_id for a in round_.assignments] == ["p1"]


def test_manual_draws_of_one_schedule_keep_a_minimum_interval():
    world = World()
    world.draws.draw("s1", MANUAL, NOW)
    with pytest.raises(DrawRejectedError) as err:
        world.draws.draw("s1", RoundOrigin.SERVICE, NOW + DRAW_MIN_INTERVAL / 2)
    assert err.value.key == "draw_too_soon"
    assert dict(err.value.placeholders) == {"seconds": DRAW_MIN_INTERVAL_SECONDS}
    assert len(world.history.rounds) == 1
    world.draws.draw("s1", MANUAL, NOW + DRAW_MIN_INTERVAL + SECOND)
    assert len(world.history.rounds) == 2


def test_automatic_draws_and_other_schedules_ignore_the_minimum_interval():
    world = World()
    world.put_schedule(id="s2", slug="s2", name="S2")
    world.draws.draw("s1", MANUAL, NOW)
    world.draws.draw("s1", AUTO, NOW)
    world.draws.draw("s2", MANUAL, NOW)
    assert len(world.history.rounds) == 3


def test_commit_keeps_the_minimum_interval_and_the_round_open():
    world = World()
    world.draws.draw("s1", MANUAL, NOW)
    panel = begin(world, "s1", NOW + DRAW_MIN_INTERVAL / 3)
    world.draws.spin_rest(panel.id, NOW)
    with pytest.raises(DrawRejectedError):
        world.draws.commit(panel.id, NOW + DRAW_MIN_INTERVAL / 2)
    assert world.draws.get(panel.id, NOW)
    assert world.draws.commit(panel.id, NOW + DRAW_MIN_INTERVAL + SECOND)


@pytest.mark.parametrize("gone", ["person", "task", "schedule"])
def test_commit_rejects_and_drops_a_round_whose_winner_was_deleted(gone: str):
    world = World()
    panel = begin(world, "s1", NOW)
    world.draws.spin_rest(panel.id, NOW)
    {
        "person": lambda: world.config.remove_person("p1"),
        "task": lambda: world.config.remove_task("t1"),
        "schedule": lambda: world.config.remove_schedule("s1"),
    }[gone]()
    with pytest.raises(NotFoundError):
        world.draws.commit(panel.id, NOW)
    assert world.history.rounds == {} and world.events.drawn == []
    assert world.draws.open_rounds(NOW) == ()


# --- Gilt-ab, Frist und Bestätigung beim manuellen Auslösen ------------------------------------


def test_panel_round_uses_the_given_window_for_every_assignment():
    world = World(0.1, 0.9)
    panel = begin(world, "s1")
    world.draws.spin_rest(panel.id, NOW)
    round_ = world.draws.commit(panel.id, NOW)
    assert {(a.starts_at, a.due_at) for a in round_.assignments} == {(WINDOW.start, WINDOW.end)}


def test_scheduled_draw_uses_the_deadline_of_the_schedule():
    world = World(0.1, 0.9)
    world.put_schedule(
        deadline=Deadline(start=DeadlineStart.NEXT_DAY, duration=4, duration_unit=HOUR)
    )
    round_ = world.draws.draw("s1", AUTO, NOW)
    expected = dt.datetime(2026, 11, 4, 10, tzinfo=dt.UTC)
    assert {(a.starts_at, a.due_at) for a in round_.assignments} == {
        (expected, expected + 4 * HOUR_DELTA)
    }


def test_person_absent_during_the_whole_window_gets_nothing():
    wednesday = dt.date(2026, 11, 4)
    world = World(0.1, 0.9)
    world.config.put_person(
        f.person(
            id="p1", slug="p1", name="p1", absences=(OnceAbsence(start=wednesday, end=wednesday),)
        )
    )
    world.put_schedule(
        deadline=Deadline(start=DeadlineStart.NEXT_DAY, duration=4, duration_unit=HOUR)
    )
    round_ = world.draws.draw("s1", AUTO, NOW)
    assert {a.person_id for a in round_.assignments} == {"p2"}


def test_scheduled_schedule_needs_confirmation_that_the_next_run_is_replaced():
    world = World()
    world.put_schedule(trigger=Recurring(weekdays=frozenset({0}), time=dt.time(7)))
    with pytest.raises(DrawRejectedError) as caught:
        world.draws.begin("s1", NOW, WINDOW)
    assert caught.value.key == "draw_replace_unconfirmed"
    assert world.draws.open_rounds(NOW) == ()
    panel = world.draws.begin("s1", NOW, WINDOW, replace_next=True)
    assert panel.draft.replaces == dt.datetime(2026, 11, 9, 7, tzinfo=dt.UTC)


def test_paused_scheduled_schedule_has_no_run_to_replace():
    world = World()
    world.put_schedule(trigger=Recurring(weekdays=frozenset({0}), time=dt.time(7)), enabled=False)
    assert world.draws.begin("s1", NOW, WINDOW).draft.replaces is None


def _with_spare_tasks(world: World) -> None:
    """Zeitplan s1 mit vier Aufgaben: t3 machbar, t4 nur für eine unbekannte Person erlaubt."""
    every = f.task(id="t3").frequency
    both = frozenset({"p1", "p2"})
    world.config.put_task(f.task(id="t3", name="C", allowed=both, frequency=every))
    world.config.put_task(f.task(id="t4", name="D", allowed=frozenset({"p9"}), frequency=every))
    world.put_schedule(task_ids=("t1", "t2", "t3", "t4"))


def test_replacements_list_tasks_outside_the_round_with_feasibility():
    world = World()
    _with_spare_tasks(world)
    panel = begin(world, "s1")
    assert [t.id for t in panel.draft.tasks] == ["t1", "t2"]
    options = world.draws.replacements(panel.id, "t1", NOW)
    assert [(o.task_id, o.doable) for o in options] == [("t3", True), ("t4", False)]


def test_replace_task_swaps_in_place_before_the_start():
    world = World()
    _with_spare_tasks(world)
    panel = begin(world, "s1")
    replaced = world.draws.replace_task(panel.id, "t1", "t3", NOW)
    assert [t.id for t in replaced.draft.tasks] == ["t3", "t2"]
    assert world.draws.get(panel.id, NOW).draft.tasks == replaced.draft.tasks
    assert [o.task_id for o in world.draws.replacements(panel.id, "t3", NOW)] == ["t1", "t4"]


def test_replacement_must_keep_the_round_assignable():
    world = World()
    every = f.task(id="t3").frequency
    world.config.put_task(f.task(id="t1", allowed=frozenset({"p1"})))
    world.config.put_task(f.task(id="t2", allowed=frozenset({"p2"})))
    world.config.put_task(f.task(id="t3", name="C", allowed=frozenset({"p1"}), frequency=every))
    world.put_schedule(task_ids=("t1", "t2", "t3"))
    panel = begin(world, "s1")
    assert [t.id for t in panel.draft.tasks] == ["t1", "t2"]
    # t3 darf nur t1 ersetzen: gegen t2 getauscht hätten beide nur p1 zur Auswahl
    assert [(o.task_id, o.doable) for o in world.draws.replacements(panel.id, "t1", NOW)] == [
        ("t3", True)
    ]
    assert [(o.task_id, o.doable) for o in world.draws.replacements(panel.id, "t2", NOW)] == [
        ("t3", False)
    ]
    with pytest.raises(DrawRejectedError, match="draw_replacement_infeasible"):
        world.draws.replace_task(panel.id, "t2", "t3", NOW)


def test_replace_task_is_logged_as_exchange_before_the_start():
    world = World()
    _with_spare_tasks(world)
    panel = begin(world, "s1")
    world.draws.replace_task(panel.id, "t1", "t3", NOW)
    (record,) = world.decision_store.records.values()
    assert record.kind.value == "exchange" and record.schedule_id == "s1"
    assert (record.exchange.task_id, record.exchange.other_task_id) == ("t1", "t3")
    assert record.exchange.before_start is True


def test_rejected_replacement_is_not_logged():
    world = World()
    _with_spare_tasks(world)
    panel = begin(world, "s1")
    with pytest.raises(DrawRejectedError):
        world.draws.replace_task(panel.id, "t1", "t4", NOW)
    assert not world.decision_store.records


def test_replace_task_is_locked_after_the_first_spin():
    world = World()
    _with_spare_tasks(world)
    panel = begin(world, "s1")
    world.draws.spin(panel.id, NOW)
    assert world.draws.replacements(panel.id, "t1", NOW) == ()
    with pytest.raises(DrawRejectedError, match="draw_already_started"):
        world.draws.replace_task(panel.id, "t2", "t3", NOW)


def test_replace_task_rejects_infeasible_and_foreign_tasks():
    world = World()
    _with_spare_tasks(world)
    world.config.put_task(f.task(id="t5", allowed=frozenset({"p1"})))
    panel = begin(world, "s1")
    with pytest.raises(DrawRejectedError, match="draw_replacement_infeasible"):
        world.draws.replace_task(panel.id, "t1", "t4", NOW)
    for new_id in ("t5", "t2", "fehlt"):  # nicht im Zeitplan, schon in der Runde, unbekannt
        with pytest.raises(DrawRejectedError, match="draw_replacement_invalid"):
            world.draws.replace_task(panel.id, "t1", new_id, NOW)
    with pytest.raises(DrawRejectedError, match="draw_replacement_invalid"):
        world.draws.replace_task(panel.id, "t4", "t3", NOW)
    assert [t.id for t in world.draws.get(panel.id, NOW).draft.tasks] == ["t1", "t2"]
