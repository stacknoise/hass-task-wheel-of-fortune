"""Events auf dem Home-Assistant-Bus (umsetzt `RoundEvents`, KONZEPT §6.2)."""

from typing import Any

from homeassistant.core import HomeAssistant

from ..application import event_payloads as payloads
from ..application.protocols import ConfigRepository
from ..const.events import (
    EVENT_ANIMATE,
    EVENT_COMPLETED,
    EVENT_DRAWN,
    EVENT_MISSED,
    EVENT_REMINDER,
    EVENT_SWAPPED,
)
from ..const.keys import ATTR_ANIMATE_ON
from ..domain.models import Assignment, Round, Schedule


class HassRoundEvents:
    """Feuert die Events; die Inhalte bilden die reinen Funktionen in `event_payloads`."""

    def __init__(self, hass: HomeAssistant, config: ConfigRepository) -> None:
        """Merkt sich Bus und Konfiguration (für Namen in den Inhalten)."""
        self._hass = hass
        self._config = config

    def _fire(self, event: str, payload: dict[str, Any]) -> None:
        """Feuert das Event im Ereignisschleifen-Thread."""
        self._hass.bus.async_fire(event, payload)

    def round_drawn(self, round_: Round) -> None:
        """`task_wheel_drawn` mit allen Zuteilungen der Runde."""
        self._fire(EVENT_DRAWN, payloads.round_payload(self._config, round_))

    def reminder_due(self, schedule: Schedule, days_since: int) -> None:
        """`task_wheel_reminder` für einen Zeitplan ohne Auslosung."""
        self._fire(EVENT_REMINDER, payloads.reminder_payload(schedule, days_since))

    def assignment_completed(self, assignment: Assignment) -> None:
        """`task_wheel_completed` für die erledigte Zuteilung."""
        self._fire(EVENT_COMPLETED, payloads.assignment_payload(self._config, assignment))

    def assignment_swapped(self, assignment: Assignment) -> None:
        """`task_wheel_swapped` samt abgebender Person."""
        self._fire(EVENT_SWAPPED, payloads.swapped_payload(self._config, assignment))

    def assignment_missed(self, assignment: Assignment) -> None:
        """`task_wheel_missed` für die verpasste Zuteilung."""
        self._fire(EVENT_MISSED, payloads.assignment_payload(self._config, assignment))

    def animation_requested(self, round_: Round, target: str) -> None:
        """`task_wheel_animate`: Hinweis für die Anzeige `target` mit dem Inhalt der Runde."""
        payload = payloads.round_payload(self._config, round_)
        self._fire(EVENT_ANIMATE, {**payload, ATTR_ANIMATE_ON: target})
