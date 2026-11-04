"""Entscheidungslog: hält fest, warum eine Person eine Aufgabe bekam oder nicht."""

import datetime as dt
from dataclasses import dataclass
from itertools import islice

from ..const.defaults import DEFAULT_HISTORY_PAGE_SIZE
from ..const.keys import REASON_NOT_ALLOWED
from ..const.limits import DECISION_OFFSET_MAX, HISTORY_PAGE_SIZE_MAX, HISTORY_PAGE_SIZE_MIN
from ..domain.decisions import (
    DecisionFilter,
    DecisionRecord,
    Exchange,
    ExcludedEntry,
    TaskDecision,
    WheelEntry,
)
from ..domain.draw.draft import RoundDraft
from ..domain.draw.types import TaskDraw
from ..domain.enums import DecisionKind
from ..domain.models import Assignment, Round
from ..domain.types import PersonId, TaskId
from ..domain.validation import ensure_range
from .ids import new_id
from .protocols import ConfigRepository, DecisionRepository, IdFactory

_FIELD_LIMIT = "limit"
_FIELD_OFFSET = "offset"


@dataclass(slots=True, frozen=True)
class DecisionPage:
    """Eine Seite des Logs (neueste zuerst); `next_offset` ist leer auf der letzten Seite."""

    entries: tuple[DecisionRecord, ...]
    next_offset: int | None


class DecisionService:
    """Schreibt und liest das Log; Namen werden zum Zeitpunkt der Entscheidung festgehalten."""

    def __init__(
        self,
        config: ConfigRepository,
        decisions: DecisionRepository,
        *,
        id_factory: IdFactory = new_id,
    ) -> None:
        """Hält Konfiguration (für Namen), Log-Repository und Kennungsquelle."""
        self._config = config
        self._decisions = decisions
        self._new_id = id_factory

    def record_draw(self, draft: RoundDraft, round_: Round) -> None:
        """Hält je Aufgabe der Runde fest: Gewinner, Rad und ausgeschlossene Personen."""
        tasks = tuple(self._task_decision(result) for result in draft.results)
        self._add(
            DecisionRecord(
                id=self._new_id(),
                kind=DecisionKind.DRAW,
                at=round_.finished_at or round_.started_at,
                schedule_id=round_.schedule_id,
                schedule_name=self._schedule_name(round_.schedule_id),
                round_id=round_.id,
                origin=round_.origin,
                tasks=tasks,
            )
        )

    def record_swap(self, first: Assignment, second: Assignment, now: dt.datetime) -> None:
        """Hält einen Tausch fest: `first` gehört jetzt der Zielperson, `second` der abgebenden."""
        giver = first.swap.from_person_id if first.swap else second.person_id
        self.record_exchange(
            DecisionKind.SWAP,
            first.schedule_id,
            Exchange(
                person_id=giver,
                person_name=self._person_name(giver),
                task_id=first.task_id,
                task_name=self._task_name(first.task_id),
                other_task_id=second.task_id,
                other_task_name=self._task_name(second.task_id),
                other_person_id=first.person_id,
                other_person_name=self._person_name(first.person_id),
            ),
            now,
            round_id=first.round_id,
        )

    def record_replacement(
        self, schedule_id: str, task_id: TaskId, new_task_id: TaskId, now: dt.datetime
    ) -> None:
        """Hält fest, dass ein Admin vor dem Start eine Aufgabe der Runde austauschte."""
        self.record_exchange(
            DecisionKind.EXCHANGE,
            schedule_id,
            Exchange(
                task_id=task_id,
                task_name=self._task_name(task_id),
                other_task_id=new_task_id,
                other_task_name=self._task_name(new_task_id),
                before_start=True,
            ),
            now,
        )

    def record_exchange(
        self,
        kind: DecisionKind,
        schedule_id: str,
        exchange: Exchange,
        now: dt.datetime,
        *,
        round_id: str | None = None,
    ) -> None:
        """Hält einen Tausch (`SWAP`) oder Austausch (`EXCHANGE`, vor dem Start) fest."""
        self._add(
            DecisionRecord(
                id=self._new_id(),
                kind=kind,
                at=now,
                schedule_id=schedule_id,
                schedule_name=self._schedule_name(schedule_id),
                round_id=round_id,
                exchange=exchange,
            )
        )

    def page(
        self,
        query: DecisionFilter | None = None,
        offset: int = 0,
        limit: int = DEFAULT_HISTORY_PAGE_SIZE,
    ) -> DecisionPage:
        """Liefert bis zu `limit` passende Einträge ab dem `offset`-ten Treffer.

        Raises:
            ValidationError: `offset` oder `limit` außerhalb des erlaubten Bereichs.
        """
        ensure_range(_FIELD_LIMIT, limit, HISTORY_PAGE_SIZE_MIN, HISTORY_PAGE_SIZE_MAX)
        ensure_range(_FIELD_OFFSET, offset, 0, DECISION_OFFSET_MAX)
        window = tuple(
            islice(self._decisions.query(query or DecisionFilter()), offset, offset + limit + 1)
        )
        more = len(window) > limit
        return DecisionPage(window[:limit], offset + limit if more else None)

    def purge(self, now: dt.datetime) -> int:
        """Löscht Einträge außerhalb der Aufbewahrung (Einstellung in Tagen)."""
        retention = dt.timedelta(days=self._config.settings.decision_retention_days)
        return self._decisions.purge(now - retention)

    def _add(self, record: DecisionRecord) -> None:
        self._decisions.add(record)

    def _task_decision(self, result: TaskDraw) -> TaskDecision:
        """Gewinner, Rad und Ausschlüsse einer Aufgabe mit den heutigen Namen."""
        return TaskDecision(
            task_id=result.task_id,
            task_name=self._task_name(result.task_id),
            winner_id=result.winner_id,
            wheel=tuple(
                WheelEntry(
                    person_id=segment.person_id,
                    person_name=self._person_name(segment.person_id),
                    chance=segment.chance,
                )
                for segment in result.segments
            ),
            excluded=self._excluded(result),
        )

    def _excluded(self, result: TaskDraw) -> tuple[ExcludedEntry, ...]:
        """Ausgeschlossene der Filterkette, danach Personen ohne Erlaubnis für die Aufgabe."""
        reasons = [(item.person_id, str(item.reason)) for item in result.exclusions]
        known = {person_id for person_id, _reason in reasons}
        known.update(segment.person_id for segment in result.segments)
        reasons.extend(
            (pid, REASON_NOT_ALLOWED) for pid in self._not_allowed(result.task_id, known)
        )
        return tuple(
            ExcludedEntry(person_id=pid, person_name=self._person_name(pid), reason=reason)
            for pid, reason in reasons
        )

    def _not_allowed(self, task_id: TaskId, known: set[PersonId]) -> list[PersonId]:
        """Personen, die weder im Rad noch ausgeschlossen sind: die Aufgabe erlaubt sie nicht."""
        task = self._config.tasks.get(task_id)
        if task is None:
            return []
        return [
            pid for pid in sorted(self._config.persons) if pid not in known and not task.allows(pid)
        ]

    def _person_name(self, person_id: PersonId) -> str:
        person = self._config.persons.get(person_id)
        return person.name if person else person_id

    def _task_name(self, task_id: TaskId) -> str:
        task = self._config.tasks.get(task_id)
        return task.name if task else task_id

    def _schedule_name(self, schedule_id: str) -> str:
        schedule = self._config.schedules.get(schedule_id)
        return schedule.name if schedule else schedule_id
