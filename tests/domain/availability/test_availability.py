import datetime as dt

import pytest

from custom_components.task_wheel.domain.availability import (
    RULE_BUILDERS,
    AvailabilityRuleFactory,
    OnceRule,
    PersonAvailability,
    RecurringRule,
    WeeklyDaysRule,
    WeekRhythmRule,
)
from custom_components.task_wheel.domain.errors import UnknownKindError, ValidationError
from custom_components.task_wheel.domain.models import (
    OnceAbsence,
    RecurringAbsence,
    WeeklyDaysAbsence,
    WeekRhythmAbsence,
)
from tests.domain.factories import person

D = dt.date
FRIDAY = 4


def rhythm(anchor: dt.date, present: set[int], cycle: int = 2, change: int = FRIDAY):
    return WeekRhythmRule(
        WeekRhythmAbsence(
            present_weeks=frozenset(present),
            cycle_weeks=cycle,
            change_weekday=change,
            anchor=anchor,
        )
    )


def test_once_inclusive_bounds() -> None:
    rule = OnceRule(OnceAbsence(start=D(2026, 12, 30), end=D(2027, 1, 2)))
    assert rule.is_present(D(2026, 12, 29))
    assert not rule.is_present(D(2026, 12, 30))
    assert not rule.is_present(D(2027, 1, 2))
    assert rule.is_present(D(2027, 1, 3))


def test_weekly_days() -> None:
    rule = WeeklyDaysRule(WeeklyDaysAbsence(weekdays=frozenset({5, 6})))
    assert rule.is_present(D(2026, 11, 6))  # Freitag
    assert not rule.is_present(D(2026, 11, 7))  # Samstag


def test_rhythm_change_day_and_year_boundary() -> None:
    # Anker Fr 2026-12-25, jede 2. Woche (Woche 0 anwesend), Wechsel freitags
    rule = rhythm(D(2026, 12, 25), {0})
    assert rule.is_present(D(2026, 12, 25))
    assert rule.is_present(D(2026, 12, 31))
    assert not rule.is_present(D(2027, 1, 1))  # Wechseltag, Jahreswechsel
    assert not rule.is_present(D(2027, 1, 7))
    assert rule.is_present(D(2027, 1, 8))


def test_rhythm_before_anchor() -> None:
    rule = rhythm(D(2026, 12, 25), {0})
    assert not rule.is_present(D(2026, 12, 24))  # Woche -1 -> Index 1
    assert rule.is_present(D(2026, 12, 11))


def test_rhythm_anchor_not_on_change_day() -> None:
    # Anker Mittwoch, Wechsel Freitag: Woche 0 beginnt am Freitag davor
    rule = rhythm(D(2026, 11, 4), {0})
    assert rule.is_present(D(2026, 10, 30))
    assert rule.is_present(D(2026, 11, 5))
    assert not rule.is_present(D(2026, 11, 6))


def test_two_of_four_weeks() -> None:
    rule = rhythm(D(2026, 11, 2), {0, 1}, cycle=4, change=0)
    flags = [rule.is_present(D(2026, 11, 2) + dt.timedelta(weeks=n)) for n in range(8)]
    assert flags == [True, True, False, False] * 2


def test_factory_all_kinds_and_unknown() -> None:
    factory = AvailabilityRuleFactory()
    configs = (
        OnceAbsence(start=D(2026, 1, 1), end=D(2026, 1, 2)),
        WeeklyDaysAbsence(weekdays=frozenset({0})),
        WeekRhythmAbsence(
            present_weeks=frozenset({0}), cycle_weeks=2, change_weekday=0, anchor=D(2026, 1, 5)
        ),
        RecurringAbsence(weekdays=frozenset({2}), interval_weeks=2, start=D(2026, 1, 7)),
    )
    types = [type(rule) for rule in factory.create_all(configs)]
    assert types == [OnceRule, WeeklyDaysRule, WeekRhythmRule, RecurringRule]
    with pytest.raises(UnknownKindError):
        AvailabilityRuleFactory({}).create(configs[0])


