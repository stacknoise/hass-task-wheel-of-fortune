"""Konsistenz der Konstanten."""

from custom_components.task_wheel.const import events, keys, limits
from custom_components.task_wheel.const.defaults import DOMAIN


def test_names_use_domain_prefix():
    assert f"{DOMAIN}_drawn" == events.EVENT_DRAWN
    assert events.WS_DRAW_BEGIN == "task_wheel/draw/begin"
    assert keys.STORE_CONFIG == "task_wheel.config"


def test_limits_are_ordered():
    assert limits.WEEKDAY_COUNT == 7
    assert limits.MISSED_FACTOR_MIN < limits.MISSED_FACTOR_MAX <= limits.LATE_FACTOR_MIN
