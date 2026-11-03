"""Runden auslosen: automatisch in einem Schritt oder schrittweise im Panel (KONZEPT §5.1)."""

import datetime as dt
from dataclasses import dataclass, replace

from ..const.defaults import PANEL_ROUND_TIMEOUT_MINUTES
from ..const.keys import ERR_SCHEDULE_ARCHIVED, ERR_SCHEDULE_DISABLED
from ..const.limits import MAX_OPEN_PANEL_ROUNDS
from ..domain.draw.draft import RoundDraft
from ..domain.draw.engine import DrawEngine
from ..domain.draw.types import RandomSource, TaskDraw
from ..domain.draw.weighting import WeightingFactory
from ..domain.enums import RoundOrigin
from ..domain.errors import DrawRejectedError, LimitReachedError, NotFoundError
from ..domain.models import Round, Schedule
from ..domain.types import ScheduleId
from .draw_inputs import build_context, due_tasks, recent_assignments
from .ids import new_id
from .protocols import (
    AssignmentRecorder,
    ConfigRepository,
    HistoryRepository,
    IdFactory,
    NoEvents,
    RoundEvents,
)

RESOURCE_SCHEDULE = "schedule"
RESOURCE_PANEL_ROUND = "panel_round"
_PANEL_TIMEOUT = dt.timedelta(minutes=PANEL_ROUND_TIMEOUT_MINUTES)


@dataclass(slots=True, frozen=True)
class PanelRound:
    """Offene Panel-Runde: der Stand der Ziehung und wann sie verfällt."""

    id: str
    draft: RoundDraft
    expires_at: dt.datetime


