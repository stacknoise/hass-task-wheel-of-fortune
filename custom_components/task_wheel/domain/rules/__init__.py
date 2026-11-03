"""Häufigkeitsregeln (Strategy) und ihre Fabrik."""

from .factory import FrequencyRuleFactory
from .protocol import FrequencyRule
from .strategies import EveryRoundRule, IntervalRule, MaxPerPeriodRule

__all__ = [
    "EveryRoundRule",
    "FrequencyRule",
    "FrequencyRuleFactory",
    "IntervalRule",
    "MaxPerPeriodRule",
]
