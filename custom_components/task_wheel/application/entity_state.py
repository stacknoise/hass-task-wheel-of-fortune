"""Werte der Entitäten (KONZEPT §6.3): offene Aufgaben, Monatspunkte, nächste Auslosung."""

import datetime as dt
from dataclasses import dataclass

from ..domain.statistics import aggregate
from ..domain.statistics.report import Tally
from ..domain.types import AssignmentId, PersonId, ScheduleId
from .names import task_name
from .protocols import ConfigRepository, HistoryRepository
from .schedule_service import ScheduleService


@dataclass(slots=True, frozen=True)
class OpenItem:
    """Eine offene Zuteilung in der Sicht einer Person (To-do-Eintrag)."""

    assignment_id: AssignmentId
    task_name: str
    due_at: dt.datetime
    points: int


def _due(item: OpenItem) -> dt.datetime:
    return item.due_at


class EntityStateService:
    """Liest nur aus den Indizes und Aggregaten; nichts davon durchläuft den Verlauf."""

    def __init__(
        self, config: ConfigRepository, history: HistoryRepository, schedules: ScheduleService
    ) -> None:
        """Hält Repositories und Zeitplan-Dienst."""
        self._config = config
        self._history = history
        self._schedules = schedules

    def open_count(self, person_id: PersonId) -> int:
        """Anzahl der noch nicht abgeschlossenen Zuteilungen (offen und getauscht)."""
        return len(self._history.open_assignments(person_id))

    def open_items(self, person_id: PersonId) -> tuple[OpenItem, ...]:
        """Die noch nicht abgeschlossenen Zuteilungen, früheste Frist zuerst."""
        items = (
            OpenItem(item.id, task_name(self._config, item), item.due_at, item.points)
            for item in self._history.open_assignments(person_id)
        )
        return tuple(sorted(items, key=_due))

    def month_points(self, person_id: PersonId, now: dt.datetime) -> int:
        """Gutgeschriebene Punkte der Person im laufenden Monat (Faktoren aus den Einstellungen)."""
        tally = Tally()
        for row in aggregate.rows(self._history.aggregates, (aggregate.month_key(now),)):
            if row.person_id == person_id:
                tally.add(row.status, row.count, row.points)
        return tally.awarded(self._config.settings)

    def next_draw(self, schedule_id: ScheduleId, now: dt.datetime) -> dt.datetime | None:
        """Nächste automatische Auslosung; leer bei pausiert, archiviert oder nur manuell."""
        schedule = self._config.schedules.get(schedule_id)
        return None if schedule is None else self._schedules.next_run(schedule, now)
