"""Konfiguration ändern: Personen, Aufgaben, Zeitpläne, Einstellungen (KONZEPT §6.4).

Die Eingaben sind unvertraute Felder aus dem Panel. Jedes Modell prüft sie streng
(`from_dict`); hier kommen nur Kennungen, Kurznamen und Verweise zwischen den Elementen hinzu.
"""

import datetime as dt
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from typing import Final, Protocol

from ..const.keys import (
    ERR_DUPLICATE,
    ERR_INCONSISTENT,
    ERR_SCHEDULE_UNASSIGNABLE,
    PH_TASKS,
    RESOURCE_ASSIGNMENT,
    RESOURCE_PERSON,
    RESOURCE_SCHEDULE,
    RESOURCE_TASK,
)
from ..const.limits import (
    HOURS_PER_DAY,
    MAX_TASKS_PER_SCHEDULE,
    RUN_DAYS_MAX,
    RUN_DAYS_MIN,
    SLUG_MAX_LENGTH,
)
from ..domain.errors import InUseError, NotFoundError, ValidationError
from ..domain.models import Interval, OnceAbsence, Person, Schedule, ScheduleEntry, Settings, Task
from ..domain.plan.preview import PlanPreview, evaluate_plan
from ..domain.types import PersonId, ScheduleId, TaskId
from ..domain.validation import ensure_range, ensure_size, ensure_unique
from .draw_inputs import unassignable_every_draw
from .draw_service import DrawService
from .ids import new_id
from .protocols import ConfigRepository, HistoryRepository, IdFactory
from .schedule_service import ScheduleService

FIELD_ID: Final = "id"
FIELD_SLUG: Final = "slug"
FIELD_NAME: Final = "name"
FIELD_ALLOWED: Final = "allowed"
FIELD_ENTRIES: Final = "entries"
FIELD_RUN_DAYS: Final = "run_days"
_SLUG_SEPARATOR: Final = "_"
_SLUG_FALLBACK: Final = "item"
_NOT_SLUG: Final = re.compile(r"[^a-z0-9]+")

type Fields = Mapping[str, object]
# Prüft das Benachrichtigungsziel einer Person (wirft bei unbekanntem Ziel)
type TargetCheck = Callable[[str | None], None]


class Sluggable(Protocol):
    """Alles mit Kennung und Kurznamen (Person, Zeitplan)."""

    @property
    def id(self) -> str:
        """Kennung."""
        ...

    @property
    def slug(self) -> str:
        """Kurzname."""
        ...


def slugify(name: object) -> str:
    """Kurzname aus dem Namen: Kleinbuchstaben, Ziffern, Unterstriche (Umlaute ohne Akzent)."""
    if not isinstance(name, str):
        return _SLUG_FALLBACK
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = _NOT_SLUG.sub(_SLUG_SEPARATOR, plain.lower()).strip(_SLUG_SEPARATOR)
    return slug[:SLUG_MAX_LENGTH].strip(_SLUG_SEPARATOR) or _SLUG_FALLBACK


def unique_slug(base: str, taken: Iterable[str]) -> str:
    """Hängt bei Bedarf eine Zahl an, bis der Kurzname frei ist (Länge bleibt begrenzt)."""
    used = set(taken)
    candidate, number = base, 1
    while candidate in used:
        number += 1
        suffix = f"{_SLUG_SEPARATOR}{number}"
        candidate = f"{base[: SLUG_MAX_LENGTH - len(suffix)]}{suffix}"
    return candidate


