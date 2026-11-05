"""Runden auslosen: automatisch in einem Schritt oder schrittweise im Panel (KONZEPT §5.1)."""

import datetime as dt
from dataclasses import dataclass, replace

from ..const.defaults import PANEL_ROUND_TIMEOUT_MINUTES
from ..const.keys import (
    ERR_CANCEL_ADMIN_ONLY,
    ERR_DRAW_STARTED,
    ERR_DRAW_TOO_SOON,
    ERR_NOTHING_DUE,
    ERR_REPLACE_UNCONFIRMED,
    ERR_REPLACEMENT_INFEASIBLE,
    ERR_REPLACEMENT_INVALID,
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
from ..domain.draw.feasibility import assignable_tasks, is_feasible
from ..domain.draw.types import RandomSource, TaskDraw, TaskReplacement
from ..domain.draw.weighting import WeightingFactory
from ..domain.enums import RoundOrigin
from ..domain.errors import DrawRejectedError, LimitReachedError, NotFoundError
from ..domain.models import Round, Schedule, Task
from ..domain.types import ScheduleId
from .draw_inputs import (
    build_context,
    due_tasks,
    limit_to_participants,
    recent_assignments,
    respecting_schedule,
)
from .ids import new_id
from .protocols import (
    AssignmentRecorder,
    ConfigRepository,
    DecisionRecorder,
    HistoryRepository,
    IdFactory,
    NoDecisions,
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
        decisions: DecisionRecorder | None = None,
        id_factory: IdFactory = new_id,
    ) -> None:
        """Hält Repositories, Zufallsquelle, Statistik, Ereignisempfänger, Log und Kennungen."""
        self._config = config
        self._history = history
        self._rng = rng
        self._recorder = recorder
        self._events = events or NoEvents()
        self._decisions = decisions or NoDecisions()
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
            DrawRejectedError: Der Zeitplan ist archiviert, (automatisch) pausiert, nichts ist
                fällig (alle Aufgaben am Maximum ihrer Häufigkeit oder niemand verfügbar), oder die
                letzte Auslosung von Hand liegt noch keine `DRAW_MIN_INTERVAL` zurück.
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
            DrawRejectedError: Der Zeitplan ist archiviert, nichts ist fällig, der vorgezogene
                reguläre Lauf ist nicht bestätigt, oder eine schon gezogene Panel-Runde würde
                ersetzt und der Benutzer ist kein Administrator.
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

    def replacements(
        self, panel_round_id: str, task_id: str, now: dt.datetime
    ) -> tuple[TaskReplacement, ...]:
        """Aufgaben des Zeitplans außerhalb der Runde und ob sie `task_id` ersetzen können.

        Machbar heißt: mindestens eine Person, die im Fenster mitlosen darf, könnte sie übernehmen,
        und die Runde bleibt danach mindestens so vollständig vergebbar wie vorher (je Person
        höchstens eine Aufgabe). Nach dem Start der Auslosung gibt es keine (Tausch gesperrt).

        Raises:
            NotFoundError: Die Panel-Runde oder der Zeitplan gibt es nicht (mehr).
            DrawRejectedError: `task_id` gehört nicht zur Runde.
        """
        draft = self.get(panel_round_id, now).draft
        taken = {task.id for task in draft.tasks}
        if task_id not in taken:
            raise DrawRejectedError(ERR_REPLACEMENT_INVALID)
        if draft.started:
            return ()
        schedule = self._known_schedule(draft.schedule_id)
        kept = assignable_tasks(draft.tasks, draft.context)
        return tuple(
            TaskReplacement(task.id, self._keeps_round(draft, task_id, task, kept))
            for task in self._schedule_tasks(schedule)
            if task.id not in taken
        )

    def _schedule_tasks(self, schedule: Schedule) -> tuple[Task, ...]:
        """Die Aufgaben des Zeitplans (bekannte, mit den Vorgaben des Zeitplans)."""
        found = (self._config.tasks.get(task_id) for task_id in schedule.task_ids)
        return tuple(respecting_schedule(schedule, task) for task in found if task is not None)

    @staticmethod
    def _keeps_round(draft: RoundDraft, task_id: str, new_task: Task, kept: int) -> bool:
        """Ob `new_task` statt `task_id` machbar ist und die Runde nicht schlechter vergibt."""
        if not is_feasible(new_task, draft.context):
            return False
        swapped = [new_task if task.id == task_id else task for task in draft.tasks]
        return assignable_tasks(swapped, draft.context) >= kept

    def replace_task(
        self, panel_round_id: str, task_id: str, new_task_id: str, now: dt.datetime
    ) -> PanelRound:
        """Tauscht vor dem Start der Auslosung eine Aufgabe der Runde gegen eine andere.

        Raises:
            NotFoundError: Die Panel-Runde, der Zeitplan oder die neue Aufgabe gibt es nicht.
            DrawRejectedError: Es wurde schon gezogen, die neue Aufgabe gehört nicht zum Zeitplan
                oder ist schon in der Runde, oder keine anwesende Person könnte sie übernehmen.
        """
        panel_round = self.get(panel_round_id, now)
        if panel_round.draft.started:
            raise DrawRejectedError(ERR_DRAW_STARTED)
        options = {item.task_id: item for item in self.replacements(panel_round_id, task_id, now)}
        option = options.get(new_task_id)
        if option is None:
            raise DrawRejectedError(ERR_REPLACEMENT_INVALID)
        if not option.doable:
            raise DrawRejectedError(ERR_REPLACEMENT_INFEASIBLE)
        schedule = self._known_schedule(panel_round.draft.schedule_id)
        new_task = respecting_schedule(schedule, self._config.tasks[new_task_id])
        draft = panel_round.draft.replace_task(task_id, new_task)
        self._decisions.record_replacement(draft.schedule_id, task_id, new_task_id, now)
        return self._store(replace(panel_round, draft=draft))

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

    def _known_schedule(self, schedule_id: ScheduleId) -> Schedule:
        """Der Zeitplan der Runde; er kann inzwischen gelöscht sein."""
        schedule = self._config.schedules.get(schedule_id)
        if schedule is None:
            raise NotFoundError(RESOURCE_SCHEDULE, schedule_id)
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
        if not tasks:
            raise DrawRejectedError(ERR_NOTHING_DUE)
        return RoundDraft(schedule_id, origin, now, context, tasks)

    def _finish(self, draft: RoundDraft, now: dt.datetime) -> Round:
        """Macht aus dem Stand die Runde, speichert sie und meldet sie."""
        round_ = draft.to_round(self._new_id(), self._new_id, now)
        self._ensure_known(round_)
        self._ensure_not_flooded(draft, now)
        self._history.put_round(round_)
        self._recorder.record_round(round_)
        self._decisions.record_draw(draft, round_)
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
