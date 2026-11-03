"""Protokolle der Anwendungsschicht: Persistenz (KONZEPT §3.2), Zeitgeber, Ereignisse."""

import datetime as dt
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Protocol

from ..domain.models import Assignment, Person, Round, Schedule, Settings, Task
from ..domain.statistics.aggregate import AssignmentChange
from ..domain.types import AssignmentId, PersonId, RoundId, ScheduleId, TaskId

type FireCallback = Callable[[dt.datetime], None]
type ChangeCallback = Callable[[], None]
type Unsubscribe = Callable[[], None]
type IdFactory = Callable[[], str]


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

    def subscribe(self, listener: ChangeCallback) -> Unsubscribe:
        """Meldet einen Empfänger für jede Änderung an; liefert die Abmeldung."""
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

    def remove_round(self, round_id: RoundId) -> Round | None:
        """Entfernt eine Runde samt Zuteilungen und Indizes; liefert sie oder `None`."""
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


class TimerPort(Protocol):
    """Zeitgeber, die zu einem Zeitpunkt einmal auslösen (Infrastruktur: HA-Zeitgeber)."""

    def schedule(self, key: str, at: dt.datetime, callback: FireCallback) -> None:
        """Setzt den Zeitgeber `key` neu; ein vorhandener mit demselben Schlüssel entfällt."""
        ...

    def cancel(self, key: str) -> None:
        """Meldet den Zeitgeber `key` ab (unbekannte Schlüssel werden ignoriert)."""
        ...

    def cancel_all(self) -> None:
        """Meldet alle Zeitgeber ab (Entladen der Integration)."""
        ...


class RoundEvents(Protocol):
    """Meldungen nach außen (Events, Entitäten, Benachrichtigung); Umsetzung: HA-Events (AP-09)."""

    def round_drawn(self, round_: Round) -> None:
        """Eine Runde wurde ausgelost und gespeichert."""
        ...

    def reminder_due(self, schedule: Schedule, days_since: int) -> None:
        """Ein Zeitplan „nur manuell“ wurde seit `days_since` Tagen nicht ausgelost."""
        ...

    def assignment_completed(self, assignment: Assignment) -> None:
        """Eine Zuteilung wurde erledigt (pünktlich oder verspätet)."""
        ...

    def assignment_swapped(self, assignment: Assignment) -> None:
        """Eine Zuteilung wurde getauscht (`assignment.swap` nennt die abgebende Person)."""
        ...

    def assignment_missed(self, assignment: Assignment) -> None:
        """Eine Zuteilung wurde als verpasst markiert."""
        ...

    def round_deleted(self, round_: Round) -> None:
        """Eine Runde wurde samt Zuteilungen gelöscht (Statistik ist zurückgerechnet)."""
        ...

    def animation_requested(self, round_: Round, target: str) -> None:
        """Eine Anzeige `target` soll die Auslosung der Runde zeigen (Dienst `draw`)."""
        ...


class NoEvents:
    """Standard ohne Empfänger (Tests)."""

    def round_drawn(self, round_: Round) -> None:
        """Tut nichts."""

    def reminder_due(self, schedule: Schedule, days_since: int) -> None:
        """Tut nichts."""

    def assignment_completed(self, assignment: Assignment) -> None:
        """Tut nichts."""

    def assignment_swapped(self, assignment: Assignment) -> None:
        """Tut nichts."""

    def assignment_missed(self, assignment: Assignment) -> None:
        """Tut nichts."""

    def round_deleted(self, round_: Round) -> None:
        """Tut nichts."""

    def animation_requested(self, round_: Round, target: str) -> None:
        """Tut nichts."""


class Notifier(Protocol):
    """Schickt eine Benachrichtigung an ein Ziel (Infrastruktur: `notify`-Entität oder -Dienst)."""

    def check(self, target: str) -> None:
        """Prüft, dass das Ziel jetzt existiert.

        Raises:
            InvalidNotifyTargetError: Es gibt keine solche Entität oder keinen solchen Dienst.
        """
        ...

    async def async_send(self, target: str, title: str, message: str) -> None:
        """Sendet die Nachricht; das Ziel wird dabei erneut geprüft.

        Raises:
            InvalidNotifyTargetError: Das Ziel gibt es nicht (mehr).
            NotifyFailedError: Der Dienst hat den Versand abgelehnt oder war zu langsam.
        """
        ...


class Texts(Protocol):
    """Übersetzte Texte der Benachrichtigungen (Sprache der Installation)."""

    def render(self, kind: str, part: str, **values: object) -> str:
        """Setzt `values` in den Text `part` der Meldungsart `kind` ein."""
        ...


class AssignmentRecorder(Protocol):
    """Nimmt Änderungen an Zuteilungen entgegen (hält die Monatsaggregate aktuell)."""

    def record(self, round_: Round, changes: Iterable[AssignmentChange]) -> None:
        """Schreibt die Änderungen der Zuteilungen einer Runde fort."""
        ...

    def record_round(self, round_: Round) -> None:
        """Nimmt alle Zuteilungen einer neuen Runde auf."""
        ...

    def forget_round(self, round_: Round) -> None:
        """Nimmt alle Zuteilungen einer gelöschten Runde (samt Punkten) wieder heraus."""
        ...
