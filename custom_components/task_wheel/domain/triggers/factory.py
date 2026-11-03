"""Fabrik der Auslöser: Registry statt Verzweigungen."""

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any

from ...const.keys import KEY_KIND
from ..enums import TriggerKind
from ..errors import UnknownKindError
from ..models import TriggerConfig
from .protocol import TriggerStrategy
from .strategies import ManualStrategy, OnceStrategy, RecurringStrategy

type TriggerBuilder = Callable[[Any], TriggerStrategy]

_BUILDERS: Mapping[TriggerKind, TriggerBuilder] = MappingProxyType(
    {
        TriggerKind.RECURRING: RecurringStrategy,
        TriggerKind.ONCE: OnceStrategy,
        TriggerKind.MANUAL: ManualStrategy,
    }
)


class TriggerFactory:
    """Erzeugt aus einer `TriggerConfig` die passende Strategie."""

    @staticmethod
    def create(config: TriggerConfig) -> TriggerStrategy:
        """Liefert die Strategie zur Art der Konfiguration.

        Raises:
            UnknownKindError: Die Art ist nicht registriert.
        """
        builder = _BUILDERS.get(config.kind)
        if builder is None:
            raise UnknownKindError(KEY_KIND, config.kind)
        return builder(config)
