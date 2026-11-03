"""Schlüssel für Speicher, Serialisierung, Dienste und Fehlermeldungen."""

from typing import Final

from .defaults import DOMAIN

# Speicher
STORE_CONFIG: Final = f"{DOMAIN}.config"
STORE_HISTORY: Final = f"{DOMAIN}.history"
STORE_VERSION: Final = 1
STORE_MINOR_VERSION: Final = 1

KEY_PERSONS: Final = "persons"
KEY_TASKS: Final = "tasks"
KEY_SCHEDULES: Final = "schedules"
KEY_SETTINGS: Final = "settings"
KEY_ROUNDS: Final = "rounds"
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
ERR_STORAGE_CORRUPT: Final = "storage_corrupt"
ERR_STORAGE_VERSION: Final = "storage_version_unsupported"

# Fehlerschlüssel für Statusübergänge und Tausch
ERR_INVALID_TRANSITION: Final = "invalid_transition"
ERR_SWAP_DISABLED: Final = "swap_disabled"
ERR_SWAP_SAME_PERSON: Final = "swap_same_person"
ERR_SWAP_NOT_ALLOWED: Final = "swap_person_not_allowed"
ERR_SWAP_PAUSED: Final = "swap_person_paused"
ERR_SWAP_ABSENT: Final = "swap_person_absent"
ERR_NO_JOKERS: Final = "no_jokers_left"

# Fehlerschlüssel für Runden und Zeitpläne
ERR_SCHEDULE_DISABLED: Final = "schedule_disabled"
ERR_SCHEDULE_ARCHIVED: Final = "schedule_archived"
ERR_ROUND_INCOMPLETE: Final = "round_incomplete"
ERR_ROUND_COMPLETE: Final = "round_complete"

# Fehlerschlüssel der Dienste
ERR_NOT_LOADED: Final = "not_loaded"
ERR_TARGET_REQUIRED: Final = "target_required"

# Fehlerschlüssel der Benachrichtigung
ERR_NOTIFY_TARGET: Final = "notify_target_invalid"
ERR_NOTIFY_FAILED: Final = "notify_failed"
