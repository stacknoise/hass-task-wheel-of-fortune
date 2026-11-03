"""Konstanten der Benachrichtigungen (KONZEPT §3.2, §8)."""

import re
from typing import Final

# Home-Assistant-Dienste und -Felder
NOTIFY_DOMAIN: Final = "notify"
NOTIFY_SEND_MESSAGE: Final = "send_message"
NOTIFY_FIELD_ENTITY: Final = "entity_id"
NOTIFY_FIELD_TITLE: Final = "title"
NOTIFY_FIELD_MESSAGE: Final = "message"
# Nur Ziele der Domäne `notify` sind erlaubt; so lässt sich kein fremder Dienst aufrufen
NOTIFY_TARGET_PATTERN: Final = re.compile(rf"^{NOTIFY_DOMAIN}\.[a-z0-9_]+$")
NOTIFY_TARGET_SEPARATOR: Final = "."

# Grenzen
NOTIFY_TIMEOUT_SECONDS: Final = 10
NOTIFY_MESSAGE_MAX_LENGTH: Final = 1000
NOTIFY_ELLIPSIS: Final = "…"

# Texte: Dateien im Verzeichnis `texts/`, Sprachen nach `hass.config.language`
TEXTS_DIRECTORY: Final = "texts"
TEXTS_FILE_SUFFIX: Final = ".json"
TEXTS_FALLBACK_LANGUAGE: Final = "en"
# Sprachcode wird Teil eines Dateinamens: nur kurze Codes wie `de` oder `pt-BR` sind zulässig
TEXTS_LANGUAGE_PATTERN: Final = re.compile(r"^[a-z]{2,3}(-[A-Za-z]{2,4})?$")
TEXT_COMMON: Final = "common"
TEXT_ROUND_DRAWN: Final = "round_drawn"
TEXT_SWAPPED: Final = "swapped"
TEXT_REMINDER: Final = "reminder"
TEXT_TITLE: Final = "title"
TEXT_MESSAGE: Final = "message"
TEXT_PERSON_LINE: Final = "person_line"
TEXT_TASK_ITEM: Final = "task_item"
TEXT_DATE_FORMAT: Final = "date_format"
TEXT_LIST_SEPARATOR: Final = "list_separator"
TEXT_LINE_SEPARATOR: Final = "line_separator"
