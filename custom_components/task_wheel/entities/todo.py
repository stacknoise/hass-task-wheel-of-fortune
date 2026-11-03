"""To-do-Liste je Person: offene Zuteilungen; Abhaken erledigt die Zuteilung."""

from typing import TYPE_CHECKING

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..application.round_updates import RESOURCE_ASSIGNMENT
from ..const.defaults import DOMAIN
from ..const.entities import ERR_TODO_COMPLETE_ONLY, KEY_TODO_TASKS
from ..domain.errors import NotFoundError, TaskWheelError
from ..domain.models import Person
from ..runtime import TaskWheelData
from ..services import to_service_error
from .base import Owner, TaskWheelEntity
from .factory import EntityFactory, EntityGroup
from .signals import signal_person

if TYPE_CHECKING:
    from .. import TaskWheelConfigEntry

# `name=None`: die Liste ist die Hauptentität des Geräts (`todo.task_wheel_anna`)
TODO_DESCRIPTION = EntityDescription(key=KEY_TODO_TASKS, name=None)


class PersonTodo(TaskWheelEntity, TodoListEntity):
    """Die offenen Aufgaben einer Person; nur das Abhaken ist erlaubt."""

    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    @property
    def todo_items(self) -> list[TodoItem]:
        """Offene Zuteilungen, früheste Frist zuerst."""
        return [
            TodoItem(
                uid=item.assignment_id,
                summary=item.task_name,
                status=TodoItemStatus.NEEDS_ACTION,
                due=item.due_at,
            )
            for item in self._data.entity_state.open_items(self._item_id)
        ]

    def _require_own(self, assignment_id: str) -> None:
        """Nur offene Zuteilungen dieser Person lassen sich über ihre Liste abhaken."""
        if all(
            item.assignment_id != assignment_id
            for item in self._data.entity_state.open_items(self._item_id)
        ):
            raise NotFoundError(RESOURCE_ASSIGNMENT, assignment_id)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Hakt die Zuteilung ab; jede andere Änderung wird abgelehnt.

        Raises:
            ServiceValidationError: Die Änderung ist kein Abhaken, oder die Zuteilung ist
                nicht mehr offen.
        """
        if item.status is not TodoItemStatus.COMPLETED or item.uid is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key=ERR_TODO_COMPLETE_ONLY
            )
        try:
            self._require_own(item.uid)
            self._data.assignments.complete(item.uid, self._data.clock())
        except TaskWheelError as err:
            raise to_service_error(err) from err


def _lists(data: TaskWheelData, person: Person) -> list[PersonTodo]:
    return [PersonTodo(data, Owner.of_person(person), TODO_DESCRIPTION)]


async def async_setup_entry(
    hass: HomeAssistant, entry: "TaskWheelConfigEntry", async_add_entities: AddEntitiesCallback
) -> None:
    """Richtet die To-do-Listen ein."""
    group = EntityGroup(lambda config: config.persons, _lists, signal_person)
    EntityFactory(hass, entry, Platform.TODO, async_add_entities, (group,)).start()
