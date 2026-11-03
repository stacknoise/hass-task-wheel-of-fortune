"""Komposition: verdrahtet alle Objekte an einer Stelle (Schicht 1, ohne Home Assistant)."""

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

from .application.assignment_service import AssignmentService
from .application.draw_service import DrawService
from .application.entity_state import EntityStateService
from .application.history_service import HistoryService
from .application.maintenance_service import MaintenanceService, Spawn
from .application.protocols import ConfigRepository, HistoryRepository, RoundEvents, TimerPort
from .application.schedule_service import ScheduleService
from .application.statistics_service import StatisticsService
from .application.swap_service import SwapService
from .domain.draw.engine import secure_random
from .domain.draw.types import RandomSource

type Clock = Callable[[], dt.datetime]


@dataclass(slots=True, frozen=True)
class TaskWheelData:
    """Alles, was eine geladene Config Entry braucht (`entry.runtime_data`)."""

    config: ConfigRepository
    history: HistoryRepository
    events: RoundEvents
    clock: Clock
    statistics: StatisticsService
    draws: DrawService
    assignments: AssignmentService
    swaps: SwapService
    schedules: ScheduleService
    maintenance: MaintenanceService
    history_service: HistoryService
    entity_state: EntityStateService


def compose(
    config: ConfigRepository,
    history: HistoryRepository,
    *,
    timers: TimerPort,
    events: RoundEvents,
    clock: Clock,
    spawn: Spawn,
    rng: RandomSource | None = None,
) -> TaskWheelData:
    """Baut die Dienste; alle teilen Repositories, Events und den Statistik-Dienst."""
    statistics = StatisticsService(config, history)
    draws = DrawService(config, history, rng or secure_random(), statistics, events=events)
    assignments = AssignmentService(config, history, statistics, events)
    schedules = ScheduleService(config, history, draws, timers, events)
    return TaskWheelData(
        config=config,
        history=history,
        events=events,
        clock=clock,
        statistics=statistics,
        draws=draws,
        assignments=assignments,
        swaps=SwapService(config, history, statistics, events),
        schedules=schedules,
        maintenance=MaintenanceService(config, history, assignments, timers, spawn),
        history_service=HistoryService(history),
        entity_state=EntityStateService(config, history, schedules),
    )