class ConfigService:
    """Legt Elemente an, ändert und löscht sie; Zeitpläne laufen über `ScheduleService`."""

    def __init__(
        self,
        config: ConfigRepository,
        history: HistoryRepository,
        schedules: ScheduleService,
        draws: DrawService,
        check_target: TargetCheck,
        *,
        id_factory: IdFactory = new_id,
    ) -> None:
        """Hält Konfiguration, Verlauf, Zeitplan-Dienst, Auslosung, Zielprüfung, Kennungsquelle."""
        self._check_target = check_target
        self._config = config
        self._history = history
        self._schedules = schedules
        self._draws = draws
        self._new_id = id_factory

    # --- Personen -------------------------------------------------------------------------

    def create_person(self, fields: Fields) -> Person:
        """Legt eine Person an (Kennung und Kurzname vergibt der Dienst, falls nötig)."""
        person = Person.from_dict(self._with_identity(fields, self._config.persons.values()))
        self._ensure_slug_free(person, self._config.persons.values())
        self._check_target(person.notify_target)
        self._config.put_person(person)
        return person

    def update_person(self, person_id: PersonId, fields: Fields) -> Person:
        """Ändert die genannten Felder einer Person."""
        current = _require(self._config.persons, person_id, RESOURCE_PERSON)
        person = Person.from_dict({**current.to_dict(), **fields})
        self._ensure_slug_free(person, self._config.persons.values())
        if person.notify_target != current.notify_target:
            self._check_target(person.notify_target)
        self._config.put_person(person)
        return person

    def add_absence(
        self, person_id: PersonId, start: dt.date, end: dt.date, today: dt.date
    ) -> Person:
        """Fügt eine einmalige Abwesenheit hinzu; vergangene einmalige entfallen (Obergrenze).

        Raises:
            NotFoundError: Die Person gibt es nicht.
            ValidationError: Die Abwesenheit ist ungültig oder es sind schon zu viele.
        """
        current = _require(self._config.persons, person_id, RESOURCE_PERSON)
        kept = tuple(
            item
            for item in current.absences
            if not (isinstance(item, OnceAbsence) and item.end < today)
        )
        person = replace(current, absences=(*kept, OnceAbsence(start=start, end=end)))
        self._config.put_person(person)
        return person

    def delete_person(self, person_id: PersonId) -> None:
        """Entfernt die Person, solange nichts sie mehr braucht.

        Raises:
            InUseError: Eine Aufgabe erlaubt sie noch, oder sie hat offene Zuteilungen.
        """
        _require(self._config.persons, person_id, RESOURCE_PERSON)
        self._ensure_unused(
            RESOURCE_PERSON,
            person_id,
            (
                (RESOURCE_TASK, (t for t in self._config.tasks.values() if person_id in t.allowed)),
                (RESOURCE_ASSIGNMENT, self._history.open_assignments(person_id)),
            ),
        )
        self._config.remove_person(person_id)

    # --- Aufgaben -------------------------------------------------------------------------

    def create_task(self, fields: Fields) -> Task:
        """Legt eine Aufgabe an; die erlaubten Personen müssen existieren."""
        task = Task.from_dict({**fields, FIELD_ID: self._new_id()})
        self._ensure_known(task.allowed, self._config.persons, RESOURCE_PERSON)
        self._config.put_task(task)
        return task

    def update_task(self, task_id: TaskId, fields: Fields) -> Task:
        """Ändert die genannten Felder einer Aufgabe."""
        current = _require(self._config.tasks, task_id, RESOURCE_TASK)
        task = Task.from_dict({**current.to_dict(), **fields})
        self._ensure_known(task.allowed, self._config.persons, RESOURCE_PERSON)
        self._config.put_task(task)
        return task

    def delete_task(self, task_id: TaskId) -> None:
        """Entfernt die Aufgabe, solange nichts sie mehr braucht.

        Raises:
            InUseError: Ein Zeitplan enthält sie noch, oder sie ist noch offen zugeteilt.
        """
        _require(self._config.tasks, task_id, RESOURCE_TASK)
        self._ensure_unused(
            RESOURCE_TASK,
            task_id,
            (
                (
                    RESOURCE_SCHEDULE,
                    (s for s in self._config.schedules.values() if task_id in s.task_ids),
                ),
                (RESOURCE_ASSIGNMENT, self._history.open_for_task(task_id)),
            ),
        )
        self._config.remove_task(task_id)

    # --- Zeitpläne ------------------------------------------------------------------------

    def create_schedule(self, fields: Fields, now: dt.datetime) -> Schedule:
        """Legt einen Zeitplan an und setzt seinen Zeitgeber."""
        schedule = Schedule.from_dict(self._with_identity(fields, self._config.schedules.values()))
        self._ensure_slug_free(schedule, self._config.schedules.values())
        self._ensure_known(schedule.task_ids, self._config.tasks, RESOURCE_TASK)
        self._ensure_schedule_valid(schedule, now)
        self._schedules.save(schedule, now)
        return schedule

    def update_schedule(
        self, schedule_id: ScheduleId, fields: Fields, now: dt.datetime
    ) -> Schedule:
        """Ändert die genannten Felder eines Zeitplans und setzt den Zeitgeber neu."""
        current = _require(self._config.schedules, schedule_id, RESOURCE_SCHEDULE)
        schedule = Schedule.from_dict({**current.to_dict(), **fields})
        self._ensure_slug_free(schedule, self._config.schedules.values())
        self._ensure_known(schedule.task_ids, self._config.tasks, RESOURCE_TASK)
        self._ensure_schedule_valid(schedule, now)
        self._schedules.save(schedule, now)
        return schedule

    def delete_schedule(self, schedule_id: ScheduleId) -> None:
        """Entfernt den Zeitplan, meldet seinen Zeitgeber ab und verwirft offene Panel-Runden."""
        _require(self._config.schedules, schedule_id, RESOURCE_SCHEDULE)
        self._draws.discard_for(schedule_id)
        self._schedules.delete(schedule_id)

    # --- Einstellungen --------------------------------------------------------------------

    def update_settings(self, fields: Fields) -> Settings:
        """Ändert die genannten Einstellungen."""
        settings = Settings.from_dict({**self._config.settings.to_dict(), **fields})
        self._config.set_settings(settings)
        return settings

    # --- Hilfen ---------------------------------------------------------------------------

    def _with_identity(self, fields: Fields, existing: Iterable[Sluggable]) -> Fields:
        """Ergänzt die Kennung und, falls nicht angegeben, einen freien Kurznamen aus dem Namen."""
        slug = fields.get(FIELD_SLUG) or unique_slug(
            slugify(fields.get(FIELD_NAME)), (item.slug for item in existing)
        )
        return {**fields, FIELD_ID: self._new_id(), FIELD_SLUG: slug}

    def preview_plan(
        self, interval: Fields, run_days: int, entries: Iterable[Fields]
    ) -> PlanPreview:
        """Bewertet einen noch nicht gespeicherten Plan (Editor): Platz, Belegung, Warnungen.

        Raises:
            ValidationError: Intervall, Lauf oder Aufgabenliste sind ungültig.
            NotFoundError: Eine Aufgabe gibt es nicht.
        """
        parsed_interval = Interval.from_dict(interval)
        parsed = tuple(ScheduleEntry.from_dict(entry) for entry in entries)
        ensure_range(FIELD_RUN_DAYS, run_days, RUN_DAYS_MIN, RUN_DAYS_MAX)
        ensure_size(FIELD_ENTRIES, parsed, 0, MAX_TASKS_PER_SCHEDULE)
        ensure_unique(FIELD_ENTRIES, (entry.task_id for entry in parsed))
        self._ensure_known((entry.task_id for entry in parsed), self._config.tasks, RESOURCE_TASK)
        draws = run_days * HOURS_PER_DAY // parsed_interval.hours
        return evaluate_plan(parsed, draws, parsed_interval.hours, self._reach(parsed))

    def _reach(self, entries: Iterable[ScheduleEntry]) -> dict[TaskId, frozenset[PersonId]]:
        """Je Aufgabe die Personen, die sie bekommen dürfen (ohne Einschränkung: alle)."""
        everyone = frozenset(self._config.persons)
        tasks = self._config.tasks
        return {
            entry.task_id: (tasks[entry.task_id].allowed & everyone)
            if tasks[entry.task_id].allowed
            else everyone
            for entry in entries
        }

    def _ensure_schedule_valid(self, schedule: Schedule, now: dt.datetime) -> None:
        """Der Plan ist speicherbar und die „jede Auslosung“-Aufgaben lassen sich vergeben.

        Überlast und Lücken sind nur Warnungen (der Editor zeigt sie), der Zeitplan lässt sich
        speichern.

        Raises:
            ValidationError: Niemand darf die Aufgaben übernehmen, oder es gibt weniger passende
                Personen als „jede Auslosung“-Aufgaben.
        """
        plan = evaluate_plan(
            schedule.entries,
            schedule.draws_per_run,
            schedule.interval.hours,
            self._reach(schedule.entries),
        )
        if not plan.savable:
            raise ValidationError(FIELD_ENTRIES, ERR_INCONSISTENT)
        stuck = unassignable_every_draw(self._config, self._history, schedule, now)
        if stuck:
            names = ", ".join(task.name for task in stuck)
            raise ValidationError(FIELD_ENTRIES, ERR_SCHEDULE_UNASSIGNABLE, {PH_TASKS: names})

    @staticmethod
    def _ensure_slug_free(item: Sluggable, existing: Iterable[Sluggable]) -> None:
        """Kein anderes Element trägt denselben Kurznamen."""
        if any(other.slug == item.slug and other.id != item.id for other in existing):
            raise ValidationError(FIELD_SLUG, ERR_DUPLICATE)

    @staticmethod
    def _ensure_unused(
        resource: str, item_id: str, uses: Iterable[tuple[str, Iterable[object]]]
    ) -> None:
        """Nichts der genannten Arten verwendet das Element noch."""
        for used_by, users in uses:
            if any(True for _ in users):
                raise InUseError(resource, item_id, used_by)

    @staticmethod
    def _ensure_known(ids: Iterable[str], known: Mapping[str, object], resource: str) -> None:
        """Alle genannten Kennungen gibt es."""
        for item_id in ids:
            if item_id not in known:
                raise NotFoundError(resource, item_id)


def _require[T](items: Mapping[str, T], item_id: str, resource: str) -> T:
    """Das Element oder `NotFoundError`."""
    item = items.get(item_id)
    if item is None:
        raise NotFoundError(resource, item_id)
    return item
