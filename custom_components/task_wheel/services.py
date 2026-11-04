"""Dienste `draw`, `complete`, `swap`, `set_absence` (Schicht 2, KONZEPT §6.1)."""

import datetime as dt
from collections.abc import Callable, Mapping
from typing import Any, Final

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .access import ensure_allowed
from .application.lookup import find_by_ref
from .const.defaults import DOMAIN
from .const.events import SERVICE_COMPLETE, SERVICE_DRAW, SERVICE_SET_ABSENCE, SERVICE_SWAP
from .const.keys import (
    ATTR_ANIMATE_ON,
    ATTR_ASSIGNMENT_ID,
    ATTR_END,
    ATTR_PERSON,
    ATTR_SCHEDULE,
    ATTR_START,
    ATTR_TASK,
    ATTR_TO_PERSON,
    ERR_NOT_LOADED,
    ERR_TARGET_REQUIRED,
    RESOURCE_PERSON,
    RESOURCE_SCHEDULE,
    RESOURCE_TASK,
)
from .const.limits import REF_MAX_LENGTH, REF_MIN_LENGTH
from .domain.enums import RoundOrigin
from .domain.errors import TaskWheelError, ValidationError
from .domain.models import Person, Schedule, Task
from .entry_lookup import loaded_runtime
from .runtime import TaskWheelData
from .service_errors import to_service_error

type Handler = Callable[[TaskWheelData, Mapping[str, Any], dt.datetime], None]

_REF = vol.All(cv.string, vol.Length(min=REF_MIN_LENGTH, max=REF_MAX_LENGTH))


SCHEMAS: Final[Mapping[str, vol.Schema | vol.All]] = {
    SERVICE_DRAW: vol.Schema(
        {vol.Required(ATTR_SCHEDULE): _REF, vol.Optional(ATTR_ANIMATE_ON): cv.entity_id}
    ),
    SERVICE_COMPLETE: vol.Schema(
        {
            vol.Optional(ATTR_ASSIGNMENT_ID): _REF,
            vol.Optional(ATTR_PERSON): _REF,
            vol.Optional(ATTR_TASK): _REF,
        }
    ),
    SERVICE_SWAP: vol.Schema(
        {vol.Required(ATTR_ASSIGNMENT_ID): _REF, vol.Required(ATTR_TO_PERSON): _REF}
    ),
    SERVICE_SET_ABSENCE: vol.Schema(
        {
            vol.Required(ATTR_PERSON): _REF,
            vol.Required(ATTR_START): cv.date,
            vol.Required(ATTR_END): cv.date,
        }
    ),
}


def _person(data: TaskWheelData, ref: str) -> Person:
    """Person über Kennung oder Kurzname."""
    return find_by_ref(data.config.persons.values(), ref, RESOURCE_PERSON, _id_or_slug)


def _schedule(data: TaskWheelData, ref: str) -> Schedule:
    """Zeitplan über Kennung oder Kurzname."""
    return find_by_ref(data.config.schedules.values(), ref, RESOURCE_SCHEDULE, _id_or_slug)


def _task(data: TaskWheelData, ref: str) -> Task:
    """Aufgabe über Kennung oder Namen."""
    return find_by_ref(
        data.config.tasks.values(), ref, RESOURCE_TASK, lambda item: (item.id, item.name)
    )


def _id_or_slug(item: Person | Schedule) -> tuple[str, str]:
    """Die Schlüssel, über die ein Dienst Personen und Zeitpläne anspricht."""
    return (item.id, item.slug)


def _draw(data: TaskWheelData, call: Mapping[str, Any], now: dt.datetime) -> None:
    """Löst die Runde aus; mit `animate_on` bittet es zusätzlich eine Anzeige um die Animation."""
    schedule = _schedule(data, call[ATTR_SCHEDULE])
    round_ = data.draws.draw(schedule.id, RoundOrigin.SERVICE, now)
    target = call.get(ATTR_ANIMATE_ON)
    if target is not None:
        data.events.animation_requested(round_, target)


def _ensure_one_target(call: Mapping[str, Any]) -> None:
    """`complete` braucht `assignment_id` oder `person` zusammen mit `task`, aber nicht beides."""
    by_id = ATTR_ASSIGNMENT_ID in call
    by_name = ATTR_PERSON in call and ATTR_TASK in call
    if by_id == by_name:
        raise ValidationError(ATTR_ASSIGNMENT_ID, ERR_TARGET_REQUIRED)


def _complete(data: TaskWheelData, call: Mapping[str, Any], now: dt.datetime) -> None:
    """Erledigt die Zuteilung (direkt oder über Person und Aufgabe)."""
    _ensure_one_target(call)
    assignment_id = call.get(ATTR_ASSIGNMENT_ID)
    if assignment_id is None:
        person = _person(data, call[ATTR_PERSON])
        assignment_id = data.assignments.find_open(person.id, _task(data, call[ATTR_TASK]).id).id
    data.assignments.complete(assignment_id, now)


def _swap(data: TaskWheelData, call: Mapping[str, Any], now: dt.datetime) -> None:
    """Tauscht die Zuteilung gegen die offene Zuteilung der Zielperson."""
    receiver = _person(data, call[ATTR_TO_PERSON])
    data.swaps.swap(call[ATTR_ASSIGNMENT_ID], receiver.id, now)


def _set_absence(data: TaskWheelData, call: Mapping[str, Any], now: dt.datetime) -> None:
    """Fügt eine einmalige Abwesenheit hinzu (die Fachlogik liegt im `ConfigService`)."""
    person = _person(data, call[ATTR_PERSON])
    data.configuration.add_absence(person.id, call[ATTR_START], call[ATTR_END], now.date())


HANDLERS: Final[Mapping[str, Handler]] = {
    SERVICE_DRAW: _draw,
    SERVICE_COMPLETE: _complete,
    SERVICE_SWAP: _swap,
    SERVICE_SET_ABSENCE: _set_absence,
}


def _runtime(hass: HomeAssistant) -> TaskWheelData:
    """Laufzeitdaten der geladenen Config Entry; ohne sie sind die Dienste nicht nutzbar."""
    data = loaded_runtime(hass)
    if data is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key=ERR_NOT_LOADED)
    return data


def _service(hass: HomeAssistant, handler: Handler) -> Callable[[ServiceCall], Any]:
    """Verpackt den Handler: Laufzeitdaten holen, Uhrzeit lesen, Fachfehler übersetzen."""

    async def call(service_call: ServiceCall) -> None:
        data = _runtime(hass)
        await ensure_allowed(
            hass, service_call.context, admin_only=data.config.settings.panel_admin_only
        )
        try:
            handler(data, service_call.data, data.clock())
        except TaskWheelError as err:
            raise to_service_error(err) from err
        finally:
            data.live.publish()

    return call


def async_register_services(hass: HomeAssistant) -> None:
    """Meldet alle Dienste an (einmal beim Start der Integration)."""
    for name, handler in HANDLERS.items():
        hass.services.async_register(DOMAIN, name, _service(hass, handler), schema=SCHEMAS[name])