def test_person_availability_combines_rules() -> None:
    p = person(
        absences=(
            WeeklyDaysAbsence(weekdays=frozenset({6})),
            OnceAbsence(start=D(2026, 11, 9), end=D(2026, 11, 10)),
        )
    )
    avail = PersonAvailability.of(p)
    assert not avail.is_present(D(2026, 11, 8))  # Sonntag
    assert not avail.is_present(D(2026, 11, 9))
    assert avail.is_present(D(2026, 11, 11))
    assert avail.present_day_count(D(2026, 11, 7), D(2026, 11, 11)) == 2
    assert avail.present_in_window(D(2026, 11, 8), D(2026, 11, 11))
    assert not avail.present_in_window(D(2026, 11, 9), D(2026, 11, 10))


def test_no_rules_always_present() -> None:
    assert PersonAvailability.of(person(absences=())).is_present(D(2026, 1, 1))


def test_preview_four_weeks() -> None:
    avail = PersonAvailability.of(person(absences=(WeeklyDaysAbsence(weekdays=frozenset({6})),)))
    days = avail.preview(D(2026, 11, 2))
    assert len(days) == 28
    assert sum(not d.present for d in days) == 4
    assert days[-1].day == D(2026, 11, 29)


@pytest.mark.parametrize("weeks", [0, 13])
def test_preview_weeks_range(weeks: int) -> None:
    with pytest.raises(ValidationError):
        PersonAvailability(()).preview(D(2026, 1, 1), weeks)


def test_window_validation() -> None:
    avail = PersonAvailability(())
    with pytest.raises(ValidationError):
        avail.present_in_window(D(2026, 1, 2), D(2026, 1, 1))
    with pytest.raises(ValidationError):
        avail.present_in_window(D(2026, 1, 1), D(2028, 1, 1))


def test_factory_rejects_mismatched_registry_entry() -> None:
    once = OnceAbsence(start=D(2026, 1, 1), end=D(2026, 1, 2))
    wrong = AvailabilityRuleFactory({"once": RULE_BUILDERS["weekly_days"]})
    with pytest.raises(UnknownKindError):
        wrong.create(once)


def test_week_preview_starts_on_monday_of_the_week() -> None:
    avail = PersonAvailability.of_rules((WeeklyDaysAbsence(weekdays=frozenset({0})),))
    days = avail.week_preview(D(2026, 11, 4), 1)
    assert days[0].day == D(2026, 11, 2)
    assert [entry.present for entry in days] == [False, True, True, True, True, True, True]


def recurring(interval: int = 2, end: dt.date | None = None) -> RecurringRule:
    """Jeden zweiten Mittwoch ab Mittwoch, 4.11.2026."""
    return RecurringRule(
        RecurringAbsence(
            weekdays=frozenset({2}), interval_weeks=interval, start=D(2026, 11, 4), end=end
        )
    )


def test_recurring_every_second_wednesday() -> None:
    rule = recurring()
    assert not rule.is_present(D(2026, 11, 4))
    assert rule.is_present(D(2026, 11, 11))
    assert not rule.is_present(D(2026, 11, 18))
    assert rule.is_present(D(2026, 11, 19))  # anderer Wochentag in einer Abwesenheitswoche
    assert not rule.is_present(D(2027, 1, 1) - dt.timedelta(days=2))  # 30.12.2026, Jahreswechsel


def test_recurring_respects_start_and_end() -> None:
    rule = recurring(end=D(2026, 11, 18))
    assert rule.is_present(D(2026, 10, 28))  # vor dem Beginn
    assert not rule.is_present(D(2026, 11, 18))  # Endtag zählt noch
    assert rule.is_present(D(2026, 12, 2))  # nach dem Ende


def test_recurring_weekdays_before_start_weekday_count_in_first_week() -> None:
    rule = RecurringRule(
        RecurringAbsence(weekdays=frozenset({0, 4}), interval_weeks=2, start=D(2026, 11, 4))
    )
    assert rule.is_present(D(2026, 11, 2))  # Montag vor dem Beginn
    assert not rule.is_present(D(2026, 11, 6))  # Freitag derselben Woche
    assert rule.is_present(D(2026, 11, 13))
    assert not rule.is_present(D(2026, 11, 16))  # Montag zwei Wochen später
