"""`EntityFactory`: legt Entitäten je Person und Zeitplan an und entfernt sie wieder."""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..application.protocols import ConfigRepository
from ..const.defaults import DOMAIN
from ..domain.models import Person, Schedule
from ..runtime import TaskWheelData
from .base import device_name, item_id_of

PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR, Platform.TODO, Platform.BUTTON)

type Item = Person | Schedule
type TaskWheelEntry = ConfigEntry[TaskWheelData]


@dataclass(frozen=True, slots=True)
class EntityGroup[T: Item]:
    """Die Entitäten einer Art von Elementen: welche es gibt, wie sie entstehen, woran sie hören."""

    items: Callable[[ConfigRepository], Mapping[str, T]]
    build: Callable[[TaskWheelData, T], Iterable[Entity]]
    signal: Callable[[str], str]


def active_schedules(config: ConfigRepository) -> Mapping[str, Schedule]:
    """Zeitpläne, die nicht archiviert sind (archivierte lösen nie wieder aus)."""
    return {key: item for key, item in config.schedules.items() if not item.archived}


class EntityFactory:
    """Gleicht die Entitäten einer Plattform mit der Konfiguration ab, ohne Abfragen.

    Der Abgleich läuft einmal beim Start und danach bei jeder Änderung der Konfiguration:
    neue Personen und Zeitpläne bekommen Entitäten, gelöschte verlieren sie samt Gerät,
    geänderte melden sich über ihr Signal.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: TaskWheelEntry,
        domain: Platform,
        add_entities: AddEntitiesCallback,
        groups: Sequence[EntityGroup[Person] | EntityGroup[Schedule]],
    ) -> None:
        """Merkt sich Plattform und Gruppen; `start` nimmt den Betrieb auf."""
        self._hass = hass
        self._entry = entry
        self._data = entry.runtime_data
        self._domain = domain
        self._add = add_entities
        self._groups = groups
        self._known: list[dict[str, Item]] = [{} for _ in groups]

    def start(self) -> None:
        """Legt die vorhandenen Entitäten an und folgt künftigen Änderungen."""
        self.sync()
        self._entry.async_on_unload(self._data.config.subscribe(self.sync))

    @callback
    def sync(self) -> None:
        """Entfernt Entitäten gelöschter Elemente, legt neue an und meldet geänderte."""
        current = [group.items(self._data.config) for group in self._groups]
        self._remove_stale({key for items in current for key in items})
        created: list[Entity] = []
        for group, known, items in zip(self._groups, self._known, current, strict=True):
            created.extend(self._create(group, known, items))
            self._notify_changed(group, known, items)
        if created:
            self._add(created)

    def _create(
        self,
        group: EntityGroup[Person] | EntityGroup[Schedule],
        known: dict[str, Item],
        items: Mapping[str, Item],
    ) -> list[Entity]:
        """Baut die Entitäten der Elemente, die noch keine haben."""
        created: list[Entity] = []
        for key in items.keys() - known.keys():
            known[key] = items[key]
            created.extend(group.build(self._data, items[key]))  # type: ignore[arg-type]
        return created

    def _notify_changed(
        self,
        group: EntityGroup[Person] | EntityGroup[Schedule],
        known: dict[str, Item],
        items: Mapping[str, Item],
    ) -> None:
        """Meldet Elemente, die sich seit dem letzten Abgleich geändert haben."""
        for key, item in items.items():
            if known[key] != item:
                known[key] = item
                self._rename_device(key, item.name)
                async_dispatcher_send(self._hass, group.signal(key))

    def _device_of(self, registry: dr.DeviceRegistry, item_id: str) -> dr.DeviceEntry | None:
        """Das Gerät eines Elements unter den Geräten dieser Config Entry.

        Statt des ab Home Assistant 2027.8 entfallenden `async_get_device` wird über die Geräte der
        Config Entry gesucht (höchstens eine Person oder ein Zeitplan je Gerät).
        """
        identifier = (DOMAIN, item_id)
        devices = dr.async_entries_for_config_entry(registry, self._entry.entry_id)
        return next((device for device in devices if identifier in device.identifiers), None)

    def _rename_device(self, item_id: str, name: str) -> None:
        """Übernimmt einen geänderten Namen in das Gerät (die Entity-IDs bleiben stabil)."""
        registry = dr.async_get(self._hass)
        device = self._device_of(registry, item_id)
        if device is not None and device.name != device_name(name):
            registry.async_update_device(device.id, name=device_name(name))

    def _remove_stale(self, current: set[str]) -> None:
        """Entfernt Entitäten und leere Geräte gelöschter Personen und Zeitpläne."""
        entities = er.async_get(self._hass)
        stale: set[str] = set()
        for entity in er.async_entries_for_config_entry(entities, self._entry.entry_id):
            if (
                entity.domain == self._domain
                and (item := item_id_of(entity.unique_id)) not in current
            ):
                stale.add(item)
                entities.async_remove(entity.entity_id)
        self._remove_empty_devices(entities, stale)

    def _remove_empty_devices(self, entities: er.EntityRegistry, item_ids: set[str]) -> None:
        """Entfernt die Geräte der Elemente, an denen keine Entität mehr hängt."""
        devices = dr.async_get(self._hass)
        for item in item_ids:
            device = self._device_of(devices, item)
            if device is not None and not er.async_entries_for_device(
                entities, device.id, include_disabled_entities=True
            ):
                devices.async_remove_device(device.id)
