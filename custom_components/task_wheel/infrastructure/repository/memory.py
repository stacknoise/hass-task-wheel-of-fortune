"""In-Memory-Speicher für Tests und Entwicklung: dieselben Repositories ohne Home Assistant."""

from collections.abc import Callable
from typing import Any

from ...domain.serialization import encode


class MemoryStore:
    """Ersetzt `Store`: hält die zuletzt gesicherten Daten im Speicher (als JSON-Struktur)."""

    def __init__(self, data: Any = None) -> None:  # noqa: ANN401 - untypisierte JSON-Daten
        """Startet optional mit vorhandenen Daten."""
        self.data = data
        self.pending: Callable[[], Any] | None = None
        self.delay: float | None = None

    async def async_load(self) -> Any:  # noqa: ANN401
        """Liefert die gesicherten Daten (oder `None`)."""
        return self.data

    async def async_save(self, data: Any) -> None:  # noqa: ANN401
        """Sichert sofort und verwirft eine geplante Sicherung."""
        self.data = encode(data)
        self.pending = None

    def async_delay_save(self, data_func: Callable[[], Any], delay: float = 0) -> None:
        """Merkt die Sicherung vor; `flush_pending` löst sie aus (wie ein Zeitgeber)."""
        self.pending = data_func
        self.delay = delay

    def flush_pending(self) -> None:
        """Führt die vorgemerkte Sicherung aus."""
        if self.pending is not None:
            self.data = encode(self.pending())
            self.pending = None
