"""Gemeinsamer Aufbau für Tests der Runden- und Zeitplan-Dienste."""

import datetime as dt
from itertools import count

from custom_components.task_wheel.application.draw_service import DrawService
from custom_components.task_wheel.application.schedule_service import ScheduleService
from custom_components.task_wheel.domain.models import EveryRound, ManualTrigger, Round, Schedule
from custom_components.task_wheel.infrastructure.repository.config_store import ConfigStore
from custom_components.task_wheel.infrastructure.repository.history_store import HistoryStore
from custom_components.task_wheel.infrastructure.repository.memory import MemoryStore

from ..domain import factories as f
from ..domain.draw.helpers import FixedRandom

DAY = dt.timedelta(days=1)


class FakeTimers:
    """Zeitgeber ohne Home Assistant: merkt sich Zeitpunkt und Rückruf je Schlüssel."""

    def __init__(self) -> None:
        self.timers: dict[str, tuple[dt.datetime, object]] = {}

    def schedule(self, key, at, callback) -> None:
        self.timers[key] = (at, callback)

    def cancel(self, key) -> None:
        self.timers.pop(key, None)

    def cancel_all(self) -> None:
        self.timers.clear()

    def fire(self, key: str, at: dt.datetime | None = None) -> None:
        """Löst den Zeitgeber aus (wie HA: er ist danach nicht mehr gesetzt)."""
        planned, callback = self.timers.pop(key)
        callback(at or planned)


class RecordingEvents:
    def __init__(self) -> None:
        self.drawn: list[Round] = []
        self.reminders: list[tuple[Schedule, int]] = []

    def round_drawn(self, round_: Round) -> None:
        self.drawn.append(round_)

    def reminder_due(self, schedule: Schedule, days_since: int) -> None:
        self.reminders.append((schedule, days_since))


class World:
    """Personen p1, p2; Aufgaben t1 (5 Punkte), t2 (2 Punkte); Zeitplan s1 über beide."""

    def __init__(self, *randoms: float, **settings: object) -> None:
        self.config = ConfigStore(MemoryStore())
        self.history = HistoryStore(MemoryStore())
        for ident in ("p1", "p2"):
            self.config.put_person(f.person(id=ident, slug=ident, name=ident, absences=()))
        both = frozenset({"p1", "p2"})
        every = EveryRound()
        self.config.put_task(f.task(id="t1", name="A", allowed=both, points=5, frequency=every))
        self.config.put_task(f.task(id="t2", name="B", allowed=both, points=2, frequency=every))
        self.config.put_schedule(f.schedule(trigger=ManualTrigger(), task_ids=("t1", "t2")))
        self.config.set_settings(f.settings(**settings))
        self.events = RecordingEvents()
        self.timers = FakeTimers()
        ids = count(1)
        self.draws = DrawService(
            self.config,
            self.history,
            FixedRandom(*(randoms or (0.1,))),
            self.events,
            lambda: f"id{next(ids)}",
        )
        self.schedules = ScheduleService(
            self.config, self.history, self.draws, self.timers, self.events
        )

    def put_schedule(self, **overrides: object) -> Schedule:
        base = {"trigger": ManualTrigger(), "task_ids": ("t1", "t2")}
        schedule = f.schedule(**{**base, **overrides})
        self.config.put_schedule(schedule)
        return schedule
