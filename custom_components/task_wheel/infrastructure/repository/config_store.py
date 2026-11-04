"""`ConfigStore`: Personen, Aufgaben, Zeitpläne und Einstellungen auf Basis von `Store`."""

from collections.abc import Callable, Mapping
from types import MappingProxyType

from ...const import defaults, limits
from ...const.keys import (
    KEY_PERSONS,
    KEY_SCHEDULES,
    KEY_SETTINGS,
    KEY_TASKS,
    RESOURCE_PERSON,
    RESOURCE_SCHEDULE,
    RESOURCE_TASK,
    STORE_CONFIG,
)
from ...domain.models import Person, Schedule, Settings, Task
from ...domain.serialization import model_of, tuple_of
from ...domain.types import PersonId, ScheduleId, TaskId
from .storage import (
    ChangeListeners,
    StoreLike,
    Unsubscribe,
    models_by_id,
    put_limited,
    read_root,
    read_section,
    remove_existing,
)


class ConfigStore:
    """Implementiert `ConfigRepository`; Daten liegen im Speicher, Sichern ist gebündelt."""

    def __init__(self, store: StoreLike) -> None:
        """Startet leer; `async_load` füllt den Bestand."""
        self._store = store
        self._persons: dict[PersonId, Person] = {}
        self._tasks: dict[TaskId, Task] = {}
        self._schedules: dict[ScheduleId, Schedule] = {}
        self._settings = Settings()
        self._listeners = ChangeListeners()

    @property
    def persons(self) -> Mapping[PersonId, Person]:
        """Alle Personen nach Kennung (schreibgeschützte Sicht)."""
        return MappingProxyType(self._persons)

    @property
    def tasks(self) -> Mapping[TaskId, Task]:
        """Alle Aufgaben nach Kennung (schreibgeschützte Sicht)."""
        return MappingProxyType(self._tasks)

    @property
    def schedules(self) -> Mapping[ScheduleId, Schedule]:
        """Alle Zeitpläne nach Kennung (schreibgeschützte Sicht)."""
        return MappingProxyType(self._schedules)

    @property
    def settings(self) -> Settings:
        """Die globalen Einstellungen."""
        return self._settings

    def subscribe(self, listener: Callable[[], None]) -> Unsubscribe:
        """Meldet einen Empfänger an, der nach jeder Änderung gerufen wird."""
        return self._listeners.subscribe(listener)

    async def async_load(self) -> None:
        """Lädt den Bestand; ohne Datei bleibt er leer. Fehlerhafte Daten brechen ab."""
        raw = await self._store.async_load()
        if raw is None:
            return
        data = read_root(STORE_CONFIG, raw)
        persons = read_section(STORE_CONFIG, data, KEY_PERSONS, tuple_of(model_of(Person)))
        tasks = read_section(STORE_CONFIG, data, KEY_TASKS, tuple_of(model_of(Task)))
        schedules = read_section(STORE_CONFIG, data, KEY_SCHEDULES, tuple_of(model_of(Schedule)))
        self._settings = read_section(STORE_CONFIG, data, KEY_SETTINGS, model_of(Settings))
        self._persons = models_by_id(persons)
        self._tasks = models_by_id(tasks)
        self._schedules = models_by_id(schedules)

    async def async_flush(self) -> None:
        """Sichert sofort."""
        await self._store.async_save(self._snapshot())

    def put_person(self, person: Person) -> None:
        """Legt eine Person an oder ersetzt sie."""
        put_limited(self._persons, person.id, person, RESOURCE_PERSON, limits.MAX_PERSONS)
        self._changed()

    def remove_person(self, person_id: PersonId) -> None:
        """Entfernt eine Person."""
        remove_existing(self._persons, person_id, RESOURCE_PERSON)
        self._changed()

    def put_task(self, task: Task) -> None:
        """Legt eine Aufgabe an oder ersetzt sie."""
        put_limited(self._tasks, task.id, task, RESOURCE_TASK, limits.MAX_TASKS)
        self._changed()

    def remove_task(self, task_id: TaskId) -> None:
        """Entfernt eine Aufgabe."""
        remove_existing(self._tasks, task_id, RESOURCE_TASK)
        self._changed()

    def put_schedule(self, schedule: Schedule) -> None:
        """Legt einen Zeitplan an oder ersetzt ihn."""
        put_limited(self._schedules, schedule.id, schedule, RESOURCE_SCHEDULE, limits.MAX_SCHEDULES)
        self._changed()

    def remove_schedule(self, schedule_id: ScheduleId) -> None:
        """Entfernt einen Zeitplan."""
        remove_existing(self._schedules, schedule_id, RESOURCE_SCHEDULE)
        self._changed()

    def set_settings(self, settings: Settings) -> None:
        """Ersetzt die Einstellungen."""
        self._settings = settings
        self._changed()

    def _changed(self) -> None:
        self._store.async_delay_save(self._snapshot, defaults.STORE_SAVE_DELAY_SECONDS)
        self._listeners.notify()

    def _snapshot(self) -> dict[str, object]:
        return {
            KEY_PERSONS: [item.to_dict() for item in self._persons.values()],
            KEY_TASKS: [item.to_dict() for item in self._tasks.values()],
            KEY_SCHEDULES: [item.to_dict() for item in self._schedules.values()],
            KEY_SETTINGS: self._settings.to_dict(),
        }
