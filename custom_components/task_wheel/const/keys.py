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

# Dienstdaten (KONZEPT §6.1)
ATTR_SCHEDULE: Final = "schedule"
ATTR_ANIMATE_ON: Final = "animate_on"
ATTR_ASSIGNMENT_ID: Final = "assignment_id"
ATTR_PERSON: Final = "person"
ATTR_TASK: Final = "task"
ATTR_TO_PERSON: Final = "to_person"
ATTR_START: Final = "start"
ATTR_END: Final = "end"

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
