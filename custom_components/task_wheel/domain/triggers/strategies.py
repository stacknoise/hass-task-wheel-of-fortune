"""Auslöser-Strategien: wiederkehrend, einmalig, nur manuell."""

import datetime as dt

from ...const.limits import ONE_DAY, ONE_WEEK, TRIGGER_LOOKAHEAD_DAYS, WEEKDAY_COUNT
from ..models import ManualTrigger, OnceTrigger, Recurring
from ..rules.periods import week_start
from ..validation import ensure_aware


class RecurringStrategy:
    """An den gewählten Wochentagen zur Uhrzeit; jede n-te Woche (ab Ankerwoche) oder monatlich.

    „Monatlich“ löst am **ersten** gewählten Wochentag jedes Monats aus.
    """

    def __init__(self, config: Recurring) -> None:
        """Übernimmt die Konfiguration."""
        self._config = config

    def next_fire(self, after: dt.datetime) -> dt.datetime | None:
        """Sucht Tag für Tag (höchstens `TRIGGER_LOOKAHEAD_DAYS`) den nächsten Zeitpunkt."""
        ensure_aware("after", after)
        first = after.date()
        moments = (
            dt.datetime.combine(first + offset * ONE_DAY, self._config.time, tzinfo=after.tzinfo)
            for offset in range(TRIGGER_LOOKAHEAD_DAYS + 1)
        )
        return next((m for m in moments if m > after and self._matches(m.date())), None)

    def _matches(self, day: dt.date) -> bool:
        """Wochentag gewählt und (monatlich: erste Woche des Monats | sonst: Rhythmuswoche)."""
        config = self._config
        if day.weekday() not in config.weekdays:
            return False
        if config.monthly:
            return self._is_first_selected_day(day)
        return self._week_index(day) % config.every_n_weeks == 0

    def _is_first_selected_day(self, day: dt.date) -> bool:
        """Ist `day` der erste gewählte Wochentag des Monats (ein Termin je Monat)."""
        earlier = (day.replace(day=n) for n in range(1, min(day.day, WEEKDAY_COUNT + 1)))
        return day.day <= WEEKDAY_COUNT and all(
            d.weekday() not in self._config.weekdays for d in earlier
        )

    def _week_index(self, day: dt.date) -> int:
        """Wochen seit der Ankerwoche (ohne Anker: 0)."""
        anchor = self._config.anchor or day
        return (week_start(day) - week_start(anchor)) // ONE_WEEK


class OnceStrategy:
    """Genau ein Zeitpunkt; danach nichts mehr."""

    def __init__(self, config: OnceTrigger) -> None:
        """Übernimmt die Konfiguration."""
        self._config = config

    def next_fire(self, after: dt.datetime) -> dt.datetime | None:
        """Der Zeitpunkt, solange er noch in der Zukunft liegt."""
        ensure_aware("after", after)
        return self._config.at if self._config.at > after else None


class ManualStrategy:
    """Kein Zeitgeber: wird nur von Hand (Panel, Dienst, Button) ausgelöst."""

    def __init__(self, _config: ManualTrigger) -> None:
        """Nimmt die Konfiguration entgegen (die Erinnerung liest `reminder.py` selbst)."""

    def next_fire(self, after: dt.datetime) -> dt.datetime | None:
        """Nie."""
        ensure_aware("after", after)
        return None
