"""Komposition: verdrahtet alle Objekte an einer Stelle (Schicht 1, ohne Home Assistant)."""

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

from .application.assignment_service import AssignmentService
from .application.config_service import ConfigService
from .application.decision_service import DecisionService
from .application.draw_service import DrawService
from .application.entity_state import EntityStateService
from .application.history_service import HistoryService
from .application.live_view import AccessWatch, LiveView, ObservedTimers
from .application.maintenance_service import MaintenanceService, Spawn
from .application.notification_service import NotificationService
from .application.protocols import (
    ConfigRepository,
    DecisionRepository,
    HistoryRepository,
    RoundEvents,
    TimerPort,
)
from .application.round_service import RoundService
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
    decision_repo: DecisionRepository
    events: RoundEvents
    notifications: NotificationService
    clock: Clock
    statistics: StatisticsService
    draws: DrawService
    assignments: AssignmentService
    rounds: RoundService
    swaps: SwapService
    schedules: ScheduleService
    maintenance: MaintenanceService
    history_service: HistoryService
    decision_service: DecisionService
    entity_state: EntityStateService
    configuration: ConfigService
    live: LiveView


def compose(
    config: ConfigRepository,
    history: HistoryRepository,
    decision_repo: DecisionRepository,
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
    decisions = DecisionService(config, decision_repo)
    draws = DrawService(
        config, history, rng or secure_random(), statistics, events=events, decisions=decisions
    )
    assignments = AssignmentService(config, history, statistics, events)
    swaps = SwapService(config, history, statistics, events, decisions)
    schedules = ScheduleService(config, history, draws, observed, events)
    live = LiveView(SnapshotBuilder(config, history, draws, schedules), clock)
    observed.listen(live.publish)
    config.subscribe(AccessWatch(live, lambda: config.settings.panel_admin_only).check)
    config.subscribe(live.publish)
    return TaskWheelData(
        config=config,
        history=history,
        decision_repo=decision_repo,
        events=events,
        notifications=notifications,
        clock=clock,
        statistics=statistics,
        draws=draws,
        assignments=assignments,
        rounds=RoundService(history, statistics, events),
        swaps=swaps,
        schedules=schedules,
        maintenance=MaintenanceService(
            config, history, assignments, observed, spawn, decisions=decisions
        ),
        history_service=HistoryService(history),
        decision_service=decisions,
        configuration=ConfigService(config, history, schedules, draws, notifications.check_target),
        live=live,
        entity_state=EntityStateService(config, history, schedules),
    )
