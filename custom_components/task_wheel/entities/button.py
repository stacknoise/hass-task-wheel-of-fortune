"""Button „Auslosen“ je Zeitplan (Dashboard, Automationen)."""

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const.entities import KEY_BUTTON_DRAW
from ..domain.enums import RoundOrigin
from ..domain.errors import TaskWheelError
from ..domain.models import Schedule
from ..runtime import TaskWheelData
from ..service_errors import to_service_error
from .base import Owner, TaskWheelEntity
from .factory import EntityFactory, EntityGroup, TaskWheelEntry, active_schedules
from .signals import signal_schedule

DRAW_BUTTON = ButtonEntityDescription(key=KEY_BUTTON_DRAW, translation_key=KEY_BUTTON_DRAW)


class DrawButton(TaskWheelEntity, ButtonEntity):
    """Löst den Zeitplan wie im Panel aus (Herkunft „manuell“)."""

    async def async_press(self) -> None:
        """Löst eine Runde aus; Fachfehler werden übersetzt gemeldet.

        Raises:
            ServiceValidationError: Der Zeitplan ist archiviert oder die Ziehung nicht möglich.
            Unauthorized: „Panel nur für Administratoren“ ist aktiv, der Benutzer aber keiner.
        """
        data = self._data
        await self._ensure_allowed()
        try:
            data.draws.draw(self._item_id, RoundOrigin.MANUAL, data.clock())
        except TaskWheelError as err:
            raise to_service_error(err) from err


def _buttons(data: TaskWheelData, schedule: Schedule) -> list[DrawButton]:
    return [DrawButton(data, Owner.of_schedule(schedule), DRAW_BUTTON)]


async def async_setup_entry(
    hass: HomeAssistant, entry: TaskWheelEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Richtet die Buttons ein."""
    group = EntityGroup(active_schedules, _buttons, signal_schedule)
    EntityFactory(hass, entry, Platform.BUTTON, async_add_entities, (group,)).start()
