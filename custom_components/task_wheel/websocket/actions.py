"""Befehle zum Erledigen, Tauschen und Auslosen (jeder angemeldete Benutzer)."""

from typing import Final

from ..application.views import panel_round_view
from ..application.wire import to_json, to_wire
from ..const.events import (
    WS_ASSIGNMENT_COMPLETE,
    WS_ASSIGNMENT_SKIP,
    WS_ASSIGNMENT_SWAP,
    WS_DRAW_BEGIN,
    WS_DRAW_CANCEL,
    WS_DRAW_COMMIT,
    WS_DRAW_PREVIEW,
    WS_DRAW_SPIN,
    WS_DRAW_SPIN_REST,
    WS_ROUND_DELETE,
)
from ..const.keys import (
    WIRE_PANEL_ROUND,
    WIRE_RESULT,
    WIRE_RESULTS,
    WS_FIELD_ASSIGNMENT_ID,
    WS_FIELD_PANEL_ROUND_ID,
    WS_FIELD_ROUND_ID,
    WS_FIELD_SCHEDULE_ID,
    WS_FIELD_TO_PERSON_ID,
)
from .command import Access, Command, Reply, Request
from .schemas import ID, required_fields

_ASSIGNMENT: Final = required_fields((WS_FIELD_ASSIGNMENT_ID, ID))
_SWAP: Final = required_fields((WS_FIELD_ASSIGNMENT_ID, ID), (WS_FIELD_TO_PERSON_ID, ID))
_SCHEDULE: Final = required_fields((WS_FIELD_SCHEDULE_ID, ID))
_ROUND: Final = required_fields((WS_FIELD_ROUND_ID, ID))
_PANEL_ROUND: Final = required_fields((WS_FIELD_PANEL_ROUND_ID, ID))


def _complete(request: Request) -> Reply:
    """Erledigt die Zuteilung."""
    done = request.data.assignments.complete(request.params[WS_FIELD_ASSIGNMENT_ID], request.now)
    return Reply(to_json(done))


def _skip(request: Request) -> Reply:
    """Markiert die Zuteilung als „Bleibt unerledigt“."""
    skipped = request.data.assignments.skip(request.params[WS_FIELD_ASSIGNMENT_ID])
    return Reply(to_json(skipped))


def _swap(request: Request) -> Reply:
    """Tauscht die Zuteilung gegen einen Joker."""
    params = request.params
    swapped = request.data.swaps.swap(
        params[WS_FIELD_ASSIGNMENT_ID], params[WS_FIELD_TO_PERSON_ID], request.now
    )
    return Reply(to_json(swapped))


def _delete_round(request: Request) -> Reply:
    """Löscht die Auslosung samt Zuteilungen; Punkte und Statistik werden zurückgerechnet."""
    request.data.rounds.delete(request.params[WS_FIELD_ROUND_ID])
    return Reply()


def _view(request: Request) -> dict[str, object]:
    """Stand der Panel-Runde nach der Änderung."""
    panel_round = request.data.draws.get(request.params[WS_FIELD_PANEL_ROUND_ID], request.now)
    return panel_round_view(panel_round)


def _begin(request: Request) -> Reply:
    """Beginnt eine Panel-Runde für den Zeitplan."""
    panel_round = request.data.draws.begin(
        request.params[WS_FIELD_SCHEDULE_ID], request.now, is_admin=request.is_admin
    )
    return Reply(panel_round_view(panel_round))


def _preview(request: Request) -> Reply:
    """Das Rad der nächsten Aufgabe, ohne zu ziehen."""
    result = request.data.draws.preview(request.params[WS_FIELD_PANEL_ROUND_ID], request.now)
    return Reply({WIRE_RESULT: to_wire(result)})


def _spin(request: Request) -> Reply:
    """Zieht die nächste Aufgabe; das Ergebnis bestimmt das Backend."""
    result = request.data.draws.spin(request.params[WS_FIELD_PANEL_ROUND_ID], request.now)
    return Reply({WIRE_RESULT: to_wire(result), WIRE_PANEL_ROUND: _view(request)})


def _spin_rest(request: Request) -> Reply:
    """Zieht alle übrigen Aufgaben."""
    results = request.data.draws.spin_rest(request.params[WS_FIELD_PANEL_ROUND_ID], request.now)
    return Reply({WIRE_RESULTS: to_wire(results), WIRE_PANEL_ROUND: _view(request)})


def _commit(request: Request) -> Reply:
    """Schließt die Panel-Runde ab und speichert sie."""
    round_ = request.data.draws.commit(request.params[WS_FIELD_PANEL_ROUND_ID], request.now)
    return Reply(to_json(round_))


def _cancel(request: Request) -> Reply:
    """Verwirft die Panel-Runde (nach dem ersten Ziehen nur für Administratoren)."""
    request.data.draws.cancel(
        request.params[WS_FIELD_PANEL_ROUND_ID], request.now, is_admin=request.is_admin
    )
    return Reply()


COMMANDS: Final = (
    Command(WS_ASSIGNMENT_COMPLETE, _ASSIGNMENT, _complete, mutates=True),
    Command(WS_ASSIGNMENT_SKIP, _ASSIGNMENT, _skip, mutates=True),
    Command(WS_ASSIGNMENT_SWAP, _SWAP, _swap, mutates=True),
    Command(WS_ROUND_DELETE, _ROUND, _delete_round, access=Access.ADMIN, mutates=True),
    Command(WS_DRAW_BEGIN, _SCHEDULE, _begin, mutates=True),
    Command(WS_DRAW_PREVIEW, _PANEL_ROUND, _preview),
    Command(WS_DRAW_SPIN, _PANEL_ROUND, _spin, mutates=True),
    Command(WS_DRAW_SPIN_REST, _PANEL_ROUND, _spin_rest, mutates=True),
    Command(WS_DRAW_COMMIT, _PANEL_ROUND, _commit, mutates=True),
    Command(WS_DRAW_CANCEL, _PANEL_ROUND, _cancel, mutates=True),
)
