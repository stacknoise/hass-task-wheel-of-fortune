"""Abonnements je Verbindung begrenzen: ein Client soll nicht alle Plätze belegen können."""

from collections.abc import Callable, Hashable, MutableMapping
from typing import Any, Protocol

type Cleanup = Callable[[], None]
type Unsubscribe = Callable[[], Any]  # so deklariert Home Assistant `connection.subscriptions`


class Connection(Protocol):
    """Der Teil einer WebSocket-Verbindung, den die Begrenzung braucht."""

    @property
    def subscriptions(self) -> MutableMapping[Hashable, Unsubscribe]:
        """Abmelde-Funktionen der offenen Abonnements nach Nachrichtenkennung."""
        ...


class SubscriptionBook:
    """Merkt sich die eigenen Abonnements je Verbindung; das älteste weicht dem neuesten."""

    def __init__(self, limit: int) -> None:
        """Höchstens `limit` Abonnements je Verbindung."""
        self._limit = limit
        self._open: dict[Connection, dict[int, Cleanup]] = {}

    def make_room(self, connection: Connection) -> None:
        """Meldet die ältesten Abonnements ab, bis ein weiteres Platz hat."""
        mine = self._open.get(connection, {})
        while len(mine) >= self._limit:
            oldest = next(iter(mine))
            cleanup = connection.subscriptions.pop(oldest, None)
            if cleanup is None:
                del mine[oldest]
            else:
                cleanup()

    def register(self, connection: Connection, message_id: int, on_close: Cleanup) -> Cleanup:
        """Merkt sich das Abonnement; die Rückgabe meldet es ab und vergisst es."""
        mine = self._open.setdefault(connection, {})
        mine[message_id] = on_close

        def cleanup() -> None:
            if mine.pop(message_id, None) is not None:
                on_close()
            if not mine:
                self._open.pop(connection, None)

        return cleanup
