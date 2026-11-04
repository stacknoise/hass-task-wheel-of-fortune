"""Aufbau für Tests der Panel-API ohne Home Assistant (echte Dienste, Speicher im RAM)."""

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from custom_components.task_wheel.application.notification_service import NotificationService
from custom_components.task_wheel.domain.enums import AssignmentStatus
from custom_components.task_wheel.domain.models import EveryRound, ManualTrigger
from custom_components.task_wheel.infrastructure.repository.config_store import ConfigStore
from custom_components.task_wheel.infrastructure.repository.decision_store import DecisionStore
from custom_components.task_wheel.infrastructure.repository.history_store import HistoryStore
from custom_components.task_wheel.infrastructure.repository.memory import MemoryStore
from custom_components.task_wheel.runtime import TaskWheelData, compose
from custom_components.task_wheel.websocket.command import Reply, Request
from custom_components.task_wheel.websocket.registry import COMMANDS

from ..application.test_notification_service import FakeNotifier
from ..application.world import FakeTimers, RecordingEvents
from ..domain import factories as f
from ..domain.draw.helpers import FixedRandom

if TYPE_CHECKING:
    from custom_components.task_wheel.application.wire import Json

PREFIX = "task_wheel/"
BY_NAME = {command.name: command for command in COMMANDS}


class Api:
    """Personen p1, p2; Aufgaben t1, t2; manueller Zeitplan s1; drei Zuteilungen in Runde r1."""

    def __init__(self, *randoms: float) -> None:
        self.now = f.NOW
        self.config = ConfigStore(MemoryStore())
        self.history = HistoryStore(MemoryStore())
        for ident in ("p1", "p2"):
            self.config.put_person(f.person(id=ident, slug=ident, name=ident, absences=()))
        both = frozenset({"p1", "p2"})
        self.config.put_task(
            f.task(id="t1", name="A", allowed=both, points=5, frequency=EveryRound())
        )
        self.config.put_task(
            f.task(id="t2", name="B", allowed=both, points=2, frequency=EveryRound())
        )
        self.config.put_schedule(f.schedule(trigger=ManualTrigger(), task_ids=("t1", "t2")))
        self.config.set_settings(f.settings())
        self.history.put_round(f.finished_round())
        self.timers = FakeTimers()
        self.events = RecordingEvents()
        self.pushed: list[Json] = []
        self.notifier = FakeNotifier()
        self.data: TaskWheelData = compose(
            self.config,
            self.history,
            DecisionStore(MemoryStore()),
            timers=self.timers,
            events=self.events,
            notifications=NotificationService(
                self.config, self.notifier, MagicMock(), lambda coro: coro.close()
            ),
            clock=lambda: self.now,
            spawn=lambda coro: coro.close(),
            rng=FixedRandom(*(randoms or (0.1,))),
        )

    def run(self, name: str, **fields: Any) -> Reply:
        """Prüft die Nachricht gegen das Schema des Befehls und führt ihn aus."""
        command = BY_NAME[PREFIX + name]
        params = command.schema()({"id": 1, "type": command.name, **fields})
        return command.run(Request(self.data, self.now, params, self.pushed.append))

    def result(self, name: str, **fields: Any) -> Any:
        """Das Ergebnis des Befehls."""
        return self.run(name, **fields).result

    def advance(self, **delta: float) -> None:
        """Schiebt die Uhr vor."""
        self.now += dt.timedelta(**delta)

    def open_partner(self) -> None:
        """Macht `a2` (p2) zur offenen Zuteilung, damit p1 mit p2 tauschen kann."""
        round_ = self.history.rounds["r1"]
        assignments = tuple(
            replace(item, status=AssignmentStatus.OPEN, swap=None) if item.id == "a2" else item
            for item in round_.assignments
        )
        self.history.put_round(replace(round_, assignments=assignments))
