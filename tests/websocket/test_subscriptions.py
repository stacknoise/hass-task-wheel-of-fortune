"""Abonnements je Verbindung: das älteste weicht, Aufräumen vergisst sie."""

from custom_components.task_wheel.websocket.subscriptions import SubscriptionBook


class FakeConnection:
    """Wie `ActiveConnection`: hashbar, mit den Abmelde-Funktionen je Nachrichtenkennung."""

    def __init__(self) -> None:
        self.subscriptions: dict[int, object] = {}


def _connection() -> FakeConnection:
    return FakeConnection()


def _open(book: SubscriptionBook, connection: FakeConnection, message_id: int, log: list[int]):
    book.make_room(connection)
    connection.subscriptions[message_id] = book.register(
        connection, message_id, lambda: log.append(message_id)
    )


def test_the_oldest_subscription_makes_room_for_a_new_one() -> None:
    book, connection, closed = SubscriptionBook(2), _connection(), []
    for message_id in (1, 2, 3):
        _open(book, connection, message_id, closed)
    assert closed == [1]
    assert set(connection.subscriptions) == {2, 3}


def test_other_connections_and_foreign_subscriptions_are_not_counted() -> None:
    book, closed = SubscriptionBook(1), []
    first, second = _connection(), _connection()
    first.subscriptions[99] = lambda: closed.append(99)  # fremdes Abonnement
    _open(book, first, 1, closed)
    _open(book, second, 2, closed)
    assert closed == []
    assert set(first.subscriptions) == {99, 1}


def test_closing_forgets_the_subscription_and_runs_the_cleanup_once() -> None:
    book, connection, closed = SubscriptionBook(1), _connection(), []
    _open(book, connection, 1, closed)
    cleanup = connection.subscriptions.pop(1)
    cleanup()
    cleanup()
    assert closed == [1]
    _open(book, connection, 2, closed)
    assert closed == [1]


def test_a_subscription_already_removed_by_the_connection_is_forgotten() -> None:
    book, connection, closed = SubscriptionBook(1), _connection(), []
    _open(book, connection, 1, closed)
    del connection.subscriptions[1]
    _open(book, connection, 2, closed)
    assert set(connection.subscriptions) == {2}
    assert closed == []
