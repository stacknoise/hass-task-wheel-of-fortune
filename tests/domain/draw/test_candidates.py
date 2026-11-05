import datetime as dt

from custom_components.task_wheel.domain.deadline import DeadlineWindow
from custom_components.task_wheel.domain.draw.candidates import (
    CandidateFilterFactory,
    CandidateSelector,
    MinLoadFilter,
    NoRepeatFilter,
    PausedFilter,
    RoundTakenFilter,
)
from custom_components.task_wheel.domain.enums import ExclusionReason, Load
from custom_components.task_wheel.domain.models import OnceAbsence, RecurringAbsence

from ..factories import NOW, TODAY, task
from .helpers import make_context, make_person

AB = frozenset({"a", "b"})


def reasons(selection):
    return {(e.person_id, e.reason) for e in selection.exclusions}


def test_paused_and_unknown_persons_are_removed():
    ctx = make_context([make_person("a"), make_person("b", load=Load.PAUSED)])
    selection = CandidateSelector().select(task(allowed=frozenset({"a", "b", "ghost"})), ctx)
    assert [p.id for p in selection.candidates] == ["a"]
    assert reasons(selection) == {("b", ExclusionReason.PAUSED)}


def test_task_without_allowed_persons_is_open_for_everyone_in_the_round():
    ctx = make_context([make_person("b"), make_person("a")])
    selection = CandidateSelector().select(task(allowed=frozenset()), ctx)
    assert [p.id for p in selection.candidates] == ["a", "b"]


def test_person_is_candidate_if_present_on_any_day_of_the_window():
    gone = OnceAbsence(start=TODAY, end=TODAY + dt.timedelta(days=30))
    back = OnceAbsence(start=TODAY, end=TODAY + dt.timedelta(days=2))
    ctx = make_context(
        [make_person("a", absences=(gone,)), make_person("b", absences=(back,))],
        window=DeadlineWindow(NOW, NOW + dt.timedelta(days=7)),
    )
    selection = CandidateSelector().select(task(allowed=AB), ctx)
    assert [p.id for p in selection.candidates] == ["b"]
    assert reasons(selection) == {("a", ExclusionReason.ABSENT)}


def test_only_the_days_of_the_window_count_not_the_day_of_the_draw():
    # Dienstag 16:00 ausgelost, gilt ab Mittwoch 10:00 für 4 Stunden: wer am Mittwoch fehlt, kann
    # nichts übernehmen, auch wenn er am Dienstag anwesend ist
    wednesday = TODAY + dt.timedelta(days=1)
    away = OnceAbsence(start=wednesday, end=wednesday)
    ctx = make_context(
        [make_person("a", absences=(away,)), make_person("b")],
        window=DeadlineWindow(
            dt.datetime(2026, 11, 4, 10, tzinfo=dt.UTC), dt.datetime(2026, 11, 4, 14, tzinfo=dt.UTC)
        ),
    )
    selection = CandidateSelector().select(task(allowed=AB), ctx)
    assert [p.id for p in selection.candidates] == ["b"]
    assert reasons(selection) == {("a", ExclusionReason.ABSENT)}


def test_recurring_absence_excludes_person_when_the_window_is_that_one_day():
    recurring = RecurringAbsence(
        weekdays=frozenset({TODAY.weekday()}), interval_weeks=2, start=TODAY, end=None
    )
    ctx = make_context(
        [make_person("a", absences=(recurring,)), make_person("b")],
        window=DeadlineWindow(NOW, NOW + dt.timedelta(hours=2)),
    )
    selection = CandidateSelector().select(task(allowed=AB), ctx)
    assert [p.id for p in selection.candidates] == ["b"]
    assert reasons(selection) == {("a", ExclusionReason.ABSENT)}


def test_absence_ignored_when_task_does_not_respect_it():
    gone = OnceAbsence(start=TODAY, end=TODAY + dt.timedelta(days=30))
    ctx = make_context([make_person("a", absences=(gone,)), make_person("b")])
    selection = CandidateSelector().select(task(allowed=AB, respect_absence=False), ctx)
    assert [p.id for p in selection.candidates] == ["a", "b"]


def test_no_repeat_removes_last_holder_when_others_remain():
    ctx = make_context([make_person("a"), make_person("b")], last_holders={"t1": "a"})
    selection = CandidateSelector().select(task(allowed=AB, no_repeat=True), ctx)
    assert [p.id for p in selection.candidates] == ["b"]
    assert reasons(selection) == {("a", ExclusionReason.REPEAT)}


