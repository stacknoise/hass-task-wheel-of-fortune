"""Kandidatenfilter (KONZEPT §5.2): jeder Filter ein Objekt mit Ausschlussgrund."""

import datetime as dt
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import ClassVar, Protocol

from ..enums import ExclusionReason, Load
from ..models import Person, Task
from .matching import safe_winners
from .types import CandidateSelection, DrawContext, Exclusion


class CandidateFilter(Protocol):
    """Entfernt Personen aus der Kandidatenliste einer Aufgabe."""

    reason: ClassVar[ExclusionReason]
    soft: ClassVar[bool]

    def excluded(
        self, task: Task, candidates: Sequence[Person], context: DrawContext
    ) -> frozenset[str]:
        """Liefert die Kennungen der Personen, die dieser Filter entfernt.

        Harte Filter (`soft` falsch) sperren eine Person wirklich; weiche sind nur eine Vorliebe
        und weichen, wenn sonst niemand übrig bliebe.
        """
        ...


class PausedFilter:
    """Pausierte Personen (Belastung `paused`) bekommen nichts."""

    reason: ClassVar[ExclusionReason] = ExclusionReason.PAUSED
    soft: ClassVar[bool] = False

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
    soft: ClassVar[bool] = False

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
    soft: ClassVar[bool] = True

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
    soft: ClassVar[bool] = False

    def excluded(
        self,
        task: Task,  # noqa: ARG002
        candidates: Sequence[Person],
        context: DrawContext,
    ) -> frozenset[str]:
        """Alle Kandidaten mit Aufgabe in der Runde."""
        return frozenset(p.id for p in candidates if p.id in context.round_holders)


type FilterBuilder = tuple[Callable[[Task], bool], CandidateFilter]

# Reihenfolge laut KONZEPT §5.2, harte Filter vor weichen; die Bedingung wählt je Aufgabe.
_FILTERS: tuple[FilterBuilder, ...] = (
    (lambda _task: True, PausedFilter()),
    (lambda task: task.respect_absence, AbsenceFilter()),
    (lambda _task: True, RoundTakenFilter()),
    (lambda task: task.no_repeat, NoRepeatFilter()),
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

    def select(
        self, task: Task, context: DrawContext, rest: Sequence[Task] = ()
    ) -> CandidateSelection:
        """Erlaubte, bekannte Personen (nach Kennung sortiert) durch die Filterkette schicken.

        Harte Filter sperren, danach bleiben nur Personen, die den Rest der Runde nicht
        unlösbar machen (`rest` sind die noch folgenden Aufgaben); erst dann greifen weiche
        Filter wie „nicht zweimal dieselbe Aufgabe“.
        """
        exclusions: list[Exclusion] = []
        chain = self.factory.create_chain(task)
        hard = tuple(f for f in chain if not f.soft)
        soft = tuple(f for f in chain if f.soft)
        remaining = self._apply(hard, task, context, self._allowed(task, context), exclusions)
        remaining = self._reserve(remaining, rest, context, exclusions)
        remaining = self._apply(soft, task, context, remaining, exclusions)
        return CandidateSelection(tuple(remaining), tuple(exclusions))

    def eligible(self, task: Task, context: DrawContext) -> frozenset[str]:
        """Personen, die `task` bekommen dürfen (nur harte Filter), für die Zuordnung der Runde."""
        hard = tuple(f for f in self.factory.create_chain(task) if not f.soft)
        remaining = self._apply(hard, task, context, self._allowed(task, context), [])
        return frozenset(p.id for p in remaining)

    @staticmethod
    def _allowed(task: Task, context: DrawContext) -> list[Person]:
        """Bekannte Personen, die die Aufgabe laut Konfiguration bekommen dürfen."""
        return [context.persons[pid] for pid in sorted(context.persons) if task.allows(pid)]

    def _reserve(
        self,
        candidates: list[Person],
        rest: Sequence[Task],
        context: DrawContext,
        exclusions: list[Exclusion],
    ) -> list[Person]:
        """Behält Personen, bei denen insgesamt so viele Aufgaben wie möglich verteilt werden.

        Die übrigen kommen mit Grund `needed` ins Protokoll.
        """
        if not rest:
            return candidates
        options = [self.eligible(t, context) for t in rest]
        keep = safe_winners(frozenset(p.id for p in candidates), options)
        exclusions.extend(
            Exclusion(p.id, ExclusionReason.NEEDED) for p in candidates if p.id not in keep
        )
        return [p for p in candidates if p.id in keep]

    @staticmethod
    def _apply(
        chain: Sequence[CandidateFilter],
        task: Task,
        context: DrawContext,
        remaining: list[Person],
        exclusions: list[Exclusion],
    ) -> list[Person]:
        """Schickt die Kandidaten durch `chain` und trägt die Ausschlüsse ein."""
        for flt in chain:
            removed = flt.excluded(task, remaining, context)
            exclusions.extend(Exclusion(pid, flt.reason) for pid in sorted(removed))
            remaining = [p for p in remaining if p.id not in removed]
        return remaining
