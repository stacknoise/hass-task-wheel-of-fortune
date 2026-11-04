"""Grenzwerte für Eingaben und Ressourcen (Sicherheit, KONZEPT §8)."""

import datetime as dt
import re
from typing import Final

# Ressourcen
MAX_PERSONS: Final = 30
MAX_TASKS: Final = 100
MAX_SCHEDULES: Final = 30
MAX_OPEN_PANEL_ROUNDS: Final = 5
MAX_ABSENCES_PER_PERSON: Final = 20
MAX_TASKS_PER_SCHEDULE: Final = MAX_TASKS
MAX_ASSIGNMENTS_PER_ROUND: Final = MAX_TASKS
MAX_STORED_ROUNDS: Final = 20000
# Mindestabstand zwischen zwei von Hand oder per Dienst ausgelösten Runden desselben Zeitplans
# (Schutz davor, den Verlauf zu fluten); automatische Auslosungen sind nicht betroffen
DRAW_MIN_INTERVAL_SECONDS: Final = 30

# Zeichenketten
NAME_MIN_LENGTH: Final = 1
NAME_MAX_LENGTH: Final = 60
SLUG_MAX_LENGTH: Final = 64
ID_MAX_LENGTH: Final = 64
NOTIFY_TARGET_MAX_LENGTH: Final = 255
# Kennung eines Home-Assistant-Bereichs (Raum)
AREA_ID_MAX_LENGTH: Final = 255
# Räume (Bereiche), die einer Aufgabe zugewiesen sein können
MAX_AREAS_PER_TASK: Final = 20
# Referenz aus einem Dienst: Kennung, Kurzname oder Name
REF_MIN_LENGTH: Final = 1
REF_MAX_LENGTH: Final = max(ID_MAX_LENGTH, SLUG_MAX_LENGTH, NAME_MAX_LENGTH)
COLOR_PATTERN: Final = re.compile(r"^#[0-9a-f]{6}$")
SLUG_PATTERN: Final = re.compile(r"^[a-z0-9_]+$")

# Zeit
WEEKDAY_MIN: Final = 0
WEEKDAY_MAX: Final = 6
WEEKDAY_COUNT: Final = WEEKDAY_MAX - WEEKDAY_MIN + 1
RHYTHM_CYCLE_MIN: Final = 1
RHYTHM_CYCLE_MAX: Final = 8
RECURRENCE_INTERVAL_MIN: Final = 1
RECURRENCE_INTERVAL_MAX: Final = 52
EVERY_N_WEEKS_MIN: Final = 1
EVERY_N_WEEKS_MAX: Final = 52
REMIND_AFTER_DAYS_MIN: Final = 1
REMIND_AFTER_DAYS_MAX: Final = 365
# So weit schaut ein wiederkehrender Auslöser höchstens voraus (längster Rhythmus plus eine Woche)
TRIGGER_LOOKAHEAD_DAYS: Final = EVERY_N_WEEKS_MAX * WEEKDAY_COUNT + WEEKDAY_COUNT

# Aufgaben und Häufigkeit
POINTS_MIN: Final = 1
POINTS_MAX: Final = 100
DUE_DAYS_MIN: Final = 1
DUE_DAYS_MAX: Final = 365
PERIOD_COUNT_MIN: Final = 1
PERIOD_COUNT_MAX: Final = 50
PERIOD_EVERY_MIN: Final = 1
PERIOD_EVERY_MAX: Final = 12
# Längster Monat; begrenzt, wie weit ein Zeitraum von `PERIOD_EVERY_MAX` Monaten zurückreicht
PERIOD_MAX_DAYS: Final = 31
INTERVAL_DAYS_MIN: Final = 1
INTERVAL_DAYS_MAX: Final = 365
INTERVAL_TOLERANCE_MIN: Final = 0

# Zuteilungen
CHANCE_MIN: Final = 0.0
CHANCE_MAX: Final = 1.0

