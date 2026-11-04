"""Gemeinsame Grundlage aller Entitäten: Gerät, eindeutige Kennung, Signal statt Abfrage."""

from dataclasses import dataclass

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity, EntityDescription

from ..access import ensure_allowed
from ..const.defaults import DOMAIN
from ..const.entities import (
    DEVICE_MANUFACTURER,
    DEVICE_MODEL_PERSON,
    DEVICE_MODEL_SCHEDULE,
    DEVICE_NAME_TEMPLATE,
    UNIQUE_ID_SEPARATOR,
    UNIQUE_ID_TEMPLATE,
)
from ..domain.models import Person, Schedule
from ..runtime import TaskWheelData
from .signals import signal_person, signal_schedule


def device_name(name: str) -> str:
    """Anzeigename des Geräts einer Person oder eines Zeitplans."""
    return DEVICE_NAME_TEMPLATE.format(name=name)


def unique_id(item_id: str, key: str) -> str:
    """Eindeutige Kennung einer Entität."""
    return UNIQUE_ID_TEMPLATE.format(item_id=item_id, separator=UNIQUE_ID_SEPARATOR, key=key)


def item_id_of(unique: str) -> str:
    """Kennung der Person oder des Zeitplans, zu der die Entität gehört."""
    return unique.partition(UNIQUE_ID_SEPARATOR)[0]


@dataclass(frozen=True, slots=True)
class Owner:
    """Die Person oder der Zeitplan, zu dem eine Entität gehört."""

    item_id: str
    name: str
    model: str
    signal: str

    @classmethod
    def of_person(cls, person: Person) -> "Owner":
        """Besitzer ist eine Person."""
        return cls(person.id, person.name, DEVICE_MODEL_PERSON, signal_person(person.id))

    @classmethod
    def of_schedule(cls, schedule: Schedule) -> "Owner":
        """Besitzer ist ein Zeitplan."""
        return cls(schedule.id, schedule.name, DEVICE_MODEL_SCHEDULE, signal_schedule(schedule.id))


class TaskWheelEntity(Entity):
    """Eine Entität einer Person oder eines Zeitplans; sie schreibt nur auf ihr Signal hin."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, data: TaskWheelData, owner: Owner, description: EntityDescription) -> None:
        """Legt Beschreibung, Kennung und Gerät fest."""
        self._data = data
        self._item_id = owner.item_id
        self._signal = owner.signal
        self.entity_description = description
        self._attr_unique_id = unique_id(owner.item_id, description.key)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, owner.item_id)},
            name=device_name(owner.name),
            manufacturer=DEVICE_MANUFACTURER,
            model=owner.model,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def _ensure_allowed(self) -> None:
        """Lässt Aktionen (Button, Abhaken) nur zu, wenn das Panel-Recht es erlaubt."""
        await ensure_allowed(
            self.hass, self._context, admin_only=self._data.config.settings.panel_admin_only
        )

    async def async_added_to_hass(self) -> None:
        """Hört auf das Signal der Person oder des Zeitplans."""
        self.async_on_remove(async_dispatcher_connect(self.hass, self._signal, self._handle_update))

    @callback
    def _handle_update(self) -> None:
        """Schreibt den Zustand neu; die Werte werden dabei aus den Indizes gelesen."""
        self.async_write_ha_state()
