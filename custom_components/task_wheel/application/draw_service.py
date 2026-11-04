"""Runden auslosen: automatisch in einem Schritt oder schrittweise im Panel (KONZEPT §5.1)."""

import datetime as dt
from dataclasses import dataclass, replace

from ..const.defaults import PANEL_ROUND_TIMEOUT_MINUTES
from ..const.keys import (
    ERR_CANCEL_ADMIN_ONLY,
    ERR_DRAW_TOO_SOON,
    ERR_REPLACE_UNCONFIRMED,
    ERR_SCHEDULE_ARCHIVED,
    ERR_SCHEDULE_DISABLED,
    PH_SECONDS,
    RESOURCE_PANEL_ROUND,
    RESOURCE_PERSON,
    RESOURCE_SCHEDULE,
    RESOURCE_TASK,
)
from ..const.limits import DRAW_MIN_INTERVAL, DRAW_MIN_INTERVAL_SECONDS, MAX_OPEN_PANEL_ROUNDS
from ..domain.deadline import DeadlineWindow
from ..domain.draw.draft import RoundDraft
from ..domain.draw.engine import DrawEngine
from ..domain.draw.types import RandomSource, TaskDraw
from ..domain.draw.weighting import WeightingFactory
from ..domain.enums import RoundOrigin
from ..domain.errors import DrawRejectedError, LimitReachedError, NotFoundError
from ..domain.models import Round, Schedule
from ..domain.types import ScheduleId
from .draw_inputs import build_context, due_tasks, limit_to_participants, recent_assignments
from .ids import new_id
from .protocols import (
    AssignmentRecorder,
    ConfigRepository,
    HistoryRepository,
    IdFactory,
    NoEvents,
    RoundEvents,
)
from .runs import next_regular_run

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

    def draw(
        self,
        schedule_id: ScheduleId,
        origin: RoundOrigin,
        now: dt.datetime,
        window: DeadlineWindow | None = None,
    ) -> Round:
        """Löst eine Runde in einem Schritt aus und speichert sie.

        Ohne `window` gilt die Frist des Zeitplans, gerechnet ab `now`.

        Eine offene Panel-Runde desselben Zeitplans wird dabei verworfen, damit keine Runde
        doppelt entsteht.

        Raises:
            NotFoundError: Den Zeitplan gibt es nicht.
            DrawRejectedError: Der Zeitplan ist archiviert, (automatisch) pausiert, oder die letzte
                Auslosung von Hand liegt noch keine `DRAW_MIN_INTERVAL` zurück.
        """
        draft = self._start(schedule_id, origin, now, window)
        self.discard_for(schedule_id)
        return self._finish(draft.spin_rest(self._engine()), now)

    def begin(
        self,
        schedule_id: ScheduleId,
        now: dt.datetime,
        window: DeadlineWindow,
        *,
        replace_next: bool = False,
        is_admin: bool = True,
    ) -> PanelRound:
        """Beginnt eine Panel-Runde (Herkunft „manuell“); eine frühere desselben Plans entfällt.

        `window` ist Pflicht: ab wann die Aufgaben gelten und bis wann sie erledigt sein müssen.
        Hat der Zeitplan einen nächsten regulären Lauf, zieht die Runde ihn vor (er entfällt);
        das muss `replace_next` bestätigen.

        Eine schon gezogene Panel-Runde ersetzen nur Administratoren (kein Neuziehen nach Sicht).

        Raises:
            NotFoundError: Den Zeitplan gibt es nicht.
            DrawRejectedError: Der Zeitplan ist archiviert, der vorgezogene reguläre Lauf ist nicht
                bestätigt, oder eine schon gezogene Panel-Runde würde ersetzt und der Benutzer ist
                kein Administrator.
            LimitReachedError: Es sind schon zu viele Panel-Runden offen.
        """
        self._purge(now)
        draft = self._start(schedule_id, RoundOrigin.MANUAL, now, window)
        upcoming = self._upcoming(schedule_id, now)
        if upcoming is not None and not replace_next:
            raise DrawRejectedError(ERR_REPLACE_UNCONFIRMED)
        draft = replace(draft, replaces=upcoming)
        if not is_admin and self._has_results(schedule_id):
            raise DrawRejectedError(ERR_CANCEL_ADMIN_ONLY)
        self.discard_for(schedule_id)
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

    def preview(self, panel_round_id: str, now: dt.datetime) -> TaskDraw:
        """Das Rad der nächsten Aufgabe (Segmente, Ausschlüsse) ohne zu ziehen."""
        return self.get(panel_round_id, now).draft.preview(self._engine())

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
            NotFoundError: Die Panel-Runde gibt es nicht (mehr), oder eine gezogene Person, Aufgabe
                oder der Zeitplan wurde inzwischen gelöscht (die Panel-Runde entfällt dann).
            DrawRejectedError: Es sind noch nicht alle Aufgaben gezogen oder der Mindestabstand zur
                letzten Auslosung ist noch nicht erreicht (die Runde bleibt offen).
        """
        panel_round = self.get(panel_round_id, now)
        try:
            round_ = self._finish(panel_round.draft, now)
        except NotFoundError:
            del self._panel_rounds[panel_round_id]
            raise
        del self._panel_rounds[panel_round_id]
        return round_

    def cancel(self, panel_round_id: str, now: dt.datetime, *, is_admin: bool = True) -> None:
        """Verwirft die Panel-Runde ohne Wirkung auf Verlauf und Punkte.

        Raises:
            NotFoundError: Die Panel-Runde gibt es nicht (mehr).
            DrawRejectedError: Es wurde schon gezogen; Verwerfen nur für Administratoren.
        """
        panel_round = self.get(panel_round_id, now)
        if not is_admin and panel_round.draft.results:
            raise DrawRejectedError(ERR_CANCEL_ADMIN_ONLY)
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

    def _upcoming(self, schedule_id: ScheduleId, now: dt.datetime) -> dt.datetime | None:
        """Der nächste reguläre Lauf des Zeitplans, den eine manuelle Auslosung vorziehen würde."""
        return next_regular_run(self._history, self._config.schedules[schedule_id], now)

    def _start(
        self,
        schedule_id: ScheduleId,
        origin: RoundOrigin,
        now: dt.datetime,
        window: DeadlineWindow | None,
    ) -> RoundDraft:
        """Liest Konfiguration und Verlauf einmal und bildet den Ausgangsstand der Runde."""
        schedule = self._schedule(schedule_id, origin)
        recent = recent_assignments(self._history, now)
        context = build_context(
            self._config, self._history, recent, now, window or schedule.deadline.window(now)
        )
        tasks = limit_to_participants(
            due_tasks(self._config, schedule, recent, now), context, self._rng
        )
        return RoundDraft(schedule_id, origin, now, context, tasks)

    def _finish(self, draft: RoundDraft, now: dt.datetime) -> Round:
        """Macht aus dem Stand die Runde, speichert sie und meldet sie."""
        round_ = draft.to_round(self._new_id(), self._new_id, now)
        self._ensure_known(round_)
        self._ensure_not_flooded(draft, now)
        self._history.put_round(round_)
        self._recorder.record_round(round_)
        self._events.round_drawn(round_)
        return round_

    def _ensure_known(self, round_: Round) -> None:
        """Zeitplan, Personen und Aufgaben der Runde gibt es noch (sie wurden nicht gelöscht)."""
        known = (
            (RESOURCE_SCHEDULE, self._config.schedules, (round_.schedule_id,)),
            (RESOURCE_PERSON, self._config.persons, (a.person_id for a in round_.assignments)),
            (RESOURCE_TASK, self._config.tasks, (a.task_id for a in round_.assignments)),
        )
        for resource, items, ids in known:
            for item_id in ids:
                if item_id not in items:
                    raise NotFoundError(resource, item_id)

    def _ensure_not_flooded(self, draft: RoundDraft, now: dt.datetime) -> None:
        """Von Hand oder per Dienst ausgelöste Runden eines Zeitplans haben einen Mindestabstand."""
        if draft.origin is RoundOrigin.AUTO:
            return
        recent = self._history.rounds_since(now - DRAW_MIN_INTERVAL)
        if any(_is_manual_for(r, draft.schedule_id) for r in recent):
            raise DrawRejectedError(ERR_DRAW_TOO_SOON, {PH_SECONDS: DRAW_MIN_INTERVAL_SECONDS})

    def _store(self, panel_round: PanelRound) -> PanelRound:
        """Merkt sich die Panel-Runde."""
        self._panel_rounds[panel_round.id] = panel_round
        return panel_round

    def _has_results(self, schedule_id: ScheduleId) -> bool:
        """Hat eine Panel-Runde des Zeitplans schon Ergebnisse gezogen."""
        return any(
            item.draft.schedule_id == schedule_id and item.draft.results
            for item in self._panel_rounds.values()
        )

    def discard_for(self, schedule_id: ScheduleId) -> None:
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


def _is_manual_for(round_: Round, schedule_id: ScheduleId) -> bool:
    """Ob die Runde zum Zeitplan gehört und nicht automatisch ausgelost wurde."""
    return round_.schedule_id == schedule_id and round_.origin is not RoundOrigin.AUTO
