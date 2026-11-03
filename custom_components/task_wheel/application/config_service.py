"""Konfiguration ändern: Personen, Aufgaben, Zeitpläne, Einstellungen (KONZEPT §6.4).

Die Eingaben sind unvertraute Felder aus dem Panel. Jedes Modell prüft sie streng
(`from_dict`); hier kommen nur Kennungen, Kurznamen und Verweise zwischen den Elementen hinzu.
"""

import datetime as dt
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Final, Protocol

from ..const.keys import ERR_DUPLICATE
from ..const.limits import SLUG_MAX_LENGTH
from ..domain.errors import InUseError, NotFoundError, ValidationError
from ..domain.models import Person, Schedule, Settings, Task
from ..domain.types import PersonId, ScheduleId, TaskId
from .draw_service import DrawService
from .ids import new_id
from .protocols import ConfigRepository, IdFactory
from .schedule_service import ScheduleService

RESOURCE_PERSON = "person"
RESOURCE_TASK = "task"
RESOURCE_SCHEDULE = "schedule"

FIELD_ID: Final = "id"
FIELD_SLUG: Final = "slug"
FIELD_NAME: Final = "name"
FIELD_ALLOWED: Final = "allowed"
FIELD_TASK_IDS: Final = "task_ids"
_SLUG_SEPARATOR: Final = "_"
_SLUG_FALLBACK: Final = "item"
_NOT_SLUG: Final = re.compile(r"[^a-z0-9]+")

type Fields = Mapping[str, object]


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
        schedules: ScheduleService,
        draws: DrawService,
        id_factory: IdFactory = new_id,
    ) -> None:
        """Hält Konfiguration, Zeitplan-Dienst, Auslosung und Kennungsquelle."""
        self._config = config
        self._schedules = schedules
        self._draws = draws
        self._new_id = id_factory

    # --- Personen -------------------------------------------------------------------------

    def create_person(self, fields: Fields) -> Person:
        """Legt eine Person an (Kennung und Kurzname vergibt der Dienst, falls nötig)."""
        person = Person.from_dict(self._with_identity(fields, self._config.persons.values()))
        self._ensure_slug_free(person, self._config.persons.values())
        self._config.put_person(person)
        return person

    def update_person(self, person_id: PersonId, fields: Fields) -> Person:
        """Ändert die genannten Felder einer Person."""
        current = _require(self._config.persons, person_id, RESOURCE_PERSON)
        person = Person.from_dict({**current.to_dict(), **fields})
        self._ensure_slug_free(person, self._config.persons.values())
        self._config.put_person(person)
        return person

    def delete_person(self, person_id: PersonId) -> None:
        """Entfernt die Person und streicht sie aus den erlaubten Personen der Aufgaben.

        Raises:
            InUseError: Eine Aufgabe würde dadurch keine erlaubte Person mehr haben.
        """
        _require(self._config.persons, person_id, RESOURCE_PERSON)
        affected = [task for task in self._config.tasks.values() if person_id in task.allowed]
        for task in affected:
            if task.allowed == {person_id}:
                raise InUseError(RESOURCE_PERSON, person_id, RESOURCE_TASK)
        self._config.remove_person(person_id)
        for task in affected:
            self._config.put_task(replace(task, allowed=task.allowed - {person_id}))

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

    def delete_task(self, task_id: TaskId, now: dt.datetime) -> None:
        """Entfernt die Aufgabe und streicht sie aus den Zeitplänen.

        Raises:
            InUseError: Ein Zeitplan bestünde dann aus keiner Aufgabe mehr.
        """
        _require(self._config.tasks, task_id, RESOURCE_TASK)
        affected = [item for item in self._config.schedules.values() if task_id in item.task_ids]
        for schedule in affected:
            if schedule.task_ids == (task_id,):
                raise InUseError(RESOURCE_TASK, task_id, RESOURCE_SCHEDULE)
        self._config.remove_task(task_id)
        for schedule in affected:
            kept = tuple(item for item in schedule.task_ids if item != task_id)
            self._schedules.save(replace(schedule, task_ids=kept), now)

    # --- Zeitpläne ------------------------------------------------------------------------

    def create_schedule(self, fields: Fields, now: dt.datetime) -> Schedule:
        """Legt einen Zeitplan an und setzt seinen Zeitgeber."""
        schedule = Schedule.from_dict(self._with_identity(fields, self._config.schedules.values()))
        self._ensure_slug_free(schedule, self._config.schedules.values())
        self._ensure_known(schedule.task_ids, self._config.tasks, RESOURCE_TASK)
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

    @staticmethod
    def _ensure_slug_free(item: Sluggable, existing: Iterable[Sluggable]) -> None:
        """Kein anderes Element trägt denselben Kurznamen."""
        if any(other.slug == item.slug and other.id != item.id for other in existing):
            raise ValidationError(FIELD_SLUG, ERR_DUPLICATE)

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
