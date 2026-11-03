"""`NotifierFactory`: wählt die Versandart nach Art des Ziels (Registry statt Verzweigung)."""

from collections.abc import Callable, Mapping
from types import MappingProxyType

from homeassistant.core import HomeAssistant

from ...domain.enums import NotifyTargetKind
from .senders import EntitySender, NoSender, Sender, ServiceSender

type Builder = Callable[[HomeAssistant], Sender]

_BUILDERS: Mapping[NotifyTargetKind, Builder] = MappingProxyType(
    {
        NotifyTargetKind.NOTIFY_ENTITY: EntitySender,
        NotifyTargetKind.NOTIFY_SERVICE: ServiceSender,
        NotifyTargetKind.NONE: lambda _hass: NoSender(),
    }
)


class NotifierFactory:
    """Erzeugt den `Sender` zu einer Art von Ziel."""

    @staticmethod
    def create(kind: NotifyTargetKind, hass: HomeAssistant) -> Sender:
        """Liefert den Sender; jede Art ist registriert."""
        return _BUILDERS[kind](hass)
