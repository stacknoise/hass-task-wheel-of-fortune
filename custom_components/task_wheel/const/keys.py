"""Schlüssel für Speicher, Serialisierung, Dienste und Fehlermeldungen."""

from typing import Final

from .defaults import DOMAIN

# Speicher
STORE_CONFIG: Final = f"{DOMAIN}.config"
STORE_HISTORY: Final = f"{DOMAIN}.history"
STORE_VERSION: Final = 1
STORE_MINOR_VERSION: Final = 4

KEY_PERSONS: Final = "persons"
KEY_TASKS: Final = "tasks"
KEY_SCHEDULES: Final = "schedules"
KEY_SETTINGS: Final = "settings"
KEY_ROUNDS: Final = "rounds"
KEY_ASSIGNMENTS: Final = "assignments"
KEY_SCHEDULE_ID: Final = "schedule_id"
KEY_AREA_ID: Final = "area_id"
KEY_AREA_IDS: Final = "area_ids"
KEY_AGGREGATES: Final = "aggregates"

# Unterscheidungsmerkmal für Modelle mit mehreren Arten (Strategien)
KEY_KIND: Final = "kind"
FIELD_FREQUENCY: Final = "frequency"

# Dienstdaten (KONZEPT §6.1)
ATTR_SCHEDULE: Final = "schedule"
ATTR_ANIMATE_ON: Final = "animate_on"
ATTR_ASSIGNMENT_ID: Final = "assignment_id"
ATTR_PERSON: Final = "person"
ATTR_TASK: Final = "task"
ATTR_TO_PERSON: Final = "to_person"
ATTR_START: Final = "start"
ATTR_END: Final = "end"

# Ereignisdaten (KONZEPT §6.2): nur Kennungen, Namen und Zahlen
ATTR_ROUND_ID: Final = "round_id"
ATTR_SCHEDULE_ID: Final = "schedule_id"
ATTR_SCHEDULE_NAME: Final = "schedule_name"
ATTR_ORIGIN: Final = "origin"
ATTR_ASSIGNMENTS: Final = "assignments"
ATTR_TASK_ID: Final = "task_id"
ATTR_TASK_NAME: Final = "task_name"
ATTR_PERSON_ID: Final = "person_id"
ATTR_PERSON_NAME: Final = "person_name"
ATTR_FROM_PERSON_ID: Final = "from_person_id"
ATTR_FROM_PERSON_NAME: Final = "from_person_name"
ATTR_POINTS: Final = "points"
ATTR_DUE_AT: Final = "due_at"
ATTR_STATUS: Final = "status"
ATTR_DAYS_SINCE: Final = "days_since"

# Einstellungen im Options Flow (Feldnamen wie in `Settings`)
OPT_JOKERS: Final = "jokers_per_month"
OPT_FAIRNESS_WINDOW: Final = "fairness_window_days"
OPT_RETENTION: Final = "history_retention_days"
OPT_LATE_FACTOR: Final = "late_points_factor"
OPT_MISSED_FACTOR: Final = "missed_points_factor"
OPT_GRACE_HOURS: Final = "missed_grace_hours"
OPT_PANEL_ADMIN_ONLY: Final = "panel_admin_only"
STEP_INIT: Final = "init"
ABORT_NOT_LOADED: Final = "not_loaded"

# Übersetzungsschlüssel für Validierungsfehler
ERR_REQUIRED: Final = "required"
ERR_TYPE: Final = "invalid_type"
ERR_RANGE: Final = "out_of_range"
ERR_LENGTH: Final = "invalid_length"
ERR_PATTERN: Final = "invalid_format"
ERR_UNKNOWN_FIELD: Final = "unknown_field"
ERR_UNKNOWN_KIND: Final = "unknown_kind"
ERR_DUPLICATE: Final = "duplicate"
ERR_EMPTY: Final = "empty"
ERR_ORDER: Final = "invalid_order"
ERR_NAIVE_DATETIME: Final = "naive_datetime"
ERR_INCONSISTENT: Final = "inconsistent"
ERR_LIMIT_REACHED: Final = "limit_reached"
ERR_NOT_FOUND: Final = "not_found"
ERR_AMBIGUOUS: Final = "ambiguous_reference"
ERR_STORAGE_CORRUPT: Final = "storage_corrupt"
ERR_STORAGE_VERSION: Final = "storage_version_unsupported"

