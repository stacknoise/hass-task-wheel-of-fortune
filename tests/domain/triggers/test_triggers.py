"""Zeitreise-Tests der Auslöser-Strategien über mehrere Wochen, Monate und die Sommerzeit."""

import datetime as dt
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from custom_components.task_wheel.domain.enums import AfterOnce
from custom_components.task_wheel.domain.errors import UnknownKindError, ValidationError
from custom_components.task_wheel.domain.models import ManualTrigger, OnceTrigger, Recurring
from custom_components.task_wheel.domain.triggers.factory import TriggerFactory
from custom_components.task_wheel.domain.triggers.lifecycle import after_fired
from custom_components.task_wheel.domain.triggers.reminder import days_since, reminder_age

from .. import factories as f

BERLIN = ZoneInfo("Europe/Berlin")
MON, TUE, THU, SAT = 0, 1, 3, 5


def at(month: int, day: int, hour: int = 12, minute: int = 0, tz: dt.tzinfo = BERLIN):
    return dt.datetime(2026, month, day, hour, minute, tzinfo=tz)


def recurring(*weekdays: int, time: dt.time = dt.time(7), **overrides: object) -> Recurring:
    return Recurring(weekdays=frozenset(weekdays), time=time, **overrides)  # type: ignore[arg-type]


def next_fire(config, after: dt.datetime) -> dt.datetime | None:
    return TriggerFactory.create(config).next_fire(after)


@pytest.mark.parametrize(
    ("config", "after", "expected"),
    [
        # wöchentlich: nächster gewählter Wochentag
        (recurring(MON, THU, time=dt.time(18, 30)), at(11, 3), at(11, 5, 18, 30)),
        # heute noch, wenn die Uhrzeit noch bevorsteht; sonst nächste Woche (strikt danach)
        (recurring(TUE, time=dt.time(18)), at(11, 3, 10), at(11, 3, 18)),
        (recurring(TUE, time=dt.time(18)), at(11, 3, 18), at(11, 10, 18)),
        # jede zweite Woche ab Ankerwoche (Mo 2. Nov. = Woche 0)
        (recurring(MON, every_n_weeks=2, anchor=dt.date(2026, 11, 2)), at(11, 3), at(11, 16, 7)),
        (recurring(MON, every_n_weeks=2, anchor=dt.date(2026, 11, 2)), at(11, 1), at(11, 2, 7)),
        # Anker in der Zukunft: Wochenindex negativ, Rhythmus bleibt korrekt
        (recurring(MON, every_n_weeks=2, anchor=dt.date(2026, 12, 14)), at(11, 3), at(11, 16, 7)),
        # monatlich: erster gewählter Wochentag des Monats
        (recurring(SAT, monthly=True), at(11, 3), at(11, 7, 7)),
        (recurring(SAT, monthly=True), at(11, 7, 8), at(12, 5, 7)),
        # monatlich mit mehreren Wochentagen: nur der früheste Termin des Monats
        (recurring(MON, THU, monthly=True), at(11, 1), at(11, 2, 7)),
        (recurring(MON, THU, monthly=True), at(11, 2, 8), at(12, 3, 7)),
        (
            recurring(MON, THU, monthly=True),
            at(12, 3, 8),
            dt.datetime(2027, 1, 4, 7, tzinfo=BERLIN),
        ),
        # Jahreswechsel
        (recurring(THU), at(12, 31, 12), dt.datetime(2027, 1, 7, 7, tzinfo=BERLIN)),
    ],
)
def test_recurring_next_fire(config, after, expected):
    assert next_fire(config, after) == expected


def test_recurring_every_n_weeks_hits_only_rhythm_weeks_over_a_year():
    config = recurring(THU, every_n_weeks=4, anchor=dt.date(2026, 11, 2))
    moment, fires = at(11, 1), []
    for _ in range(13):
        moment = next_fire(config, moment)
        fires.append(moment.date())
    assert [(a - b).days for a, b in zip(fires[1:], fires, strict=False)] == [28] * 12


