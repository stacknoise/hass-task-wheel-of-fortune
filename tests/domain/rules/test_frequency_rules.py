"""Tabellengetriebene Tests der Häufigkeitsregeln inkl. Periodengrenzen."""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from custom_components.task_wheel.domain.enums import Period
from custom_components.task_wheel.domain.errors import UnknownKindError, ValidationError
from custom_components.task_wheel.domain.models import EveryRound, Interval, MaxPerPeriod
from custom_components.task_wheel.domain.rules import (
    EveryRoundRule,
    FrequencyRuleFactory,
    IntervalRule,
    MaxPerPeriodRule,
)

BERLIN = ZoneInfo("Europe/Berlin")


def at(year: int, month: int, day: int, hour: int = 12, tz: dt.tzinfo = BERLIN) -> dt.datetime:
    return dt.datetime(year, month, day, hour, tzinfo=tz)


@pytest.mark.parametrize(
    ("config", "assigned", "now", "due"),
    [
        # Tag
        (MaxPerPeriod(count=1, period=Period.DAY), [], at(2026, 11, 4), True),
        (MaxPerPeriod(count=1, period=Period.DAY), [at(2026, 11, 4, 1)], at(2026, 11, 4), False),
        (MaxPerPeriod(count=1, period=Period.DAY), [at(2026, 11, 3, 23)], at(2026, 11, 4, 0), True),
        # Woche (Montag): Sonntag -> Montag wechselt die Periode
        (MaxPerPeriod(count=1, period=Period.WEEK), [at(2026, 11, 1)], at(2026, 11, 2), True),
        (MaxPerPeriod(count=1, period=Period.WEEK), [at(2026, 11, 2)], at(2026, 11, 8), False),
        (MaxPerPeriod(count=2, period=Period.WEEK), [at(2026, 11, 2)], at(2026, 11, 8), True),
        # Monatsende / Monatswechsel, Schaltjahr
        (MaxPerPeriod(count=1, period=Period.MONTH), [at(2026, 10, 31)], at(2026, 11, 1), True),
        (MaxPerPeriod(count=1, period=Period.MONTH), [at(2026, 11, 1)], at(2026, 11, 30), False),
        (MaxPerPeriod(count=1, period=Period.MONTH), [at(2028, 2, 1)], at(2028, 2, 29), False),
        (MaxPerPeriod(count=1, period=Period.MONTH), [at(2028, 2, 29)], at(2028, 3, 1), True),
        # Jahreswechsel in der Woche
        (MaxPerPeriod(count=1, period=Period.WEEK), [at(2026, 12, 29)], at(2027, 1, 1), False),
        # Sommerzeit: 29.03.2026 hat 23 Stunden, Zuteilung kurz nach Mitternacht lokal
        (
            MaxPerPeriod(count=1, period=Period.DAY),
            [dt.datetime(2026, 3, 28, 23, 30, tzinfo=dt.UTC)],  # 00:30 lokal am 29.03.
            at(2026, 3, 29, 20),
            False,
        ),
        # UTC-Zeitpunkt am Vortag ist lokal schon am nächsten Tag
        (
            MaxPerPeriod(count=1, period=Period.DAY),
            [dt.datetime(2026, 11, 3, 23, 30, tzinfo=dt.UTC)],  # 00:30 lokal am 04.11.
            at(2026, 11, 4),
            False,
        ),
        # Sommerzeit-Ende 25.10.2026 (25 Stunden)
        (
            MaxPerPeriod(count=2, period=Period.DAY),
            [at(2026, 10, 25, 0)],
            at(2026, 10, 25, 23),
            True,
        ),
    ],
)
def test_max_per_period(config, assigned, now, due):
    assert MaxPerPeriodRule(config).is_due(assigned, now) is due


