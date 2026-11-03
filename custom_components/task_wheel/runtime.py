"""Komposition: verdrahtet alle Objekte an einer Stelle (Schicht 1, ohne Home Assistant)."""

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

from .application.assignment_service import AssignmentService
from .application.config_service import ConfigService
from .application.draw_service import DrawService
from .application.history_service import HistoryService
from .application.live_view import LiveView, ObservedTimers
from .application.maintenance_service import MaintenanceService, Spawn
from .application.notification_service import NotificationService
from .application.protocols import ConfigRepository, HistoryRepository, RoundEvents, TimerPort
from .application.schedule_service import ScheduleService
from .application.statistics_service import StatisticsService
from .application.swap_service import SwapService
from .application.views import SnapshotBuilder
from .domain.draw.engine import secure_random
from .domain.draw.types import RandomSource

type Clock = Callable[[], dt.datetime]


@dataclass(slots=True, frozen=True)
class TaskWheelData:
    """Alles, was eine geladene Config Entry braucht (`entry.runtime_data`)."""

    config: ConfigRepository
    history: HistoryRepository
    events: RoundEvents
    notifications: NotificationService
    clock: Clock
    statistics: StatisticsService
    draws: DrawService
    assignments: AssignmentService
    swaps: SwapService
    schedules: ScheduleService
    maintenance: MaintenanceService
    history_service: HistoryService
    configuration: ConfigService
    live: LiveView


def compose(
    config: ConfigRepository,
    history: HistoryRepository,
    *,
    timers: TimerPort,
    events: RoundEvents,
    notifications: NotificationService,
    clock: Clock,
    spawn: Spawn,
    rng: RandomSource | None = None,
) -> TaskWheelData:
    """Baut die Dienste; alle teilen Repositories, Events und den Statistik-Dienst.

    Abonnenten der Panel-API (`live`) sehen auch Änderungen, die kein Befehl ausgelöst hat:
    Änderungen der Konfiguration (egal von wo) und alles, was ein Zeitgeber auslöst
    (automatische Auslosung, Wartung).

    `notifications` hängt bereits hinter `events`; es wird hier nur für die Zielprüfung angeboten.
    """
    observed = ObservedTimers(timers)
    statistics = StatisticsService(config, history)
    draws = DrawService(config, history, rng or secure_random(), statistics, events=events)
    assignments = AssignmentService(config, history, statistics, events)
    swaps = SwapService(config, history, statistics, events)
    schedules = ScheduleService(config, history, draws, observed, events)
    live = LiveView(SnapshotBuilder(config, history, draws, swaps, schedules), clock)
    observed.listen(live.publish)
    config.subscribe(live.publish)
    return TaskWheelData(
        config=config,
        history=history,
        events=events,
        notifications=notifications,
        clock=clock,
        statistics=statistics,
        draws=draws,
        assignments=assignments,
        swaps=swaps,
        schedules=schedules,
        maintenance=MaintenanceService(config, history, assignments, observed, spawn),
        history_service=HistoryService(history),
        configuration=ConfigService(config, schedules, draws, notifications.check_target),
        live=live,
    )