def test_no_repeat_keeps_sole_candidate():
    ctx = make_context([make_person("a")], last_holders={"t1": "a"})
    selection = CandidateSelector().select(task(allowed=frozenset({"a"}), no_repeat=True), ctx)
    assert [p.id for p in selection.candidates] == ["a"]
    assert not selection.exclusions


def test_no_repeat_ignores_holder_outside_candidates():
    ctx = make_context([make_person("a"), make_person("b")], last_holders={"t1": "x"})
    selection = CandidateSelector().select(task(allowed=AB, no_repeat=True), ctx)
    assert len(selection.candidates) == 2


def test_chain_order_and_conditions():
    chain = CandidateFilterFactory().create_chain(task(no_repeat=True, respect_absence=False))
    assert [type(f) for f in chain] == [PausedFilter, RoundTakenFilter, NoRepeatFilter]
    assert len(CandidateFilterFactory().create_chain(task())) == 3


def test_min_load_filter_only_in_chain_when_task_demands_it():
    chain = CandidateFilterFactory().create_chain(task(min_load=Load.FULL))
    assert MinLoadFilter in [type(f) for f in chain]


def test_min_load_excludes_lower_capacity_and_leaves_unassigned_if_nobody_fits():
    ctx = make_context([make_person("a", load=Load.HALF), make_person("b", load=Load.FULL)])
    selection = CandidateSelector().select(task(allowed=AB, min_load=Load.FULL), ctx)
    assert [p.id for p in selection.candidates] == ["b"]
    assert reasons(selection) == {("a", ExclusionReason.LOAD)}
    only_half = make_context([make_person("a", load=Load.HALF)])
    assert (
        not CandidateSelector().select(task(allowed=AB, min_load=Load.FULL), only_half).candidates
    )


def test_min_load_half_accepts_half_and_full_but_default_accepts_all():
    ctx = make_context([make_person("a", load=Load.HALF), make_person("b", load=Load.FULL)])
    assert (
        len(CandidateSelector().select(task(allowed=AB, min_load=Load.HALF), ctx).candidates) == 2
    )
    assert len(CandidateSelector().select(task(allowed=AB), ctx).candidates) == 2


def test_nobody_left_gives_empty_selection():
    ctx = make_context([make_person("a", load=Load.PAUSED)])
    selection = CandidateSelector().select(task(allowed=frozenset({"a"})), ctx)
    assert not selection.candidates


def test_person_with_a_task_in_this_round_is_not_on_the_wheel():
    ctx = make_context([make_person("a"), make_person("b")], round_holders=frozenset({"a"}))
    selection = CandidateSelector().select(task(allowed=AB), ctx)
    assert [p.id for p in selection.candidates] == ["b"]
    assert reasons(selection) == {("a", ExclusionReason.TAKEN)}


def test_nobody_is_left_when_every_candidate_already_has_a_task():
    ctx = make_context([make_person("a"), make_person("b")], round_holders=AB)
    selection = CandidateSelector().select(task(allowed=AB), ctx)
    assert not selection.candidates
    assert reasons(selection) == {("a", ExclusionReason.TAKEN), ("b", ExclusionReason.TAKEN)}


def test_last_person_gets_the_task_even_if_they_held_it_before():
    ctx = make_context(
        [make_person("a"), make_person("b")],
        last_holders={"t1": "b"},
        round_holders=frozenset({"a"}),
    )
    selection = CandidateSelector().select(task(allowed=AB, no_repeat=True), ctx)
    assert [p.id for p in selection.candidates] == ["b"]
    assert not selection.exclusions or ("b", ExclusionReason.REPEAT) not in reasons(selection)


def test_person_needed_for_a_stricter_task_is_not_on_the_wheel():
    ctx = make_context([make_person("a"), make_person("b")])
    strict = task(id="t2", allowed=frozenset({"a"}))
    selection = CandidateSelector().select(task(allowed=AB), ctx, (strict,))
    assert [p.id for p in selection.candidates] == ["b"]
    assert reasons(selection) == {("a", ExclusionReason.NEEDED)}


def test_nobody_is_held_back_when_the_rest_cannot_use_them():
    ctx = make_context([make_person("a"), make_person("b")])
    selection = CandidateSelector().select(task(allowed=AB), ctx, (task(id="t2", allowed=AB),))
    assert [p.id for p in selection.candidates] == ["a", "b"]
