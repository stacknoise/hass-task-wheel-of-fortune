"""Entscheidungslog (Verbesserung 3): warum eine Person eine Aufgabe bekam oder nicht.

Ein Eintrag hält den Stand zum Zeitpunkt der Entscheidung fest, auch die Namen. So bleibt er
lesbar, wenn Personen, Aufgaben oder Zeitpläne später umbenannt oder gelöscht werden.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Final

from ..const import limits
from ..const.keys import ERR_INCONSISTENT, ERR_ORDER
from .enums import DecisionKind, RoundOrigin
from .serialization import (
    Model,
    enum_of,
    model_of,
    optional,
    spec,
    to_bool,
    to_datetime,
    to_float,
    to_str,
    tuple_of,
)
from .types import PersonId, RoundId, ScheduleId, TaskId
from .validation import ensure, ensure_aware, ensure_id, ensure_range, ensure_size

_FIELD_SINCE: Final = "since"
_FIELD_UNTIL: Final = "until"


@dataclass(slots=True, frozen=True, kw_only=True)
class WheelEntry(Model):
    """Eine Person, die im Rad der Aufgabe war, mit ihrer Chance."""

    person_id: PersonId = spec(to_str)
    person_name: str = spec(to_str)
    chance: float = spec(to_float)

    def __post_init__(self) -> None:
        """Prüft Kennung und Chance."""
        ensure_id("person_id", self.person_id)
        ensure_range("chance", self.chance, limits.CHANCE_MIN, limits.CHANCE_MAX)


@dataclass(slots=True, frozen=True, kw_only=True)
class ExcludedEntry(Model):
    """Eine Person, die nicht im Rad war, mit dem Grund (`ExclusionReason` oder `not_allowed`)."""

    person_id: PersonId = spec(to_str)
    person_name: str = spec(to_str)
    reason: str = spec(to_str)

    def __post_init__(self) -> None:
        """Prüft Kennung und Grund (Schlüssel `ExclusionReason` oder `not_allowed`)."""
        ensure_id("person_id", self.person_id)
        ensure_id("reason", self.reason)


@dataclass(slots=True, frozen=True, kw_only=True)
class TaskDecision(Model):
    """Ausgang für eine Aufgabe: Gewinner (oder niemand), Rad und Ausschlüsse."""

    task_id: TaskId = spec(to_str)
    task_name: str = spec(to_str)
    winner_id: PersonId | None = spec(optional(to_str), default=None)
    wheel: tuple[WheelEntry, ...] = spec(tuple_of(model_of(WheelEntry)), default=())
    excluded: tuple[ExcludedEntry, ...] = spec(tuple_of(model_of(ExcludedEntry)), default=())

    def __post_init__(self) -> None:
        """Prüft Kennung, Größen und dass der Gewinner im Rad stand."""
        ensure_id("task_id", self.task_id)
        ensure_size("wheel", self.wheel, 0, limits.MAX_PERSONS)
        ensure_size("excluded", self.excluded, 0, limits.MAX_PERSONS * limits.MAX_PERSONS)
        ensure(
            self.winner_id is None or any(w.person_id == self.winner_id for w in self.wheel),
            "winner_id",
            ERR_INCONSISTENT,
        )

    @property
    def assigned(self) -> bool:
        """Wahr, wenn eine Person die Aufgabe bekam."""
        return self.winner_id is not None


@dataclass(slots=True, frozen=True, kw_only=True)
class Exchange(Model):
    """Ein Tausch oder Austausch.

    Beim Tausch zweier Personen (`other_person_id` gesetzt) gibt `person_id` die Aufgabe
    `task_id` ab und bekommt `other_task_id`. Beim Austausch durch einen Administrator wird die
    Aufgabe `task_id` der Person `person_id` durch `other_task_id` ersetzt; `before_start`
    vermerkt, dass das vor dem Start der Auslosung geschah.
    """

    person_id: PersonId = spec(to_str)
    person_name: str = spec(to_str)
    task_id: TaskId = spec(to_str)
    task_name: str = spec(to_str)
    other_task_id: TaskId = spec(to_str)
    other_task_name: str = spec(to_str)
    other_person_id: PersonId | None = spec(optional(to_str), default=None)
    other_person_name: str | None = spec(optional(to_str), default=None)
    before_start: bool = spec(to_bool, default=False)

    def __post_init__(self) -> None:
        """Prüft die Kennungen."""
        for name in ("person_id", "task_id", "other_task_id"):
            ensure_id(name, getattr(self, name))

    @property
    def person_ids(self) -> tuple[PersonId, ...]:
        """Alle beteiligten Personen."""
        return (
            (self.person_id,)
            if self.other_person_id is None
            else (
                self.person_id,
                self.other_person_id,
            )
        )

    @property
    def task_ids(self) -> tuple[TaskId, ...]:
        """Beide beteiligten Aufgaben."""
        return (self.task_id, self.other_task_id)


@dataclass(slots=True, frozen=True, kw_only=True)
class DecisionRecord(Model):
    """Ein Eintrag des Entscheidungslogs: eine Auslosung, ein Tausch oder ein Austausch."""

    id: str = spec(to_str)
    kind: DecisionKind = spec(enum_of(DecisionKind))
    at: dt.datetime = spec(to_datetime)
    schedule_id: ScheduleId = spec(to_str)
    schedule_name: str = spec(to_str)
    round_id: RoundId | None = spec(optional(to_str), default=None)
    origin: RoundOrigin | None = spec(optional(enum_of(RoundOrigin)), default=None)
    tasks: tuple[TaskDecision, ...] = spec(tuple_of(model_of(TaskDecision)), default=())
    exchange: Exchange | None = spec(optional(model_of(Exchange)), default=None)

    def __post_init__(self) -> None:
        """Prüft Kennungen, Zeitzone und dass die Art zum Inhalt passt."""
        ensure_id("id", self.id)
        ensure_id("schedule_id", self.schedule_id)
        ensure_aware("at", self.at)
        ensure_size("tasks", self.tasks, 0, limits.MAX_ASSIGNMENTS_PER_ROUND)
        is_draw = self.kind is DecisionKind.DRAW
        ensure(is_draw == (self.exchange is None), "exchange", ERR_INCONSISTENT)
        ensure(is_draw or not self.tasks, "tasks", ERR_INCONSISTENT)

    def involves_person(self, person_id: PersonId) -> bool:
        """Die Person war Gewinner, im Rad, ausgeschlossen oder am Tausch beteiligt."""
        if self.exchange is not None:
            return person_id in self.exchange.person_ids
        return any(
            person_id in {w.person_id for w in item.wheel}
            or person_id in {e.person_id for e in item.excluded}
            for item in self.tasks
        )

    def involves_task(self, task_id: TaskId) -> bool:
        """Die Aufgabe wurde ausgelost oder getauscht."""
        if self.exchange is not None:
            return task_id in self.exchange.task_ids
        return any(item.task_id == task_id for item in self.tasks)


@dataclass(slots=True, frozen=True, kw_only=True)
class DecisionFilter:
    """Abfrage des Logs; leere Felder filtern nicht. `since` gilt einschließlich."""

    schedule_id: ScheduleId | None = None
    person_id: PersonId | None = None
    task_id: TaskId | None = None
    kind: DecisionKind | None = None
    since: dt.datetime | None = None
    until: dt.datetime | None = None

    def __post_init__(self) -> None:
        """Prüft Zeitzonen und Reihenfolge des Zeitraums."""
        if self.since is not None:
            ensure_aware(_FIELD_SINCE, self.since)
        if self.until is not None:
            ensure_aware(_FIELD_UNTIL, self.until)
        if self.since is not None and self.until is not None:
            ensure(self.since < self.until, _FIELD_UNTIL, ERR_ORDER)

    def matches(self, record: DecisionRecord) -> bool:
        """Alle gesetzten Felder passen auf den Eintrag."""
        return (
            _same(self.schedule_id, record.schedule_id)
            and _same(self.kind, record.kind)
            and self._in_range(record.at)
            and (self.person_id is None or record.involves_person(self.person_id))
            and (self.task_id is None or record.involves_task(self.task_id))
        )

    def _in_range(self, at: dt.datetime) -> bool:
        return (self.since is None or at >= self.since) and (self.until is None or at < self.until)


def _same[T](wanted: T | None, actual: T) -> bool:
    """Kein Filter gesetzt oder gleich."""
    return wanted is None or wanted == actual
