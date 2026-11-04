"""Schicht 2: WebSocket-API des Panels (KONZEPT §6.4).

Die Befehle stehen in `registry.COMMANDS` (Schema, Recht, Handler, ohne Home Assistant); dieses
Paket meldet sie bei Home Assistant an, prüft das Recht und übersetzt Fachfehler in Fehlerantworten.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized

from ..const.keys import ERR_NOT_LOADED, WS_KEY_ID
from ..const.limits import MAX_SUBSCRIPTIONS_PER_CONNECTION
from ..domain.errors import TaskWheelError
from ..entry_lookup import loaded_runtime
from .command import Access, Command, Request
from .registry import COMMANDS
from .subscriptions import SubscriptionBook

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.components.websocket_api.connection import ActiveConnection


_BOOK = SubscriptionBook(MAX_SUBSCRIPTIONS_PER_CONNECTION)


def _handler(command: Command) -> Callable[[HomeAssistant, ActiveConnection, dict[str, Any]], None]:
    """Verpackt den Befehl: Laufzeit holen, Recht prüfen, Fachfehler als Fehlerantwort senden."""

    @callback
    def handle(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
        message_id = msg[WS_KEY_ID]
        data = loaded_runtime(hass)
        if data is None:
            connection.send_error(message_id, ERR_NOT_LOADED, ERR_NOT_LOADED)
            return
        user = connection.user
        if not user.is_admin and (
            command.access is Access.ADMIN or data.config.settings.panel_admin_only
        ):
            raise Unauthorized
        if command.subscribes:
            _BOOK.make_room(connection)
        request = Request(
            data, data.clock(), msg, lambda payload: connection.send_event(message_id, payload)
        )
        try:
            reply = command.run(request)
        except TaskWheelError as err:
            connection.send_error(message_id, err.key, str(err))
            return
        if reply.on_close is not None:
            connection.subscriptions[message_id] = _BOOK.register(
                connection, message_id, reply.on_close
            )
        connection.send_result(message_id, reply.result)

    return handle


def async_register_commands(hass: HomeAssistant) -> None:
    """Meldet alle Befehle an (einmal beim Start der Integration)."""
    for command in COMMANDS:
        websocket_api.async_register_command(
            hass, command.name, _handler(command), command.schema()
        )
