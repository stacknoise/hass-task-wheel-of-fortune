"""Machbarkeit: wer eine Aufgabe im Fenster der Frist übernehmen kann."""

import datetime as dt

from custom_components.task_wheel.domain.deadline import DeadlineWindow
from custom_components.task_wheel.domain.draw.feasibility import (
    feasible_persons,
    feasible_tasks,
    is_feasible,
)
from custom_components.task_wheel.domain.enums import Load
from custom_components.task_wheel.domain.models import OnceAbsence

from ..factories import NOW, TODAY, task
from .helpers import make_context, make_person

DAY = dt.timedelta(days=1)


def _context(window: DeadlineWindow):
    away_tomorrow = OnceAbsence(start=TODAY + DAY, end=TODAY + DAY)
    people = [
        make_person("a", absences=(away_tomorrow,)),
        make_person("b"),
        make_person("c", load=Load.HALF),
    ]
    return make_context(people, window=window)


def test_present_on_any_day_of_the_window_is_enough():
    context = _context(DeadlineWindow(NOW, NOW + 2 * DAY))
    assert feasible_persons(task(allowed=frozenset()), context) == {"a", "b", "c"}


def test_absent_for_the_whole_window_is_not_feasible():
    window = DeadlineWindow(NOW + DAY, NOW + DAY + dt.timedelta(hours=4))
    assert feasible_persons(task(allowed=frozenset()), _context(window)) == {"b", "c"}


def test_allowed_persons_and_minimum_load_apply():
    context = _context(DeadlineWindow(NOW, NOW + DAY))
    assert feasible_persons(task(allowed=frozenset({"a", "c"})), context) == {"a", "c"}
    assert feasible_persons(task(allowed=frozenset(), min_load=Load.FULL), context) == {"a", "b"}


def test_tasks_nobody_can_do_are_left_out():
    window = DeadlineWindow(NOW + DAY, NOW + DAY + dt.timedelta(hours=4))
    context = _context(window)
    only_a = task(id="t1", allowed=frozenset({"a"}))
    anyone = task(id="t2", allowed=frozenset())
    assert not is_feasible(only_a, context) and is_feasible(anyone, context)
    assert feasible_tasks([only_a, anyone], context) == (anyone,)
    ignoring = task(id="t3", allowed=frozenset({"a"}), respect_absence=False)
    assert is_feasible(ignoring, context)