class DrawService:
    """Zieht Runden für einen Zeitplan; das Ergebnis bestimmt immer das Backend."""

    def __init__(
        self,
        config: ConfigRepository,
        history: HistoryRepository,
        rng: RandomSource,
        recorder: AssignmentRecorder,
        *,
        events: RoundEvents | None = None,
        id_factory: IdFactory = new_id,
    ) -> None:
        """Hält Repositories, Zufallsquelle, Statistik, Ereignisempfänger und Kennungsquelle."""
        self._config = config
        self._history = history
        self._rng = rng
        self._recorder = recorder
        self._events = events or NoEvents()
        self._new_id = id_factory
        self._panel_rounds: dict[str, PanelRound] = {}

    def draw(self, schedule_id: ScheduleId, origin: RoundOrigin, now: dt.datetime) -> Round:
        """Löst eine Runde in einem Schritt aus und speichert sie.

        Eine offene Panel-Runde desselben Zeitplans wird dabei verworfen, damit keine Runde
        doppelt entsteht.

        Raises:
            NotFoundError: Den Zeitplan gibt es nicht.
            DrawRejectedError: Der Zeitplan ist archiviert, oder (automatisch) pausiert.
        """
        draft = self._start(schedule_id, origin, now)
        self._discard_for(schedule_id)
        return self._finish(draft.spin_rest(self._engine()), now)

    def begin(self, schedule_id: ScheduleId, now: dt.datetime) -> PanelRound:
        """Beginnt eine Panel-Runde (Herkunft „manuell“); eine frühere desselben Plans entfällt.

        Raises:
            NotFoundError: Den Zeitplan gibt es nicht.
            DrawRejectedError: Der Zeitplan ist archiviert.
            LimitReachedError: Es sind schon zu viele Panel-Runden offen.
        """
        self._purge(now)
        draft = self._start(schedule_id, RoundOrigin.MANUAL, now)
        self._discard_for(schedule_id)
        if len(self._panel_rounds) >= MAX_OPEN_PANEL_ROUNDS:
            raise LimitReachedError(RESOURCE_PANEL_ROUND, MAX_OPEN_PANEL_ROUNDS)
        return self._store(PanelRound(self._new_id(), draft, now + _PANEL_TIMEOUT))

    def get(self, panel_round_id: str, now: dt.datetime) -> PanelRound:
        """Liefert die offene Panel-Runde.

        Raises:
            NotFoundError: Sie ist unbekannt, abgebrochen, abgeschlossen oder verfallen.
        """
        self._purge(now)
        panel_round = self._panel_rounds.get(panel_round_id)
        if panel_round is None:
            raise NotFoundError(RESOURCE_PANEL_ROUND, panel_round_id)
        return panel_round

    def spin(self, panel_round_id: str, now: dt.datetime) -> TaskDraw:
        """Zieht die nächste Aufgabe der Panel-Runde und liefert deren Ergebnis."""
        panel_round = self.get(panel_round_id, now)
        updated = self._store(replace(panel_round, draft=panel_round.draft.spin(self._engine())))
        return updated.draft.results[-1]

    def spin_rest(self, panel_round_id: str, now: dt.datetime) -> tuple[TaskDraw, ...]:
        """Zieht alle übrigen Aufgaben und liefert deren Ergebnisse."""
        panel_round = self.get(panel_round_id, now)
        before = len(panel_round.draft.results)
        updated = self._store(
            replace(panel_round, draft=panel_round.draft.spin_rest(self._engine()))
        )
        return updated.draft.results[before:]

    def commit(self, panel_round_id: str, now: dt.datetime) -> Round:
        """Schließt die vollständig gezogene Panel-Runde ab und speichert sie.

        Raises:
            NotFoundError: Die Panel-Runde gibt es nicht (mehr).
            DrawRejectedError: Es sind noch nicht alle Aufgaben gezogen (die Runde bleibt offen).
        """
        panel_round = self.get(panel_round_id, now)
        round_ = self._finish(panel_round.draft, now)
        del self._panel_rounds[panel_round_id]
        return round_

    def cancel(self, panel_round_id: str, now: dt.datetime) -> None:
        """Verwirft die Panel-Runde ohne Wirkung auf Verlauf und Punkte."""
        self.get(panel_round_id, now)
        del self._panel_rounds[panel_round_id]

    def open_rounds(self, now: dt.datetime) -> tuple[PanelRound, ...]:
        """Alle noch gültigen Panel-Runden."""
        self._purge(now)
        return tuple(self._panel_rounds.values())

    def _engine(self) -> DrawEngine:
        """Engine mit der in den Einstellungen gewählten Gewichtung."""
        return DrawEngine(WeightingFactory.create(self._config.settings.weighting), self._rng)

    def _schedule(self, schedule_id: ScheduleId, origin: RoundOrigin) -> Schedule:
        """Der Zeitplan, sofern er ausgelost werden darf (Pausierte nur von Hand)."""
        schedule = self._config.schedules.get(schedule_id)
        if schedule is None:
            raise NotFoundError(RESOURCE_SCHEDULE, schedule_id)
        if schedule.archived:
            raise DrawRejectedError(ERR_SCHEDULE_ARCHIVED)
        if origin is RoundOrigin.AUTO and not schedule.enabled:
            raise DrawRejectedError(ERR_SCHEDULE_DISABLED)
        return schedule

    def _start(self, schedule_id: ScheduleId, origin: RoundOrigin, now: dt.datetime) -> RoundDraft:
        """Liest Konfiguration und Verlauf einmal und bildet den Ausgangsstand der Runde."""
        schedule = self._schedule(schedule_id, origin)
        recent = recent_assignments(self._history, now)
        tasks = due_tasks(self._config, schedule, recent, now)
        context = build_context(self._config, self._history, recent, now)
        return RoundDraft(schedule_id, origin, now, context, tasks)

    def _finish(self, draft: RoundDraft, now: dt.datetime) -> Round:
        """Macht aus dem Stand die Runde, speichert sie und meldet sie."""
        round_ = draft.to_round(self._new_id(), self._new_id, now)
        self._history.put_round(round_)
        self._recorder.record_round(round_)
        self._events.round_drawn(round_)
        return round_

    def _store(self, panel_round: PanelRound) -> PanelRound:
        """Merkt sich die Panel-Runde."""
        self._panel_rounds[panel_round.id] = panel_round
        return panel_round

    def _discard_for(self, schedule_id: ScheduleId) -> None:
        """Verwirft offene Panel-Runden des Zeitplans."""
        stale = [
            key for key, item in self._panel_rounds.items() if item.draft.schedule_id == schedule_id
        ]
        for key in stale:
            del self._panel_rounds[key]

    def _purge(self, now: dt.datetime) -> None:
        """Entfernt verfallene Panel-Runden."""
        expired = [key for key, item in self._panel_rounds.items() if item.expires_at <= now]
        for key in expired:
            del self._panel_rounds[key]