# Fehlerschlüssel für Statusübergänge und Tausch
ERR_INVALID_TRANSITION: Final = "invalid_transition"
ERR_SWAP_DISABLED: Final = "swap_disabled"
ERR_SWAP_SAME_PERSON: Final = "swap_same_person"
ERR_SWAP_NOT_ALLOWED: Final = "swap_person_not_allowed"
ERR_SWAP_PAUSED: Final = "swap_person_paused"
ERR_SWAP_LOAD: Final = "swap_person_load_too_low"
ERR_SWAP_ABSENT: Final = "swap_person_absent"
ERR_SWAP_NO_OPEN_ASSIGNMENT: Final = "swap_person_has_no_open_assignment"
ERR_ROUND_HAS_DONE: Final = "round_has_done_assignments"

# Fehlerschlüssel für Runden und Zeitpläne
ERR_SCHEDULE_DISABLED: Final = "schedule_disabled"
ERR_SCHEDULE_ARCHIVED: Final = "schedule_archived"
ERR_ROUND_INCOMPLETE: Final = "round_incomplete"
ERR_ROUND_COMPLETE: Final = "round_complete"
ERR_DRAW_TOO_SOON: Final = "draw_too_soon"
ERR_CANCEL_ADMIN_ONLY: Final = "draw_cancel_admin_only"

# Fehlerschlüssel der Dienste
ERR_NOT_LOADED: Final = "not_loaded"
ERR_TARGET_REQUIRED: Final = "target_required"

# Fehlerschlüssel der Konfiguration über die WebSocket-API
ERR_IN_USE: Final = "in_use"
ERR_TOO_DEEP: Final = "too_deep"

# Felder der WebSocket-Nachrichten (KONZEPT §6.4)
WS_KEY_ID: Final = "id"
WS_KEY_TYPE: Final = "type"
WS_FIELD_PERSON_ID: Final = "person_id"
WS_FIELD_TASK_ID: Final = "task_id"
WS_FIELD_SCHEDULE_ID: Final = "schedule_id"
WS_FIELD_ASSIGNMENT_ID: Final = "assignment_id"
WS_FIELD_ROUND_ID: Final = "round_id"
WS_FIELD_TO_PERSON_ID: Final = "to_person_id"
WS_FIELD_PANEL_ROUND_ID: Final = "panel_round_id"
WS_FIELD_STATUS: Final = "status"
WS_FIELD_SINCE: Final = "since"
WS_FIELD_UNTIL: Final = "until"
WS_FIELD_OFFSET: Final = "offset"
WS_FIELD_LIMIT: Final = "limit"
WS_FIELD_MONTHS: Final = "months"
WS_FIELD_WEEKS: Final = "weeks"
WS_FIELD_ABSENCES: Final = "absences"

# Inhalt der Antworten und Deltas
WIRE_PERSONS: Final = "persons"
WIRE_TASKS: Final = "tasks"
WIRE_SCHEDULES: Final = "schedules"
WIRE_ASSIGNMENTS: Final = "assignments"
WIRE_ROUNDS: Final = "rounds"
WIRE_ORIGIN: Final = "origin"
WIRE_STARTED_AT: Final = "started_at"
WIRE_TOTAL: Final = "total"
WIRE_DONE: Final = "done"
WIRE_PANEL_ROUNDS: Final = "panel_rounds"
WIRE_SETTINGS: Final = "settings"
WIRE_UPSERT: Final = "upsert"
WIRE_REMOVE: Final = "remove"
WIRE_NOW: Final = "now"
WIRE_ENTRIES: Final = "entries"
WIRE_NEXT_OFFSET: Final = "next_offset"
WIRE_ROUND: Final = "round"
WIRE_RESULT: Final = "result"
WIRE_RESULTS: Final = "results"
WIRE_PANEL_ROUND: Final = "panel_round"
WIRE_EXPIRES_AT: Final = "expires_at"
WIRE_PENDING: Final = "pending_task_ids"
WIRE_NEXT_RUN: Final = "next_run"
WIRE_PRESENT: Final = "present"

# Namen der Ressourcen in Fehlern (Platzhalter `resource`)
RESOURCE_PERSON: Final = "person"
RESOURCE_TASK: Final = "task"
RESOURCE_SCHEDULE: Final = "schedule"
RESOURCE_ASSIGNMENT: Final = "assignment"
RESOURCE_ROUND: Final = "round"
RESOURCE_PANEL_ROUND: Final = "panel_round"
RESOURCE_SUBSCRIPTION: Final = "subscription"

# Platzhalter in Fehlermeldungen
PH_SECONDS: Final = "seconds"

# Fehlerschlüssel der Benachrichtigung
ERR_NOTIFY_TARGET: Final = "notify_target_invalid"
ERR_NOTIFY_FAILED: Final = "notify_failed"
