"""Standardwerte und Bezeichner der Integration."""

import datetime as dt
from typing import Final

from .limits import RETENTION_MIN

DOMAIN: Final = "task_wheel"
INTEGRATION_NAME: Final = "Task Wheel of Fortune"
INTEGRATION_NAME_DE: Final = "Aufgaben-Glücksrad"
GERMAN_LANGUAGE_PREFIX: Final = "de"

# Einstellungen (KONZEPT §4, §11)
DEFAULT_JOKERS_PER_MONTH: Final = 2
DEFAULT_FAIRNESS_WINDOW_DAYS: Final = 30
DEFAULT_HISTORY_RETENTION_DAYS: Final = RETENTION_MIN
DEFAULT_DECISION_RETENTION_DAYS: Final = 7
DEFAULT_LATE_POINTS_FACTOR: Final = 1.0
DEFAULT_MISSED_POINTS_FACTOR: Final = 0.0
DEFAULT_MISSED_GRACE_HOURS: Final = 24
DEFAULT_PANEL_ADMIN_ONLY: Final = False

# Personen, Aufgaben, Zeitpläne
DEFAULT_PERSON_COLOR: Final = "#4f8cff"
DEFAULT_TASK_POINTS: Final = 1
DEFAULT_DEADLINE_DAYS: Final = 7
DEFAULT_DEADLINE_TIME: Final = dt.time(10, 0)
DEFAULT_EVERY_N_WEEKS: Final = 1
DEFAULT_INTERVAL_TOLERANCE: Final = 0
DEFAULT_PERIOD_EVERY: Final = 1

# Belastbarkeit einer Person als Faktor der Kapazität
LOAD_FACTOR_FULL: Final = 1.0
LOAD_FACTOR_HALF: Final = 0.5
LOAD_FACTOR_PAUSED: Final = 0.0

# Persistenz: Verzögerung des gebündelten Speicherns (Sekunden)
STORE_SAVE_DELAY_SECONDS: Final = 10

# Anwesenheit vorschauen (Personen-Ansicht zeigt die nächsten vier Wochen)
DEFAULT_PREVIEW_WEEKS: Final = 4

# Fairness-Gewichtung (KONZEPT §5.3)
FAIRNESS_DAMPING: Final = 1.0
WEIGHT_MIN: Final = 0.005
WEIGHT_MAX: Final = 1.0
UNIFORM_WEIGHT: Final = 1.0

# Runden im Panel (KONZEPT §5.1): so lange bleibt eine offene Panel-Runde gültig
PANEL_ROUND_TIMEOUT_MINUTES: Final = 15

# Erinnerungen für Zeitpläne „nur manuell“ werden täglich zu dieser vollen Stunde geprüft
REMINDER_HOUR: Final = 9

# Täglicher Wartungslauf (verpasste Zuteilungen markieren, alte Runden löschen), nachts
MAINTENANCE_HOUR: Final = 3

# Statistik und Historie
DEFAULT_STATISTICS_MONTHS: Final = 1
DEFAULT_STATISTICS_WEEKS: Final = 8
DEFAULT_GOAL_WINDOWS: Final = 4
DEFAULT_HISTORY_PAGE_SIZE: Final = 50
MONTH_KEY_FORMAT: Final = "%Y-%m"
