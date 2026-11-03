"""Fabrik der Häufigkeitsregeln: Registry statt Verzweigungen."""

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any

from ...const.keys import FIELD_FREQUENCY
from ..enums import FrequencyKind
from ..errors import UnknownKindError
from ..models import FrequencyConfig
from .protocol import FrequencyRule
from .strategies import EveryRoundRule, IntervalRule, MaxPerPeriodRule

type RuleBuilder = Callable[[Any], FrequencyRule]

_BUILDERS: Mapping[FrequencyKind, RuleBuilder] = MappingProxyType(
    {
        FrequencyKind.EVERY_ROUND: lambda _config: EveryRoundRule(),
        FrequencyKind.MAX_PER_PERIOD: MaxPerPeriodRule,
        FrequencyKind.INTERVAL: IntervalRule,
    }
)


class FrequencyRuleFactory:
    """Erzeugt aus einer `FrequencyConfig` die passende Regel."""

    @staticmethod
    def create(config: FrequencyConfig) -> FrequencyRule:
        """Liefert die Strategie zur Art der Konfiguration."""
        builder = _BUILDERS.get(config.kind)
        if builder is None:
            raise UnknownKindError(FIELD_FREQUENCY, config.kind)
        return builder(config)
