"""Aufzählungen der Domäne (StrEnum, Werte sind Speicher- und API-Format)."""

from enum import StrEnum

from ..const.defaults import LOAD_FACTOR_FULL, LOAD_FACTOR_HALF, LOAD_FACTOR_PAUSED


class Load(StrEnum):
    """Belastbarkeit einer Person."""

    FULL = "full"
    HALF = "half"
    PAUSED = "paused"

    @property
    def factor(self) -> float:
        """Faktor der Kapazität (voll 1,0 · halb 0,5 · pausiert 0)."""
        return _LOAD_FACTORS[self]


_LOAD_FACTORS = {
    Load.FULL: LOAD_FACTOR_FULL,
    Load.HALF: LOAD_FACTOR_HALF,
    Load.PAUSED: LOAD_FACTOR_PAUSED,
}


class NotifyTargetKind(StrEnum):
    """Art des Benachrichtigungsziels einer Person."""

    NOTIFY_ENTITY = "notify_entity"
    NOTIFY_SERVICE = "notify_service"
    NONE = "none"


class AbsenceKind(StrEnum):
    """Art einer Anwesenheitsregel."""

    ONCE = "once"
    WEEKLY_DAYS = "weekly_days"
    WEEK_RHYTHM = "week_rhythm"


class FrequencyKind(StrEnum):
    """Art einer Häufigkeitsregel."""

    EVERY_ROUND = "every_round"
    MAX_PER_PERIOD = "max_per_period"
    INTERVAL = "interval"


class Period(StrEnum):
    """Zeitraum einer Häufigkeitsregel."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class TriggerKind(StrEnum):
    """Art eines Zeitplan-Auslösers."""

    RECURRING = "recurring"
    ONCE = "once"
    MANUAL = "manual"


class AfterOnce(StrEnum):
    """Verhalten eines einmaligen Zeitplans nach der Auslösung."""

    KEEP_MANUAL = "keep_manual"
    ARCHIVE = "archive"
    DELETE = "delete"


class RoundOrigin(StrEnum):
    """Wer eine Runde ausgelöst hat."""

    AUTO = "auto"
    MANUAL = "manual"
    SERVICE = "service"


class AssignmentStatus(StrEnum):
    """Status einer Zuteilung."""

    OPEN = "open"
    ON_TIME = "on_time"
    LATE = "late"
    SWAPPED = "swapped"
    MISSED = "missed"
    SKIPPED = "skipped"


class AssignmentAction(StrEnum):
    """Aktion, die den Status einer Zuteilung ändert (Schlüssel der Übergangstabelle)."""

    COMPLETE_ON_TIME = "complete_on_time"
    COMPLETE_LATE = "complete_late"
    MISS = "miss"
    SWAP = "swap"
    SKIP = "skip"


class WeightingKind(StrEnum):
    """Art der Gewichtung bei der Ziehung."""

    FAIRNESS = "fairness"
    UNIFORM = "uniform"


class ExclusionReason(StrEnum):
    """Grund, warum eine Person nicht im Rad einer Aufgabe ist (Anzeige „Wer ist im Rad?“)."""

    PAUSED = "paused"
    ABSENT = "absent"
    REPEAT = "no_repeat"
    TAKEN = "taken"