def test_recurring_keeps_local_time_across_dst_change():
    config = recurring(*range(7), time=dt.time(7))
    before = dt.datetime(2026, 10, 24, 8, tzinfo=BERLIN)
    first = next_fire(config, before)  # Sa 25. Okt., Ende der Sommerzeit um 03:00
    second = next_fire(config, first)
    assert (first.hour, first.utcoffset()) == (7, dt.timedelta(hours=1))
    assert (second.hour, second.utcoffset()) == (7, dt.timedelta(hours=1))
    assert first.date() == dt.date(2026, 10, 25)


def test_recurring_in_summer_time_has_other_offset_than_winter():
    config = recurring(*range(7), time=dt.time(7))
    summer = next_fire(config, dt.datetime(2026, 10, 23, 8, tzinfo=BERLIN))
    assert summer.utcoffset() == dt.timedelta(hours=2)


def test_once_fires_only_while_in_the_future():
    config = OnceTrigger(at=at(12, 19, 10))
    assert next_fire(config, at(11, 3)) == at(12, 19, 10)
    assert next_fire(config, at(12, 19, 10)) is None
    assert next_fire(config, at(12, 20)) is None


def test_manual_never_fires():
    assert next_fire(ManualTrigger(), at(11, 3)) is None


@pytest.mark.parametrize("kind", [Recurring, OnceTrigger, ManualTrigger])
def test_naive_time_is_rejected(kind):
    config = {
        Recurring: recurring(MON),
        OnceTrigger: OnceTrigger(at=at(12, 1)),
        ManualTrigger: ManualTrigger(),
    }[kind]
    with pytest.raises(ValidationError):
        next_fire(config, dt.datetime(2026, 11, 3, 10))


def test_factory_rejects_unknown_kind():
    with pytest.raises(UnknownKindError):
        TriggerFactory.create(SimpleNamespace(kind="unbekannt"))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("after", "keeps_id", "result"),
    [
        (AfterOnce.KEEP_MANUAL, True, "manual"),
        (AfterOnce.ARCHIVE, True, "archived"),
        (AfterOnce.DELETE, False, None),
    ],
)
def test_once_lifecycle_after_firing(after, keeps_id, result):
    schedule = f.schedule(trigger=OnceTrigger(at=at(12, 1), after=after))
    updated = after_fired(schedule)
    if not keeps_id:
        assert updated is None
    elif result == "manual":
        assert updated.trigger == ManualTrigger() and updated.enabled and not updated.archived
    else:
        assert updated.archived and not updated.enabled


def test_lifecycle_leaves_other_kinds_unchanged():
    schedule = f.schedule()
    assert after_fired(schedule) is schedule


def test_archived_schedule_must_not_be_enabled():
    with pytest.raises(ValidationError):
        f.schedule(archived=True, enabled=True)


def reminder_schedule(**overrides: object):
    return f.schedule(trigger=ManualTrigger(remind_after_days=7), **overrides)


@pytest.mark.parametrize(
    ("days", "expected"),
    [(0, None), (6, None), (7, 7), (8, None), (14, 14), (15, None)],
)
def test_reminder_comes_after_each_multiple_of_the_period(days, expected):
    last = f.NOW - dt.timedelta(days=days)
    assert reminder_age(reminder_schedule(), last, f.NOW) == expected


@pytest.mark.parametrize(
    "schedule",
    [
        f.schedule(),  # nicht manuell
        f.schedule(trigger=ManualTrigger()),  # ohne Erinnerung
        reminder_schedule(enabled=False),
        reminder_schedule(enabled=False, archived=True),
    ],
)
def test_no_reminder_when_not_applicable(schedule):
    assert reminder_age(schedule, f.NOW - dt.timedelta(days=7), f.NOW) is None


def test_no_reminder_without_any_round():
    assert reminder_age(reminder_schedule(), None, f.NOW) is None


def test_days_since_counts_calendar_days_in_local_zone():
    now = dt.datetime(2026, 11, 3, 0, 30, tzinfo=BERLIN)
    last = dt.datetime(2026, 11, 2, 23, 30, tzinfo=dt.UTC)  # 3. Nov. 00:30 Berlin
    assert days_since(last, now) == 0