# Einstellungen
JOKERS_MIN: Final = 0
JOKERS_MAX: Final = 31
FAIRNESS_WINDOW_MIN: Final = 1
FAIRNESS_WINDOW_MAX: Final = 365
RETENTION_MAX: Final = 3650
LATE_FACTOR_MIN: Final = 0.0
LATE_FACTOR_MAX: Final = 1.0
MISSED_FACTOR_MIN: Final = -1.0
MISSED_FACTOR_MAX: Final = 0.0
GRACE_HOURS_MIN: Final = 0
GRACE_HOURS_MAX: Final = 168

# Zuteilungen: so lange kann eine Zuteilung höchstens offen sein (Frist plus Kulanzzeit plus ein
# Sicherheitstag, damit Sommerzeit-Verschiebungen sie nicht aus dem Suchfenster fallen lassen)
HOURS_PER_DAY: Final = 24
OPEN_ASSIGNMENT_SAFETY_DAYS: Final = 1
OPEN_ASSIGNMENT_MAX_AGE_DAYS: Final = (
    DUE_DAYS_MAX + GRACE_HOURS_MAX // HOURS_PER_DAY + OPEN_ASSIGNMENT_SAFETY_DAYS
)

# Verlauf, der für Häufigkeitsregeln und Fairness-Fenster einer Runde herangezogen wird
RECENT_HISTORY_DAYS: Final = max(
    INTERVAL_DAYS_MAX, FAIRNESS_WINDOW_MAX, PERIOD_EVERY_MAX * PERIOD_MAX_DAYS
)

# Aufbewahrung des Verlaufs: mindestens so lange, wie Regeln, Fairness und offene Zuteilungen ihn
# brauchen (sonst gälten Häufigkeitsregeln still nicht mehr oder offene Zuteilungen verschwänden)
RETENTION_MIN: Final = max(RECENT_HISTORY_DAYS, OPEN_ASSIGNMENT_MAX_AGE_DAYS)

# Zeitspannen
ONE_DAY: Final = dt.timedelta(days=1)
ONE_WEEK: Final = dt.timedelta(days=WEEKDAY_COUNT)
DRAW_MIN_INTERVAL: Final = dt.timedelta(seconds=DRAW_MIN_INTERVAL_SECONDS)
OPEN_ASSIGNMENT_MAX_AGE: Final = dt.timedelta(days=OPEN_ASSIGNMENT_MAX_AGE_DAYS)
RECENT_HISTORY: Final = dt.timedelta(days=RECENT_HISTORY_DAYS)

# Anwesenheit
PREVIEW_WEEKS_MIN: Final = 1
PREVIEW_WEEKS_MAX: Final = 12
AVAILABILITY_WINDOW_MAX_DAYS: Final = DUE_DAYS_MAX + 1

# Statistik und Historie (KONZEPT §6)
MONTHS_PER_YEAR: Final = 12
STATISTICS_MONTHS_MIN: Final = 1
STATISTICS_MONTHS_MAX: Final = MONTHS_PER_YEAR
STATISTICS_WEEKS_MIN: Final = 1
STATISTICS_WEEKS_MAX: Final = 52
RELIABILITY_MIN_CLOSED: Final = 3
HISTORY_PAGE_SIZE_MIN: Final = 1
HISTORY_PAGE_SIZE_MAX: Final = 200
HISTORY_OFFSET_MAX: Final = MAX_STORED_ROUNDS

# WebSocket-API (KONZEPT §6.4, §8): Grenzen für Nachrichten des Panels
WS_STRING_MAX_LENGTH: Final = max(NOTIFY_TARGET_MAX_LENGTH, AREA_ID_MAX_LENGTH, NAME_MAX_LENGTH)
WS_LIST_MAX_ITEMS: Final = max(MAX_TASKS, MAX_PERSONS)
WS_OBJECT_MAX_KEYS: Final = 32
WS_MAX_DEPTH: Final = 4
WS_ISO_MAX_LENGTH: Final = 40
WS_MESSAGE_ID_MIN: Final = 1
MAX_SUBSCRIPTIONS: Final = 50
