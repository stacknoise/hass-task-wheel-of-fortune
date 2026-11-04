"""Frist am Zeitplan: Beginn, Dauer, Einheiten, Zeitzonen und Grenzen."""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from custom_components.task_wheel.domain.deadline import Deadline, DeadlineWindow
from custom_components.task_wheel.domain.enums import DeadlineStart, DeadlineUnit
from custom_components.task_wheel.domain.errors import ValidationError

BERLIN = ZoneInfo("Europe/Berlin")
# Dienstag, 10.11.2026, 16:00
DRAW = dt.datetime(2026, 11, 10, 16, tzinfo=BERLIN)
HOUR, DAY, WEEK, MONTH = (
    DeadlineUnit.HOUR,
    DeadlineUnit.DAY,
    DeadlineUnit.WEEK,
    DeadlineUnit.MONTH,
)


def at(day: int, hour: int, minute: int = 0, month: int = 11) -> dt.datetime:
    return dt.datetime(2026, month, day, hour, minute, tzinfo=BERLIN)


def test_default_runs_from_the_draw_for_seven_days():
    window = Deadline().window(DRAW)
    assert (window.start, window.end) == (DRAW, at(17, 16))


def test_next_day_at_a_time_for_a_number_of_hours():
    deadline = Deadline(
        start=DeadlineStart.NEXT_DAY, time=dt.time(10), duration=4, duration_unit=HOUR
    )
    window = deadline.window(DRAW)
    assert (window.start, window.end) == (at(11, 10), at(11, 14))
    assert window.first_day == window.last_day == dt.date(2026, 11, 11)


@pytest.mark.parametrize(
    ("weekday", "expected_day"),
    [(3, 12), (1, 17), (0, 16)],  # Donnerstag, derselbe Wochentag -> eine Woche später, Montag
)
def test_next_weekday_is_never_today(weekday, expected_day):
    deadline = Deadline(start=DeadlineStart.WEEKDAY, weekday=weekday, time=dt.time(9, 30))
    assert deadline.window(DRAW).start == at(expected_day, 9, 30)


@pytest.mark.parametrize(
    ("unit", "start"),
    [(HOUR, at(10, 18)), (DAY, at(12, 16)), (WEEK, at(24, 16)), (MONTH, at(10, 16, month=1))],
)
def test_offset_in_every_unit(unit, start):
    window = Deadline(start=DeadlineStart.OFFSET, offset=2, offset_unit=unit, duration=1).window(
        DRAW
    )
    expected = start if unit is not MONTH else dt.datetime(2027, 1, 10, 16, tzinfo=BERLIN)
    assert window.start == expected


def test_months_are_calendar_months_and_shorten_the_day():
    january = dt.datetime(2027, 1, 31, 12, tzinfo=BERLIN)
    window = Deadline(duration=1, duration_unit=MONTH).window(january)
    assert window.end == dt.datetime(2027, 2, 28, 12, tzinfo=BERLIN)
    december = dt.datetime(2026, 12, 15, 8, tzinfo=BERLIN)
    assert Deadline(duration=2, duration_unit=MONTH).window(december).end == dt.datetime(
        2027, 2, 15, 8, tzinfo=BERLIN
    )


def test_days_keep_the_wall_clock_across_the_dst_change_but_hours_are_real_time():
    before = dt.datetime(2026, 10, 24, 10, tzinfo=BERLIN)  # Umstellung in der Nacht zum 25.10.
    assert Deadline(duration=1, duration_unit=DAY).window(before).end == dt.datetime(
        2026, 10, 25, 10, tzinfo=BERLIN
    )
    night = dt.datetime(2026, 10, 24, 23, tzinfo=BERLIN)
    end = Deadline(duration=24, duration_unit=HOUR).window(night).end
    assert end == dt.datetime(2026, 10, 25, 22, tzinfo=BERLIN)


def test_window_after_for_a_manual_draw():
    window = DeadlineWindow.after(DRAW, 3, WEEK)
    assert (window.start, window.end) == (DRAW, at(1, 16, month=12))


@pytest.mark.parametrize(("amount", "unit"), [(0, DAY), (-1, HOUR), (13, MONTH), (366, DAY)])
def test_manual_window_rejects_amounts_outside_the_limits(amount, unit):
    with pytest.raises(ValidationError):
        DeadlineWindow.after(DRAW, amount, unit)


def test_window_needs_time_zones_and_a_sensible_order():
    with pytest.raises(ValidationError):
        DeadlineWindow(dt.datetime(2026, 1, 1), DRAW)
    with pytest.raises(ValidationError):
        DeadlineWindow(DRAW, DRAW - dt.timedelta(hours=1))


def test_last_day_is_taken_in_the_zone_of_the_window():
    late = dt.datetime(2026, 11, 10, 23, 30, tzinfo=dt.UTC)  # 00:30 am 11.11. in Berlin
    window = DeadlineWindow(DRAW, late)
    assert window.last_day == dt.date(2026, 11, 11)


@pytest.mark.parametrize(
    "fields",
    [
        {"duration": 0},
        {"duration": 366},
        {"duration": 13, "duration_unit": MONTH},
        {"offset": -1},
        {"weekday": 7},
        {"start": DeadlineStart.WEEKDAY, "duration": 365},
    ],
)
def test_deadline_rejects_invalid_values(fields):
    with pytest.raises(ValidationError):
        Deadline(**fields)


def test_deadline_round_trips_through_dict():
    deadline = Deadline(
        start=DeadlineStart.WEEKDAY, weekday=2, time=dt.time(8, 15), duration=2, duration_unit=WEEK
    )
    assert Deadline.from_dict(deadline.to_dict()) == deadline
    assert Deadline.from_dict({}) == Deadline()