@pytest.mark.parametrize(
    ("config", "assigned", "now", "due"),
    [
        # 1x in 2 Wochen: laufende plus vorherige Woche zählen
        (MaxPerPeriod(count=1, period=Period.WEEK, every=2), [at(2026, 10, 26)], at(2026, 11, 8), False),
        (MaxPerPeriod(count=1, period=Period.WEEK, every=2), [at(2026, 10, 26)], at(2026, 11, 9), True),
        (MaxPerPeriod(count=1, period=Period.WEEK, every=2), [at(2026, 10, 25)], at(2026, 11, 8), True),
        # 5x in 2 Monaten, über den Jahreswechsel
        (
            MaxPerPeriod(count=5, period=Period.MONTH, every=2),
            [at(2026, 12, d) for d in (1, 2, 3)] + [at(2027, 1, 4), at(2027, 1, 5)],
            at(2027, 1, 31),
            False,
        ),
        (
            MaxPerPeriod(count=5, period=Period.MONTH, every=2),
            [at(2026, 12, d) for d in (1, 2, 3)] + [at(2027, 1, 4), at(2027, 1, 5)],
            at(2027, 2, 1),
            True,
        ),
        (MaxPerPeriod(count=2, period=Period.MONTH, every=2), [at(2026, 10, 31), at(2026, 11, 1)], at(2026, 12, 1), True),
        # 2 Tage: heute und gestern
        (MaxPerPeriod(count=1, period=Period.DAY, every=2), [at(2026, 11, 3)], at(2026, 11, 4), False),
        (MaxPerPeriod(count=1, period=Period.DAY, every=2), [at(2026, 11, 2)], at(2026, 11, 4), True),
        # Standard every=1 bleibt unverändert (alte Daten)
        (MaxPerPeriod(count=1, period=Period.WEEK), [at(2026, 10, 30)], at(2026, 11, 2), True),
    ],
)
def test_max_per_period_spanning_several_periods(config, assigned, now, due):
    assert MaxPerPeriodRule(config).is_due(assigned, now) is due


@pytest.mark.parametrize(
    ("config", "assigned", "now", "due"),
    [
        (Interval(days=7, tolerance=0), [], at(2026, 11, 4), True),
        (Interval(days=7, tolerance=0), [at(2026, 10, 28)], at(2026, 11, 4), True),
        (Interval(days=7, tolerance=0), [at(2026, 10, 29)], at(2026, 11, 4), False),
        (Interval(days=7, tolerance=2), [at(2026, 10, 30)], at(2026, 11, 4), True),
        (Interval(days=7, tolerance=2), [at(2026, 10, 31)], at(2026, 11, 4), False),
        # nur die letzte Zuteilung zählt, Reihenfolge egal
        (Interval(days=3, tolerance=0), [at(2026, 11, 3), at(2026, 10, 1)], at(2026, 11, 4), False),
        # Kalendertage statt 24-Stunden-Blöcke: über die Sommerzeitumstellung
        (Interval(days=1, tolerance=0), [at(2026, 3, 28, 23)], at(2026, 3, 29, 0), True),
        (Interval(days=2, tolerance=0), [at(2026, 3, 28, 23)], at(2026, 3, 30, 0), True),
        # Jahreswechsel
        (Interval(days=7, tolerance=0), [at(2026, 12, 25)], at(2027, 1, 1), True),
        (Interval(days=7, tolerance=0), [at(2026, 12, 26)], at(2027, 1, 1), False),
    ],
)
def test_interval(config, assigned, now, due):
    assert IntervalRule(config).is_due(assigned, now) is due


def test_every_round_is_always_due():
    rule = EveryRoundRule()
    assert rule.is_due([at(2026, 11, 4)], at(2026, 11, 4)) is True


@pytest.mark.parametrize(
    "rule",
    [
        EveryRoundRule(),
        MaxPerPeriodRule(MaxPerPeriod(count=1, period=Period.DAY)),
        IntervalRule(Interval(days=2)),
    ],
)
def test_naive_now_is_rejected(rule):
    with pytest.raises(ValidationError):
        rule.is_due([], dt.datetime(2026, 11, 4, 12))


def test_naive_assignment_is_rejected():
    rule = MaxPerPeriodRule(MaxPerPeriod(count=1, period=Period.DAY))
    with pytest.raises(ValidationError):
        rule.is_due([dt.datetime(2026, 11, 4, 1)], at(2026, 11, 4))


@pytest.mark.parametrize(
    ("config", "rule_type"),
    [
        (EveryRound(), EveryRoundRule),
        (MaxPerPeriod(count=1, period=Period.WEEK), MaxPerPeriodRule),
        (Interval(days=3), IntervalRule),
    ],
)
def test_factory_creates_rule_for_each_kind(config, rule_type):
    assert isinstance(FrequencyRuleFactory.create(config), rule_type)


def test_factory_rejects_unregistered_kind():
    class Unknown:
        kind = "unknown"

    with pytest.raises(UnknownKindError):
        FrequencyRuleFactory.create(Unknown())  # type: ignore[arg-type]
