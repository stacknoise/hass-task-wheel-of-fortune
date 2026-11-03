"""Historie: gefilterte, seitenweise Abfrage der Runden (KONZEPT §6)."""

import datetime as dt
from dataclasses import dataclass
from itertools import islice
from typing import Final

from ..const.defaults import DEFAULT_HISTORY_PAGE_SIZE
from ..const.limits import HISTORY_OFFSET_MAX, HISTORY_PAGE_SIZE_MAX, HISTORY_PAGE_SIZE_MIN
from ..domain.history import HistoryFilter
from ..domain.models import Assignment, Round
from ..domain.validation import ensure_range
from .protocols import HistoryRepository

_FIELD_LIMIT = "limit"
_FIELD_OFFSET = "offset"
_EARLIEST: Final = dt.datetime.min.replace(tzinfo=dt.UTC)


@dataclass(slots=True, frozen=True)
class HistoryEntry:
    """Eine Runde mit den Zuteilungen, die zum Filter passen."""

    round: Round
    assignments: tuple[Assignment, ...]


@dataclass(slots=True, frozen=True)
class HistoryPage:
    """Eine Seite der Historie (neueste zuerst); `next_offset` ist leer auf der letzten Seite."""

    entries: tuple[HistoryEntry, ...]
    next_offset: int | None


class HistoryService:
    """Liest die Historie über das Repository; Filter und Seitengröße sind begrenzt."""

    def __init__(self, history: HistoryRepository) -> None:
        """Hält das Repository."""
        self._history = history

    def page(
        self,
        query: HistoryFilter | None = None,
        offset: int = 0,
        limit: int = DEFAULT_HISTORY_PAGE_SIZE,
    ) -> HistoryPage:
        """Liefert bis zu `limit` passende Runden ab dem `offset`-ten Treffer.

        Raises:
            ValidationError: `offset` oder `limit` außerhalb des erlaubten Bereichs.
        """
        ensure_range(_FIELD_LIMIT, limit, HISTORY_PAGE_SIZE_MIN, HISTORY_PAGE_SIZE_MAX)
        ensure_range(_FIELD_OFFSET, offset, 0, HISTORY_OFFSET_MAX)
        flt = query or HistoryFilter()
        rounds = self._history.rounds_since(flt.since or _EARLIEST)
        matches = (
            HistoryEntry(round_, found) for round_ in rounds if (found := flt.matching(round_))
        )
        window = tuple(islice(matches, offset, offset + limit + 1))
        more = len(window) > limit
        return HistoryPage(window[:limit], offset + limit if more else None)
