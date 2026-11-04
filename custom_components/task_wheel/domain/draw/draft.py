"""Eine Runde in Arbeit: schrittweise gezogen (Panel) oder in einem Zug (automatisch)."""

import datetime as dt
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field, replace

from ...const.keys import ERR_ROUND_COMPLETE, ERR_ROUND_INCOMPLETE
from ..enums import RoundOrigin
from ..errors import DrawRejectedError
from ..models import Assignment, Round, Task
from ..types import PersonId, RoundId, ScheduleId, TaskId
from .engine import DrawEngine, capacities
from .types import DrawContext, TaskDraw


@dataclass(slots=True, frozen=True)
class RoundDraft:
    """Unveränderlicher Zwischenstand: `results` sind die bisher gezogenen Aufgaben.

    Jeder Schritt liefert einen neuen Stand; Punkte und letzte Inhaber der bisherigen Ziehungen
    fließen in die nächste ein, damit eine Runde nicht alles an dieselbe Person verteilt.
    """

    schedule_id: ScheduleId
    origin: RoundOrigin
    started_at: dt.datetime
    context: DrawContext
    tasks: tuple[Task, ...]
    results: tuple[TaskDraw, ...] = ()
    replaces: dt.datetime | None = None
    # Ändern sich innerhalb einer Runde nicht und werden deshalb nur einmal berechnet:
    # Kapazität je Person und (als gemeinsamer Zwischenspeicher) die möglichen Personen je Aufgabe
    capacity: Mapping[PersonId, float] = field(default_factory=dict, compare=False, repr=False)
    reach: dict[TaskId, frozenset[PersonId]] = field(
        default_factory=dict, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        """Berechnet die Kapazitäten der Runde einmal (ein weitergereichter Stand behält sie)."""
        if not self.capacity:
            object.__setattr__(self, "capacity", capacities(self.context))

    @property
    def pending(self) -> tuple[Task, ...]:
        """Aufgaben, die noch nicht gezogen wurden."""
        return self.tasks[len(self.results) :]

    @property
    def complete(self) -> bool:
        """Alle Aufgaben sind gezogen."""
        return len(self.results) == len(self.tasks)

    def spin(self, engine: DrawEngine) -> "RoundDraft":
        """Zieht die nächste Aufgabe.

        Raises:
            DrawRejectedError: Es ist nichts mehr zu ziehen.
        """
        if self.complete:
            raise DrawRejectedError(ERR_ROUND_COMPLETE)
        task = self.tasks[len(self.results)]
        result = engine.draw_task(
            task, self.context, self.pending[1:], capacity=self.capacity, reach=self.reach
        )
        return replace(self, context=self._advance(task, result), results=(*self.results, result))

    def preview(self, engine: DrawEngine) -> TaskDraw:
        """Das Rad der nächsten Aufgabe ohne Ziehung.

        Raises:
            DrawRejectedError: Es ist nichts mehr zu ziehen.
        """
        if self.complete:
            raise DrawRejectedError(ERR_ROUND_COMPLETE)
        return engine.preview_task(
            self.pending[0],
            self.context,
            self.pending[1:],
            capacity=self.capacity,
            reach=self.reach,
        )

    def spin_rest(self, engine: DrawEngine) -> "RoundDraft":
        """Zieht alle übrigen Aufgaben."""
        draft = self
        for _ in self.pending:
            draft = draft.spin(engine)
        return draft

    def to_round(
        self, round_id: RoundId, new_id: Callable[[], str], finished_at: dt.datetime
    ) -> Round:
        """Macht aus dem vollständigen Stand die Runde; nicht verteilbare Aufgaben fehlen.

        Raises:
            DrawRejectedError: Es sind noch nicht alle Aufgaben gezogen.
        """
        if not self.complete:
            raise DrawRejectedError(ERR_ROUND_INCOMPLETE)
        assignments = tuple(
            self._assignment(round_id, new_id(), task, person_id, result)
            for task, person_id, result in self._winning()
        )
        return Round(
            id=round_id,
            schedule_id=self.schedule_id,
            origin=self.origin,
            started_at=self.started_at,
            finished_at=finished_at,
            replaces=self.replaces,
            assignments=assignments,
        )

    def _winning(self) -> Iterator[tuple[Task, PersonId, TaskDraw]]:
        """Aufgaben mit Gewinner, in der Reihenfolge der Ziehung."""
        for task, result in zip(self.tasks, self.results, strict=True):
            if result.winner_id is not None:
                yield task, result.winner_id, result

    def _assignment(
        self,
        round_id: RoundId,
        assignment_id: str,
        task: Task,
        person_id: PersonId,
        result: TaskDraw,
    ) -> Assignment:
        """Zuteilung mit dem Zeitraum der Runde (gilt ab, Frist)."""
        return Assignment(
            id=assignment_id,
            round_id=round_id,
            schedule_id=self.schedule_id,
            task_id=task.id,
            person_id=person_id,
            chance=result.chance,
            points=task.points,
            due_at=self.context.window.end,
            starts_at=self.context.window.start,
        )

    def _advance(self, task: Task, result: TaskDraw) -> DrawContext:
        """Kontext nach der Ziehung: Punkte, letzter Inhaber und Besetzung der Runde."""
        winner = result.winner_id
        if winner is None:
            return self.context
        points = {**self.context.points, winner: self.context.points.get(winner, 0) + task.points}
        holders = {**self.context.last_holders, task.id: winner}
        taken = self.context.round_holders | {winner}
        return replace(self.context, points=points, last_holders=holders, round_holders=taken)
