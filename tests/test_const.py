"""Konsistenz der Konstanten."""

from custom_components.task_wheel.const import defaults, events, keys, limits
from custom_components.task_wheel.const.defaults import DOMAIN


def test_names_use_domain_prefix():
    assert f"{DOMAIN}_drawn" == events.EVENT_DRAWN
    assert events.WS_DRAW_BEGIN == "task_wheel/draw/begin"
    assert keys.STORE_CONFIG == "task_wheel.config"


def test_limits_are_ordered():
    assert limits.WEEKDAY_COUNT == 7
    assert limits.MISSED_FACTOR_MIN < limits.MISSED_FACTOR_MAX <= limits.LATE_FACTOR_MIN


def test_retention_covers_rules_and_open_assignments():
    assert limits.RETENTION_MIN >= limits.RECENT_HISTORY_DAYS
    assert limits.RETENTION_MIN >= limits.OPEN_ASSIGNMENT_MAX_AGE_DAYS
    assert limits.RETENTION_MIN <= defaults.DEFAULT_HISTORY_RETENTION_DAYS <= limits.RETENTION_MAX


def test_open_assignment_window_has_a_safety_day():
    longest = limits.DUE_DAYS_MAX + limits.GRACE_HOURS_MAX // limits.HOURS_PER_DAY
    assert limits.OPEN_ASSIGNMENT_MAX_AGE_DAYS > longest
