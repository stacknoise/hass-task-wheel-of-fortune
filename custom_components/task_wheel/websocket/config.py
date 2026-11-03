"""Konfigurationsbefehle `person/*`, `task/*`, `schedule/*`, `settings/update` (Administratoren)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import voluptuous as vol

from ..application.config_service import Fields
from ..application.wire import to_json
from ..const.events import (
    WS_ACTION_CREATE,
    WS_ACTION_DELETE,
    WS_ACTION_UPDATE,
    WS_PERSON_PREFIX,
    WS_SCHEDULE_PREFIX,
    WS_SETTINGS_UPDATE,
    WS_TASK_PREFIX,
)
from ..const.keys import WIRE_SETTINGS, WS_FIELD_PERSON_ID, WS_FIELD_SCHEDULE_ID, WS_FIELD_TASK_ID
from ..domain.models import Person, Schedule, Settings, Task
from ..domain.serialization import Model
from .command import Access, Command, Reply, Request
from .schemas import ID, model_fields

type Create = Callable[[Request, Fields], Model]
type Update = Callable[[Request, str, Fields], Model]
type Delete = Callable[[Request, str], None]

KEY_PERSON: Final = "person"
KEY_TASK: Final = "task"
KEY_SCHEDULE: Final = "schedule"


@dataclass(slots=True, frozen=True)
class Resource:
    """Eine Art von Konfiguration mit ihren drei Befehlen anlegen, ändern, löschen."""

    prefix: str
    key: str
    id_field: str
    model: type[Model]
    create: Create
    update: Update
    delete: Delete


RESOURCES: Final = (
    Resource(
        WS_PERSON_PREFIX,
        KEY_PERSON,
        WS_FIELD_PERSON_ID,
        Person,
        lambda r, fields: r.data.configuration.create_person(fields),
        lambda r, ident, fields: r.data.configuration.update_person(ident, fields),
        lambda r, ident: r.data.configuration.delete_person(ident),
    ),
    Resource(
        WS_TASK_PREFIX,
        KEY_TASK,
        WS_FIELD_TASK_ID,
        Task,
        lambda r, fields: r.data.configuration.create_task(fields),
        lambda r, ident, fields: r.data.configuration.update_task(ident, fields),
        lambda r, ident: r.data.configuration.delete_task(ident, r.now),
    ),
    Resource(
        WS_SCHEDULE_PREFIX,
        KEY_SCHEDULE,
        WS_FIELD_SCHEDULE_ID,
        Schedule,
        lambda r, fields: r.data.configuration.create_schedule(fields, r.now),
        lambda r, ident, fields: r.data.configuration.update_schedule(ident, fields, r.now),
        lambda r, ident: r.data.configuration.delete_schedule(ident),
    ),
)


def _object(resource: Resource, *, required: bool) -> vol.Schema:
    """Liefert das Schema des Objekts im Befehl: nur Felder des Modells, begrenzt in Größe."""
    return vol.Schema(model_fields(resource.model, required=required), extra=vol.PREVENT_EXTRA)


def _commands(resource: Resource) -> tuple[Command, ...]:
    """Die drei Befehle einer Art."""

    def create(request: Request) -> Reply:
        return Reply(to_json(resource.create(request, request.params[resource.key])))

    def update(request: Request) -> Reply:
        params = request.params
        return Reply(
            to_json(resource.update(request, params[resource.id_field], params[resource.key]))
        )

    def delete(request: Request) -> Reply:
        resource.delete(request, request.params[resource.id_field])
        return Reply()

    return (
        Command(
            f"{resource.prefix}{WS_ACTION_CREATE}",
            {vol.Required(resource.key): _object(resource, required=True)},
            create,
            Access.ADMIN,
            mutates=True,
        ),
        Command(
            f"{resource.prefix}{WS_ACTION_UPDATE}",
            {
                vol.Required(resource.id_field): ID,
                vol.Required(resource.key): _object(resource, required=False),
            },
            update,
            Access.ADMIN,
            mutates=True,
        ),
        Command(
            f"{resource.prefix}{WS_ACTION_DELETE}",
            {vol.Required(resource.id_field): ID},
            delete,
            Access.ADMIN,
            mutates=True,
        ),
    )


def _update_settings(request: Request) -> Reply:
    """Ändert die genannten Einstellungen."""
    return Reply(to_json(request.data.configuration.update_settings(request.params[WIRE_SETTINGS])))


COMMANDS: Final = (
    *(command for resource in RESOURCES for command in _commands(resource)),
    Command(
        WS_SETTINGS_UPDATE,
        {
            vol.Required(WIRE_SETTINGS): vol.Schema(
                model_fields(Settings, required=False), extra=vol.PREVENT_EXTRA
            )
        },
        _update_settings,
        Access.ADMIN,
        mutates=True,
    ),
)
