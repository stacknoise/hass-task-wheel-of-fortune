"""Live-Ansicht: Abonnenten erhalten nach dem Snapshot nur noch Änderungen je Objekt (§6.4)."""

import datetime as dt
from collections.abc import Callable
from itertools import count

from ..const.keys import RESOURCE_SUBSCRIPTION
from ..const.limits import MAX_SUBSCRIPTIONS
from ..domain.errors import LimitReachedError
from .protocols import FireCallback, TimerPort
from .views import Snapshot, SnapshotBuilder, diff
from .wire import Json

type Listener = Callable[[Json], None]
type Unsubscribe = Callable[[], None]
type Clock = Callable[[], dt.datetime]


class LiveView:
    """Hält den zuletzt gesendeten Stand und verteilt Deltas an alle Abonnenten.

    Es wird nur gerechnet, solange es Abonnenten gibt. `publish` ist billig, wenn sich
    nichts geändert hat (ein Vergleich je Objekt).
    """

    def __init__(self, builder: SnapshotBuilder, clock: Clock) -> None:
        """Hält Bauer und Uhr; ohne Abonnenten gibt es keinen gemerkten Stand."""
        self._builder = builder
        self._clock = clock
        self._listeners: dict[int, Listener] = {}
        self._ids = count()
        self._last: Snapshot | None = None

    def snapshot(self) -> Snapshot:
        """Der aktuelle Stand (ohne zu abonnieren)."""
        return self._builder.build(self._clock())

    def subscribe(self, listener: Listener) -> tuple[Snapshot, Unsubscribe]:
        """Meldet den Abonnenten an und liefert den Stand, auf dem seine Deltas aufbauen.

        Raises:
            LimitReachedError: Es sind schon zu viele Abonnenten angemeldet.
        """
        if len(self._listeners) >= MAX_SUBSCRIPTIONS:
            raise LimitReachedError(RESOURCE_SUBSCRIPTION, MAX_SUBSCRIPTIONS)
        self.publish()
        snapshot = self._last or self.snapshot()
        key = next(self._ids)
        self._listeners[key] = listener
        self._last = snapshot
        return snapshot, lambda: self._unsubscribe(key)

    def drop_all(self) -> None:
        """Meldet alle Abonnenten ab (der Zugriff wurde auf Administratoren beschränkt)."""
        self._listeners.clear()
        self._last = None

    def _unsubscribe(self, key: int) -> None:
        """Entfernt den Abonnenten (mehrfaches Abmelden ist unschädlich)."""
        self._listeners.pop(key, None)

    def publish(self) -> None:
        """Berechnet den Stand neu und schickt die Änderungen an alle Abonnenten."""
        if not self._listeners:
            self._last = None
            return
        current = self.snapshot()
        delta = diff(self._last, current) if self._last else {}
        self._last = current
        if delta:
            for listener in tuple(self._listeners.values()):
                listener(delta)


class AccessWatch:
    """Meldet die Abonnenten ab, sobald der Zugriff auf Administratoren eingeschränkt wird."""

    def __init__(self, live: LiveView, restricted: Callable[[], bool]) -> None:
        """Merkt sich den Stand der Einschränkung; `restricted` liest ihn aus den Einstellungen."""
        self._live = live
        self._restricted = restricted
        self._was = restricted()

    def check(self) -> None:
        """Nach jeder Änderung der Konfiguration aufrufen."""
        now = self._restricted()
        if now and not self._was:
            self._live.drop_all()
        self._was = now


def _nothing() -> None:
    """Tut nichts (Standard ohne Zuhörer)."""


class ObservedTimers:
    """Reicht Zeitgeber durch und meldet nach jedem Auslösen eine mögliche Änderung."""

    def __init__(self, inner: TimerPort) -> None:
        """Hält die eigentlichen Zeitgeber; wer zuhört, meldet sich über `listen` an."""
        self._inner = inner
        self._changed: Callable[[], None] = _nothing

    def listen(self, changed: Callable[[], None]) -> None:
        """Legt fest, was nach jedem Auslösen eines Zeitgebers geschieht."""
        self._changed = changed

    def schedule(self, key: str, at: dt.datetime, callback: FireCallback) -> None:
        """Setzt den Zeitgeber; nach dem Auslösen folgt `changed`."""

        def fire(fired: dt.datetime) -> None:
            try:
                callback(fired)
            finally:
                self._changed()

        self._inner.schedule(key, at, fire)

    def cancel(self, key: str) -> None:
        """Meldet den Zeitgeber ab."""
        self._inner.cancel(key)

    def cancel_all(self) -> None:
        """Meldet alle Zeitgeber ab."""
        self._inner.cancel_all()
