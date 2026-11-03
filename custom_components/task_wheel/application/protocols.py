"""Protokolle der Anwendungsschicht: Persistenz (Repository-Muster, KONZEPT §3.2)."""

import datetime as dt
from collections.abc import Iterable, Iterator, Mapping
from typing import Protocol

from ..domain.models import Assignment, Person, Round, Schedule, Settings, Task
from ..domain.statistics.aggregate import AssignmentChange
from ..domain.types import AssignmentId, PersonId, RoundId, ScheduleId, TaskId


class ConfigRepository(Protocol):
    """Konfiguration: Personen, Aufgaben, Zeitpläne, Einstellungen.

    Lesen kommt aus dem Speicher (Indizes); Schreiben ändert den Speicher sofort und
    stößt das gebündelte Sichern an.
    """

    @property
    def persons(self) -> Mapping[PersonId, Person]:
        """Alle Personen nach Kennung."""
        ...

    @property
    def tasks(self) -> Mapping[TaskId, Task]:
        """Alle Aufgaben nach Kennung."""
        ...

    @property
    def schedules(self) -> Mapping[ScheduleId, Schedule]:
        """Alle Zeitpläne nach Kennung."""
        ...

    @property
    def settings(self) -> Settings:
        """Die globalen Einstellungen."""
        ...

    async def async_load(self) -> None:
        """Lädt (und migriert) den Bestand."""
        ...

    async def async_flush(self) -> None:
        """Sichert sofort (z. B. beim Entladen)."""
        ...

    def put_person(self, person: Person) -> None:
        """Legt eine Person an oder ersetzt sie."""
        ...

    def remove_person(self, person_id: PersonId) -> None:
        """Entfernt eine Person."""
        ...

    def put_task(self, task: Task) -> None:
        """Legt eine Aufgabe an oder ersetzt sie."""
        ...

    def remove_task(self, task_id: TaskId) -> None:
        """Entfernt eine Aufgabe."""
        ...

    def put_schedule(self, schedule: Schedule) -> None:
        """Legt einen Zeitplan an oder ersetzt ihn."""
        ...

    def remove_schedule(self, schedule_id: ScheduleId) -> None:
        """Entfernt einen Zeitplan."""
        ...

    def set_settings(self, settings: Settings) -> None:
        """Ersetzt die Einstellungen."""
        ...


class HistoryRepository(Protocol):
    """Verlauf: Runden mit Zuteilungen und Monatsaggregate, mit Indizes für Regelprüfungen."""

    @property
    def rounds(self) -> Mapping[RoundId, Round]:
        """Alle gespeicherten Runden nach Kennung (älteste zuerst)."""
        ...

    @property
    def aggregates(self) -> Mapping[str, object]:
        """Monatsaggregate (Struktur gehört dem Statistik-Service)."""
        ...

    async def async_load(self) -> None:
        """Lädt (und migriert) den Bestand."""
        ...

    async def async_flush(self) -> None:
        """Sichert sofort (z. B. beim Entladen)."""
        ...

    def put_round(self, round_: Round) -> None:
        """Legt eine Runde an oder ersetzt sie samt Zuteilungen."""
        ...

    def set_aggregates(self, aggregates: Mapping[str, object]) -> None:
        """Ersetzt die Monatsaggregate."""
        ...

    def get_assignment(self, assignment_id: AssignmentId) -> Assignment | None:
        """Sucht eine Zuteilung über den Index."""
        ...

    def open_assignments(self, person_id: PersonId) -> tuple[Assignment, ...]:
        """Offene Zuteilungen einer Person über den Index."""
        ...

    def last_assignment(self, task_id: TaskId) -> Assignment | None:
        """Jüngste Zuteilung einer Aufgabe (nach Rundenbeginn) über den Index."""
        ...

    def rounds_since(self, since: dt.datetime) -> Iterator[Round]:
        """Runden, die ab `since` begonnen haben, die neueste zuerst."""
        ...

    def assignments_since(self, since: dt.datetime) -> tuple[Assignment, ...]:
        """Zuteilungen aus Runden, die ab `since` begonnen haben."""
        ...

    async def async_purge(self, cutoff: dt.datetime) -> int:
        """Entfernt Runden, die vor `cutoff` begonnen haben; liefert die Anzahl."""
        ...


class AssignmentRecorder(Protocol):
    """Nimmt Änderungen an Zuteilungen entgegen (hält die Monatsaggregate aktuell)."""

    def record(self, round_: Round, changes: Iterable[AssignmentChange]) -> None:
        """Schreibt die Änderungen der Zuteilungen einer Runde fort."""
        ...
