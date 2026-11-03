"""Sensoren: offene Aufgaben und Punkte je Person, nächste Auslosung je Zeitplan."""

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.typing import StateType

from ..application.entity_state import EntityStateService
from ..const.entities import (
    KEY_SENSOR_NEXT_DRAW,
    KEY_SENSOR_OPEN,
    KEY_SENSOR_POINTS,
    NEXT_DRAW_REFRESH_DELAY_SECONDS,
)
from ..domain.models import Person, Schedule
from ..runtime import TaskWheelData
from .base import Owner, TaskWheelEntity
from .factory import EntityFactory, EntityGroup, active_schedules
from .signals import signal_person, signal_schedule

if TYPE_CHECKING:
    from .. import TaskWheelConfigEntry

type ValueFn = Callable[[EntityStateService, str, dt.datetime], StateType | dt.datetime]

_REFRESH_DELAY = dt.timedelta(seconds=NEXT_DRAW_REFRESH_DELAY_SECONDS)


@dataclass(frozen=True, kw_only=True)
class TaskWheelSensorDescription(SensorEntityDescription):
    """Sensorbeschreibung mit der Funktion, die den Wert aus den Indizes liest."""

    value_fn: ValueFn


PERSON_SENSORS: tuple[TaskWheelSensorDescription, ...] = (
    TaskWheelSensorDescription(
        key=KEY_SENSOR_OPEN,
        translation_key=KEY_SENSOR_OPEN,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state, item_id, _now: state.open_count(item_id),
    ),
    TaskWheelSensorDescription(
        key=KEY_SENSOR_POINTS,
        translation_key=KEY_SENSOR_POINTS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state, item_id, now: state.month_points(item_id, now),
    ),
)

SCHEDULE_SENSORS: tuple[TaskWheelSensorDescription, ...] = (
    TaskWheelSensorDescription(
        key=KEY_SENSOR_NEXT_DRAW,
        translation_key=KEY_SENSOR_NEXT_DRAW,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda state, item_id, now: state.next_draw(item_id, now),
    ),
)


class TaskWheelSensor(TaskWheelEntity, SensorEntity):
    """Sensor, dessen Wert die Beschreibung aus den Indizes liest."""

    entity_description: TaskWheelSensorDescription

    @property
    def native_value(self) -> StateType | dt.datetime:
        """Aktueller Wert."""
        return self.entity_description.value_fn(
            self._data.entity_state, self._item_id, self._data.clock()
        )


class NextDrawSensor(TaskWheelSensor):
    """Nächste Auslosung; rechnet nach dem Zeitpunkt neu, auch wenn die Auslosung ausfiel."""

    _cancel_refresh: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Hört auf das Signal und plant die Neuberechnung."""
        await super().async_added_to_hass()
        self.async_on_remove(self._cancel)
        self._arm()

    @callback
    def _handle_update(self) -> None:
        super()._handle_update()
        self._arm()

    @callback
    def _arm(self) -> None:
        """Plant die Neuberechnung kurz nach dem angezeigten Zeitpunkt."""
        self._cancel()
        value = self.native_value
        if isinstance(value, dt.datetime):
            self._cancel_refresh = async_track_point_in_time(
                self.hass, self._due, value + _REFRESH_DELAY
            )

    @callback
    def _due(self, _now: dt.datetime) -> None:
        self._cancel_refresh = None
        self._handle_update()

    @callback
    def _cancel(self) -> None:
        if self._cancel_refresh is not None:
            self._cancel_refresh()
            self._cancel_refresh = None


def _person_sensors(data: TaskWheelData, person: Person) -> list[TaskWheelSensor]:
    return [TaskWheelSensor(data, Owner.of_person(person), item) for item in PERSON_SENSORS]


def _schedule_sensors(data: TaskWheelData, schedule: Schedule) -> list[NextDrawSensor]:
    return [NextDrawSensor(data, Owner.of_schedule(schedule), item) for item in SCHEDULE_SENSORS]


GROUPS = (
    EntityGroup(lambda config: config.persons, _person_sensors, signal_person),
    EntityGroup(active_schedules, _schedule_sensors, signal_schedule),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: "TaskWheelConfigEntry", async_add_entities: AddEntitiesCallback
) -> None:
    """Richtet die Sensoren ein."""
    EntityFactory(hass, entry, Platform.SENSOR, async_add_entities, GROUPS).start()
