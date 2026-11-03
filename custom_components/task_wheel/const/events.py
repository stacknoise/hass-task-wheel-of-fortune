"""Event-, Dienst- und Befehlsnamen (KONZEPT §6)."""

from typing import Final

from .defaults import DOMAIN

# Events
EVENT_DRAWN: Final = f"{DOMAIN}_drawn"
EVENT_COMPLETED: Final = f"{DOMAIN}_completed"
EVENT_SWAPPED: Final = f"{DOMAIN}_swapped"
EVENT_MISSED: Final = f"{DOMAIN}_missed"
EVENT_REMINDER: Final = f"{DOMAIN}_reminder"
# Wunsch einer Anzeige (Dienst `draw` mit `animate_on`); keine Zuteilung, nur Hinweis
EVENT_ANIMATE: Final = f"{DOMAIN}_animate"

# Dienste
SERVICE_DRAW: Final = "draw"
SERVICE_COMPLETE: Final = "complete"
SERVICE_SWAP: Final = "swap"
SERVICE_SET_ABSENCE: Final = "set_absence"

# WebSocket-Befehle (Präfix `task_wheel/`)
WS_PREFIX: Final = f"{DOMAIN}/"
WS_SNAPSHOT: Final = f"{WS_PREFIX}snapshot"
WS_SUBSCRIBE: Final = f"{WS_PREFIX}subscribe"
WS_HISTORY_LIST: Final = f"{WS_PREFIX}history/list"
WS_STATISTICS_GET: Final = f"{WS_PREFIX}statistics/get"
WS_ASSIGNMENT_COMPLETE: Final = f"{WS_PREFIX}assignment/complete"
WS_ASSIGNMENT_SWAP: Final = f"{WS_PREFIX}assignment/swap"
WS_ROUND_DELETE: Final = f"{WS_PREFIX}round/delete"
WS_DRAW_BEGIN: Final = f"{WS_PREFIX}draw/begin"
WS_DRAW_SPIN: Final = f"{WS_PREFIX}draw/spin"
WS_DRAW_SPIN_REST: Final = f"{WS_PREFIX}draw/spin_rest"
WS_DRAW_COMMIT: Final = f"{WS_PREFIX}draw/commit"
WS_DRAW_CANCEL: Final = f"{WS_PREFIX}draw/cancel"
WS_SETTINGS_UPDATE: Final = f"{WS_PREFIX}settings/update"
WS_PERSON_PREFIX: Final = f"{WS_PREFIX}person/"
WS_TASK_PREFIX: Final = f"{WS_PREFIX}task/"
WS_SCHEDULE_PREFIX: Final = f"{WS_PREFIX}schedule/"
WS_ACTION_CREATE: Final = "create"
WS_ACTION_UPDATE: Final = "update"
WS_ACTION_DELETE: Final = "delete"
