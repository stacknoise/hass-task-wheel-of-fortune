"""Lesebefehle: Snapshot, Abonnement mit Deltas, Historie, Statistik (angemeldete Benutzer)."""

from typing import Any, Final

import voluptuous as vol

from ..application.views import history_entry_view
from ..application.wire import to_json
from ..const.defaults import (
    DEFAULT_HISTORY_PAGE_SIZE,
    DEFAULT_PREVIEW_WEEKS,
    DEFAULT_STATISTICS_MONTHS,
    DEFAULT_STATISTICS_WEEKS,
)
from ..const.events import (
    WS_AVAILABILITY_PREVIEW,
    WS_DECISIONS_LIST,
    WS_HISTORY_LIST,
    WS_SNAPSHOT,
    WS_STATISTICS_GET,
    WS_SUBSCRIBE,
)
from ..const.keys import (
    WIRE_ENTRIES,
    WIRE_NEXT_OFFSET,
    WIRE_PRESENT,
    WS_FIELD_ABSENCES,
    WS_FIELD_KIND,
    WS_FIELD_LIMIT,
    WS_FIELD_MONTHS,
    WS_FIELD_OFFSET,
    WS_FIELD_PERSON_ID,
    WS_FIELD_SCHEDULE_ID,
    WS_FIELD_SINCE,
    WS_FIELD_STATUS,
    WS_FIELD_TASK_ID,
    WS_FIELD_UNTIL,
    WS_FIELD_WEEKS,
)
from ..const.limits import MAX_ABSENCES_PER_PERSON
from ..domain.availability import PersonAvailability
from ..domain.decisions import DecisionFilter
from ..domain.enums import AssignmentStatus, DecisionKind
from ..domain.history import HistoryFilter
from ..domain.models import decode_absence
from ..domain.serialization import enum_of, optional, to_datetime
from .command import Command, Params, Reply, Request
from .schemas import ID, INTEGER, ISO_TEXT, bounded, optional_fields, required_fields

_DECODE_STATUS: Final = optional(enum_of(AssignmentStatus))
_DECODE_TIME: Final = optional(to_datetime)
_DECODE_KIND: Final = optional(enum_of(DecisionKind))

_HISTORY_FIELDS: Final[dict[Any, Any]] = optional_fields(
    (WS_FIELD_SCHEDULE_ID, ID),
    (WS_FIELD_PERSON_ID, ID),
    (WS_FIELD_TASK_ID, ID),
    (WS_FIELD_STATUS, ID),
    (WS_FIELD_SINCE, ISO_TEXT),
    (WS_FIELD_UNTIL, ISO_TEXT),
    (WS_FIELD_OFFSET, INTEGER),
    (WS_FIELD_LIMIT, INTEGER),
)
_DECISION_FIELDS: Final[dict[Any, Any]] = optional_fields(
    (WS_FIELD_SCHEDULE_ID, ID),
    (WS_FIELD_PERSON_ID, ID),
    (WS_FIELD_TASK_ID, ID),
    (WS_FIELD_KIND, ID),
    (WS_FIELD_SINCE, ISO_TEXT),
    (WS_FIELD_UNTIL, ISO_TEXT),
    (WS_FIELD_OFFSET, INTEGER),
    (WS_FIELD_LIMIT, INTEGER),
)
_STATISTICS_FIELDS: Final[dict[Any, Any]] = optional_fields(
    (WS_FIELD_MONTHS, INTEGER), (WS_FIELD_WEEKS, INTEGER)
)
_PREVIEW_FIELDS: Final[dict[Any, Any]] = {
    **required_fields(
        (WS_FIELD_ABSENCES, vol.All([bounded], vol.Length(max=MAX_ABSENCES_PER_PERSON)))
    ),
    **optional_fields((WS_FIELD_WEEKS, INTEGER)),
}


def _snapshot(request: Request) -> Reply:
    """Der aktuelle Gesamtstand."""
    return Reply(request.data.live.snapshot().to_wire())


def _subscribe(request: Request) -> Reply:
    """Antwortet mit dem Stand; danach folgen nur noch Deltas je Objekt über `push`."""
    snapshot, unsubscribe = request.data.live.subscribe(request.push)
    return Reply(snapshot.to_wire(), on_close=unsubscribe)


