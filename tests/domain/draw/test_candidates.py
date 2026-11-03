import datetime as dt

from custom_components.task_wheel.domain.draw.candidates import (
    CandidateFilterFactory,
    CandidateSelector,
    NoRepeatFilter,
    PausedFilter,
    RoundTakenFilter,
)
from custom_components.task_wheel.domain.enums import ExclusionReason, Load
from custom_components.task_wheel.domain.models import OnceAbsence

from ..factories import TODAY, task
from .helpers import make_context, make_person

AB = frozenset({"a", "b"})


def reasons(selection):
    return {(e.person_id, e.reason) for e in selection.exclusions}


def test_paused_and_unknown_persons_are_removed():
    ctx = make_context([make_person("a"), make_person("b", load=Load.PAUSED)])
    selection = CandidateSelector().select(task(allowed=frozenset({"a", "b", "ghost"})), ctx)
    assert [p.id for p in selection.candidates] == ["a"]
    assert reasons(selection) == {("b", ExclusionReason.PAUSED)}


def test_absent_throughout_window_is_excluded_but_one_day_present_is_enough():
    gone = OnceAbsence(start=TODAY, end=TODAY + dt.timedelta(days=30))
    back = OnceAbsence(start=TODAY, end=TODAY + dt.timedelta(days=2))
    ctx = make_context([make_person("a", absences=(gone,)), make_person("b", absences=(back,))])
    selection = CandidateSelector().select(task(allowed=AB, due_days=7), ctx)
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
    assert [type(f) for f in chain] == [PausedFilter, NoRepeatFilter, RoundTakenFilter]
    assert len(CandidateFilterFactory().create_chain(task())) == 3


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
