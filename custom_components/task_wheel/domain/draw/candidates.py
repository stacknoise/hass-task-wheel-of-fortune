"""Kandidatenfilter (KONZEPT §5.2): jeder Filter ein Objekt mit Ausschlussgrund."""

from collections.abc import Callable, MutableMapping, Sequence
from dataclasses import dataclass, replace
from typing import ClassVar, Protocol

from ..enums import ExclusionReason, Load
from ..models import Person, Task
from ..types import PersonId, TaskId
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


class MinLoadFilter:
    """Personen, deren Belastbarkeit unter der Mindest-Belastbarkeit der Aufgabe liegt."""

    reason: ClassVar[ExclusionReason] = ExclusionReason.LOAD
    soft: ClassVar[bool] = False

    def excluded(
        self,
        task: Task,
        candidates: Sequence[Person],
        context: DrawContext,  # noqa: ARG002
    ) -> frozenset[str]:
        """Alle Personen, für die `task.accepts_load` verneint."""
        return frozenset(p.id for p in candidates if not task.accepts_load(p.load))


class AbsenceFilter:
    """Personen, die im ganzen Zeitraum der Frist abwesend sind (irgendwann da genügt)."""

    reason: ClassVar[ExclusionReason] = ExclusionReason.ABSENT
    soft: ClassVar[bool] = False

    def excluded(
        self,
        task: Task,  # noqa: ARG002
        candidates: Sequence[Person],
        context: DrawContext,
    ) -> frozenset[str]:
        """Personen, die an keinem Tag von „gilt ab“ bis zur Frist anwesend sind."""
        window = context.window
        return frozenset(
            p.id
            for p in candidates
            if not context.availability[p.id].present_in_window(window.first_day, window.last_day)
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
    (lambda task: task.min_load is not Load.PAUSED, MinLoadFilter()),
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
        self,
        task: Task,
        context: DrawContext,
        rest: Sequence[Task] = (),
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None = None,
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
        shown = self._apply(soft, task, context, remaining, [])
        remaining = self._reserve(remaining, rest, context, exclusions, reach)
        remaining = self._apply(soft, task, context, remaining, exclusions)
        return self._selection(remaining, shown, exclusions)

    @staticmethod
    def _selection(
        candidates: list[Person], shown: list[Person], exclusions: list[Exclusion]
    ) -> CandidateSelection:
        """Kandidaten, Rad (Kandidaten und alle weiter möglichen Personen) und Ausschlüsse.

        Wer im Rad steht, gilt nicht als ausgeschlossen.
        """
        if not candidates:
            return CandidateSelection((), tuple(exclusions))
        wheel = {p.id: p for p in (*shown, *candidates)}
        kept = tuple(e for e in exclusions if e.person_id not in wheel)
        return CandidateSelection(tuple(candidates), kept, tuple(wheel[i] for i in sorted(wheel)))

    def eligible(self, task: Task, context: DrawContext) -> frozenset[str]:
        """Personen, die `task` bekommen dürfen (harte Filter), ohne die Besetzung der Runde."""
        hard = tuple(f for f in self.factory.create_chain(task) if not f.soft)
        free = replace(context, round_holders=frozenset())
        remaining = self._apply(hard, task, free, self._allowed(task, free), [])
        return frozenset(p.id for p in remaining)

    def _options(
        self,
        tasks: Sequence[Task],
        context: DrawContext,
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None,
    ) -> list[frozenset[PersonId]]:
        """Mögliche Personen je Aufgabe ohne die Besetzung der Runde (aus `reach`, falls da)."""
        memo = {} if reach is None else reach
        return [self._reach(memo, task, context) - context.round_holders for task in tasks]

    def _reach(
        self,
        memo: MutableMapping[TaskId, frozenset[PersonId]],
        task: Task,
        context: DrawContext,
    ) -> frozenset[PersonId]:
        """Mögliche Personen der Aufgabe; nur berechnet, wenn `memo` sie noch nicht kennt."""
        if task.id not in memo:
            memo[task.id] = self.eligible(task, context)
        return memo[task.id]

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
        reach: MutableMapping[TaskId, frozenset[PersonId]] | None,
    ) -> list[Person]:
        """Behält Personen, bei denen insgesamt so viele Aufgaben wie möglich verteilt werden.

        Die übrigen kommen mit Grund `needed` ins Protokoll.
        """
        if not rest:
            return candidates
        options = self._options(rest, context, reach)
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
