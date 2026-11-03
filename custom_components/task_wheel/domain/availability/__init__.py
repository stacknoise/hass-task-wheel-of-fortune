"""Anwesenheitsregeln: Strategien, Fabrik und Kalender einer Person."""

from .calendar import DayPresence, PersonAvailability
from .factory import RULE_BUILDERS, AvailabilityRuleFactory
from .rule import AvailabilityRule
from .strategies import OnceRule, WeeklyDaysRule, WeekRhythmRule

__all__ = [
    "RULE_BUILDERS",
    "AvailabilityRule",
    "AvailabilityRuleFactory",
    "DayPresence",
    "OnceRule",
    "PersonAvailability",
    "WeekRhythmRule",
    "WeeklyDaysRule",
]
