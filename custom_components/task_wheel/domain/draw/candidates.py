"""Kandidatenfilter (KONZEPT §5.2): jeder Filter ein Objekt mit Ausschlussgrund."""

import datetime as dt
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import ClassVar, Protocol

from ..enums import ExclusionReason, Load
from ..models import Person, Task
from .types import CandidateSelection, DrawContext, Exclusion


class CandidateFilter(Protocol):
    """Entfernt Personen aus der Kandidatenliste einer Aufgabe."""

    reason: ClassVar[ExclusionReason]

    def excluded(
        self, task: Task, candidates: Sequence[Person], context: DrawContext
    ) -> frozenset[str]:
        """Liefert die Kennungen der Personen, die dieser Filter entfernt."""
        ...


class PausedFilter:
    """Pausierte Personen (Belastung `paused`) bekommen nichts."""

    reason: ClassVar[ExclusionReason] = ExclusionReason.PAUSED

    def excluded(
        self,
        task: Task,  # noqa: ARG002
        candidates: Sequence[Person],
        context: DrawContext,  # noqa: ARG002
    ) -> frozenset[str]:
        """Alle Personen mit Belastung `paused`."""
        return frozenset(p.id for p in candidates if p.load is Load.PAUSED)


class AbsenceFilter:
    """Personen, die im Fristfenster an keinem Tag anwesend sind."""

    reason: ClassVar[ExclusionReason] = ExclusionReason.ABSENT

    def excluded(
        self, task: Task, candidates: Sequence[Person], context: DrawContext
    ) -> frozenset[str]:
        """Personen ohne anwesenden Tag in `[heute, heute + due_days]`."""
        start = context.now.date()
        end = start + dt.timedelta(days=task.due_days)
        return frozenset(
            p.id for p in candidates if not context.availability[p.id].present_in_window(start, end)
        )


class NoRepeatFilter:
    """Wer die Aufgabe zuletzt hatte, bleibt draußen, sofern noch andere übrig sind."""

    reason: ClassVar[ExclusionReason] = ExclusionReason.REPEAT

    def excluded(
        self, task: Task, candidates: Sequence[Person], context: DrawContext
    ) -> frozenset[str]:
        """Der letzte Inhaber, wenn mindestens eine andere Person bleibt."""
        holder = context.last_holders.get(task.id)
        is_candidate = any(p.id == holder for p in candidates)
        return (
            frozenset({holder}) if holder and is_candidate and len(candidates) > 1 else frozenset()
        )


class RoundTakenFilter:
    """Wer in dieser Runde schon eine Aufgabe hat, bekommt keine zweite."""

    reason: ClassVar[ExclusionReason] = ExclusionReason.TAKEN

    def excluded(
        self,
        task: Task,  # noqa: ARG002
        candidates: Sequence[Person],
        context: DrawContext,
    ) -> frozenset[str]:
        """Alle Kandidaten mit Aufgabe in der Runde."""
        return frozenset(p.id for p in candidates if p.id in context.round_holders)


type FilterBuilder = tuple[Callable[[Task], bool], CandidateFilter]

# Reihenfolge laut KONZEPT §5.2; die Bedingung entscheidet, ob der Filter für die Aufgabe gilt.
_FILTERS: tuple[FilterBuilder, ...] = (
    (lambda _task: True, PausedFilter()),
    (lambda task: task.respect_absence, AbsenceFilter()),
    (lambda task: task.no_repeat, NoRepeatFilter()),
    (lambda _task: True, RoundTakenFilter()),
)


class CandidateFilterFactory:
    """Stellt die Filterkette für eine Aufgabe zusammen."""

    def __init__(self, filters: Sequence[FilterBuilder] = _FILTERS) -> None:
        """Übernimmt die geordnete Registry; Tests können eine eigene übergeben."""
        self._filters = filters

    def create_chain(self, task: Task) -> tuple[CandidateFilter, ...]:
        """Filter, die für `task` gelten, in fester Reihenfolge."""
        return tuple(flt for applies, flt in self._filters if applies(task))


@dataclass(slots=True, frozen=True)
class CandidateSelector:
    """Wendet die Filterkette an und protokolliert die Ausschlussgründe."""

    factory: CandidateFilterFactory = CandidateFilterFactory()  # noqa: RUF009

    def select(self, task: Task, context: DrawContext) -> CandidateSelection:
        """Erlaubte, bekannte Personen (nach Kennung sortiert) durch die Filterkette schicken."""
        remaining = [context.persons[pid] for pid in sorted(context.persons) if task.allows(pid)]
        exclusions: list[Exclusion] = []
        for flt in self.factory.create_chain(task):
            removed = flt.excluded(task, remaining, context)
            exclusions.extend(Exclusion(pid, flt.reason) for pid in sorted(removed))
            remaining = [p for p in remaining if p.id not in removed]
        return CandidateSelection(tuple(remaining), tuple(exclusions))
