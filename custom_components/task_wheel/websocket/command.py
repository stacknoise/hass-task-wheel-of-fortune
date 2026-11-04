"""Ein Befehl der Panel-API: Name, Schema, Recht und Handler (ohne Home Assistant)."""

import datetime as dt
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import voluptuous as vol

from ..application.wire import Json
from ..const.keys import WS_KEY_ID, WS_KEY_TYPE
from ..runtime import TaskWheelData
from .schemas import MESSAGE_ID

type Params = Mapping[str, Any]
type Push = Callable[[Json], None]
type Cleanup = Callable[[], None]


class Access(StrEnum):
    """Wer den Befehl ausführen darf."""

    USER = "user"
    ADMIN = "admin"


@dataclass(slots=True, frozen=True)
class Request:
    """Alles, was ein Handler braucht: Laufzeitdaten, Uhrzeit, geprüfte Felder, Rückkanal."""

    data: TaskWheelData
    now: dt.datetime
    params: Params
    push: Push
    is_admin: bool = False


@dataclass(slots=True, frozen=True)
class Reply:
    """Antwort eines Handlers; `on_close` meldet ein Abonnement beim Schließen ab."""

    result: object = None
    on_close: Cleanup | None = None


type Handler = Callable[[Request], Reply]


@dataclass(slots=True, frozen=True)
class Command:
    """Ein Befehl: `fields` sind die erlaubten Felder (ohne `id` und `type`)."""

    name: str
    fields: Mapping[Any, Any]
    handler: Handler
    access: Access = Access.USER
    mutates: bool = False
    subscribes: bool = False

    def schema(self) -> vol.Schema:
        """Vollständiges Schema der Nachricht; unbekannte Felder sind nicht erlaubt."""
        base = {vol.Required(WS_KEY_ID): MESSAGE_ID, vol.Required(WS_KEY_TYPE): self.name}
        return vol.Schema({**base, **self.fields}, extra=vol.PREVENT_EXTRA)

    def run(self, request: Request) -> Reply:
        """Führt den Handler aus; nach einer Änderung bekommen Abonnenten das Delta."""
        reply = self.handler(request)
        if self.mutates:
            request.data.live.publish()
        return reply