def history_filter(params: Params) -> HistoryFilter:
    """Filter aus den Feldern der Nachricht (Zeiten als ISO-Text, Status als Schlüssel)."""
    return HistoryFilter(
        schedule_id=params.get(WS_FIELD_SCHEDULE_ID),
        person_id=params.get(WS_FIELD_PERSON_ID),
        task_id=params.get(WS_FIELD_TASK_ID),
        status=_DECODE_STATUS(params.get(WS_FIELD_STATUS)),
        since=_DECODE_TIME(params.get(WS_FIELD_SINCE)),
        until=_DECODE_TIME(params.get(WS_FIELD_UNTIL)),
    )


def _history_list(request: Request) -> Reply:
    """Eine Seite der Historie, neueste zuerst."""
    params = request.params
    page = request.data.history_service.page(
        history_filter(params),
        params.get(WS_FIELD_OFFSET, 0),
        params.get(WS_FIELD_LIMIT, DEFAULT_HISTORY_PAGE_SIZE),
    )
    entries = [history_entry_view(entry) for entry in page.entries]
    return Reply({WIRE_ENTRIES: entries, WIRE_NEXT_OFFSET: page.next_offset})


def decision_filter(params: Params) -> DecisionFilter:
    """Filter des Entscheidungslogs aus den Feldern der Nachricht."""
    return DecisionFilter(
        schedule_id=params.get(WS_FIELD_SCHEDULE_ID),
        person_id=params.get(WS_FIELD_PERSON_ID),
        task_id=params.get(WS_FIELD_TASK_ID),
        kind=_DECODE_KIND(params.get(WS_FIELD_KIND)),
        since=_DECODE_TIME(params.get(WS_FIELD_SINCE)),
        until=_DECODE_TIME(params.get(WS_FIELD_UNTIL)),
    )


def _decisions_list(request: Request) -> Reply:
    """Eine Seite des Entscheidungslogs, neueste zuerst (für alle sichtbar)."""
    params = request.params
    page = request.data.decision_service.page(
        decision_filter(params),
        params.get(WS_FIELD_OFFSET, 0),
        params.get(WS_FIELD_LIMIT, DEFAULT_HISTORY_PAGE_SIZE),
    )
    return Reply(
        {
            WIRE_ENTRIES: [to_json(entry) for entry in page.entries],
            WIRE_NEXT_OFFSET: page.next_offset,
        }
    )


def _statistics_get(request: Request) -> Reply:
    """Auswertung der letzten Monate und Wochen."""
    params = request.params
    report = request.data.statistics.report(
        request.now,
        params.get(WS_FIELD_MONTHS, DEFAULT_STATISTICS_MONTHS),
        params.get(WS_FIELD_WEEKS, DEFAULT_STATISTICS_WEEKS),
    )
    return Reply(to_json(report))


def _availability_preview(request: Request) -> Reply:
    """Anwesenheit der nächsten Wochen für einen noch nicht gespeicherten Satz von Regeln.

    Die Regeln rechnet nur das Backend aus (eine Quelle der Wahrheit); das Panel zeigt das Ergebnis.
    """
    params = request.params
    rules = tuple(decode_absence(item) for item in params[WS_FIELD_ABSENCES])
    days = PersonAvailability.of_rules(rules).week_preview(
        request.now.date(), params.get(WS_FIELD_WEEKS, DEFAULT_PREVIEW_WEEKS)
    )
    return Reply({WIRE_PRESENT: [entry.present for entry in days]})


COMMANDS: Final = (
    Command(WS_SNAPSHOT, {}, _snapshot),
    Command(WS_SUBSCRIBE, {}, _subscribe, subscribes=True),
    Command(WS_HISTORY_LIST, _HISTORY_FIELDS, _history_list),
    Command(WS_DECISIONS_LIST, _DECISION_FIELDS, _decisions_list),
    Command(WS_STATISTICS_GET, _STATISTICS_FIELDS, _statistics_get),
    Command(WS_AVAILABILITY_PREVIEW, _PREVIEW_FIELDS, _availability_preview),
)
