"""Fabrik für Anwesenheitsregeln: wählt die Strategie über eine unveränderliche Registry."""

from collections.abc import Callable, Iterable, Mapping
from types import MappingProxyType

from ..enums import AbsenceKind
from ..errors import UnknownKindError
from ..models import AbsenceConfig, OnceAbsence, WeeklyDaysAbsence, WeekRhythmAbsence
from .rule import AvailabilityRule
from .strategies import OnceRule, WeeklyDaysRule, WeekRhythmRule

type RuleBuilder = Callable[[AbsenceConfig], AvailabilityRule]

_KIND_FIELD = "kind"

RULE_BUILDERS: Mapping[str, RuleBuilder] = MappingProxyType(
    {
        AbsenceKind.ONCE.value: lambda config: OnceRule(_expect(config, OnceAbsence)),
        AbsenceKind.WEEKLY_DAYS.value: lambda config: WeeklyDaysRule(
            _expect(config, WeeklyDaysAbsence)
        ),
        AbsenceKind.WEEK_RHYTHM.value: lambda config: WeekRhythmRule(
            _expect(config, WeekRhythmAbsence)
        ),
    }
)


def _expect[C: AbsenceConfig](config: AbsenceConfig, config_type: type[C]) -> C:
    """Stellt sicher, dass `config` zur gewählten Strategie passt (verhindert falsche Zuordnung)."""
    if not isinstance(config, config_type):
        raise UnknownKindError(_KIND_FIELD, config.kind)
    return config


class AvailabilityRuleFactory:
    """Erzeugt aus einer `AbsenceConfig` die passende `AvailabilityRule`."""

    def __init__(self, builders: Mapping[str, RuleBuilder] = RULE_BUILDERS) -> None:
        """Übernimmt die Registry; Tests können eine eigene übergeben."""
        self._builders = builders

    def create(self, config: AbsenceConfig) -> AvailabilityRule:
        """Erzeugt die Regel zur Art der Konfiguration.

        Raises:
            UnknownKindError: Die Art ist nicht registriert.
        """
        builder = self._builders.get(config.kind.value)
        if builder is None:
            raise UnknownKindError(_KIND_FIELD, config.kind)
        return builder(config)

    def create_all(self, configs: Iterable[AbsenceConfig]) -> tuple[AvailabilityRule, ...]:
        """Erzeugt die Regeln für mehrere Konfigurationen."""
        return tuple(self.create(config) for config in configs)
