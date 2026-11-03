"""Bezeichner der Entitäten und ihrer Geräte (KONZEPT §6.3)."""

from typing import Final

from .defaults import DOMAIN

# Schlüssel der Entitäten (zugleich Übersetzungsschlüssel und Teil der eindeutigen Kennung)
KEY_SENSOR_OPEN: Final = "open"
KEY_SENSOR_POINTS: Final = "points"
KEY_SENSOR_NEXT_DRAW: Final = "next_draw"
KEY_TODO_TASKS: Final = "tasks"
KEY_BUTTON_DRAW: Final = "draw"

# Eindeutige Kennung = `<Kennung der Person oder des Zeitplans>_<Schlüssel>`
UNIQUE_ID_SEPARATOR: Final = "_"
UNIQUE_ID_TEMPLATE: Final = "{item_id}{separator}{key}"

# Geräte: je Person und je Zeitplan eines; der Name ergibt die Entity-IDs (`task_wheel_anna_offen`)
DEVICE_NAME_TEMPLATE: Final = "Task Wheel {name}"
DEVICE_MANUFACTURER: Final = "Task Wheel of Fortune"
DEVICE_MODEL_PERSON: Final = "Person"
DEVICE_MODEL_SCHEDULE: Final = "Zeitplan"

# Signale (Dispatcher): ein Signal je Person und je Zeitplan, damit nur Betroffene schreiben
SIGNAL_PERSON_TEMPLATE: Final = f"{DOMAIN}_person_{{item_id}}"
SIGNAL_SCHEDULE_TEMPLATE: Final = f"{DOMAIN}_schedule_{{item_id}}"

# Sekunden nach der geplanten Auslosung, bis der Sensor „nächste Auslosung“ neu rechnet
NEXT_DRAW_REFRESH_DELAY_SECONDS: Final = 1

# Fehlerschlüssel
ERR_TODO_COMPLETE_ONLY: Final = "todo_complete_only"
