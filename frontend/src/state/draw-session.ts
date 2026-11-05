import type {
  ApiClient,
  DrawWindowRequest,
  PanelRoundWire,
  TaskDrawWire,
  TaskReplacementWire,
} from '../api/index.ts';
import { DRAW_PHASE, DRAW_UNKNOWN_ERROR } from '../constants/index.ts';
import type { DrawPhase } from '../constants/index.ts';

export type { DrawPhase } from '../constants/index.ts';

export interface DrawState {
  readonly phase: DrawPhase;
  readonly scheduleId: string | undefined;
  readonly roundId: string | undefined;
  /** Alle Aufgaben der Runde in der Reihenfolge der Ziehung. */
  readonly taskIds: readonly string[];
  /** Die bisher gezogenen Ergebnisse (gleiche Reihenfolge). */
  readonly results: readonly TaskDrawWire[];
  /** Das Ergebnis, das gerade gedreht oder gezeigt wird. */
  readonly current: TaskDrawWire | undefined;
  /** Das Rad der nächsten Aufgabe vor dem Drehen (Segmente und Ausschlüsse, ohne Gewinner). */
  readonly preview: TaskDrawWire | undefined;
  readonly errorCode: string | undefined;
  /** Vorbereitung ohne Animation: die Runde steht bereit und wird direkt verteilt (kein Rad). */
  readonly direct: boolean;
}

type Listener = () => void;

/** Fragt, ob der laufende Schritt noch gilt (nach „Neu starten“ gilt er nicht mehr). */
type Alive = () => boolean;

const INITIAL: DrawState = {
  phase: DRAW_PHASE.choose,
  scheduleId: undefined,
  roundId: undefined,
  taskIds: [],
  results: [],
  current: undefined,
  preview: undefined,
  errorCode: undefined,
  direct: false,
};

/** Wartet die Auslosung auf eine Wahl (noch keine Runde oder ein Fehler)? */
export const isIdle = (state: DrawState): boolean =>
  state.phase === DRAW_PHASE.choose || state.phase === DRAW_PHASE.error;

/** Wie viele Ergebnisse schon gezeigt werden dürfen: das gerade drehende bleibt verborgen. */
export const shownCount = (state: DrawState): number =>
  state.phase === DRAW_PHASE.spinning ? state.results.length - 1 : state.results.length;

/** Darf der Admin jetzt Aufgaben der Runde tauschen? Nur vor dem Start, also vor dem ersten Dreh. */
export const canReplace = (state: DrawState): boolean =>
  state.phase === DRAW_PHASE.ready && state.results.length === 0 && state.roundId !== undefined;

/** Wartet die animierte Runde auf den nächsten Dreh (nicht die Vorbereitung ohne Animation)? */
export const awaitsSpin = (state: DrawState): boolean =>
  state.phase === DRAW_PHASE.ready && !state.direct;

const isPausedInRound = (state: DrawState): boolean =>
  state.phase === DRAW_PHASE.ready || state.phase === DRAW_PHASE.revealed;

/** Bietet die Ansicht „Rest ohne Animation ziehen“ an? */
export const canSkip = (state: DrawState): boolean =>
  isPausedInRound(state) && shownCount(state) < state.taskIds.length;

/**
 * Ablauf einer manuellen Auslosung: Runde beginnen, je Aufgabe drehen, abschließen.
 *
 * Das Ergebnis jeder Ziehung kommt vom Backend; die Sitzung merkt es sich nur und führt die
 * Ansicht durch die Schritte. Aktionen außerhalb ihrer Phase werden ignoriert (Doppelklick).
 * Antworten, die nach „Neu starten“ eintreffen, werden verworfen.
 */
export class DrawSession {
  readonly #client: ApiClient;
  readonly #listeners = new Set<Listener>();
  #state: DrawState = INITIAL;
  /** Wächst mit jedem Neustart; Schritte aus einer älteren Generation schreiben nichts mehr. */
  #generation = 0;

  constructor(client: ApiClient) {
    this.#client = client;
  }

  get state(): DrawState {
    return this.#state;
  }

  listen(listener: Listener): () => void {
    this.#listeners.add(listener);
    return () => {
      this.#listeners.delete(listener);
    };
  }

  /**
   * Beginnt eine neue Runde für den Zeitplan (eine offene desselben Plans entfällt im Backend);
   * `window` sagt, ab wann die Aufgaben gelten und bis wann sie erledigt sein müssen.
   * Ohne Animation (`animated` falsch) wird sofort alles gezogen und die Runde abgeschlossen;
   * mit `prepare` bleibt die Runde stattdessen bereit (zum Austauschen von Aufgaben), bis der
   * Benutzer „direkt verteilen“ wählt.
   */
  async begin(
    scheduleId: string,
    window: DrawWindowRequest,
    animated = true,
    prepare = false,
  ): Promise<void> {
    if (!isIdle(this.#state)) {
      return;
    }
    await this.#run(async (alive) => {
      const round = await this.#client.beginDraw(scheduleId, window);
      if (!alive()) {
        return;
      }
      this.#open(scheduleId, round);
      await this.#finishIfNothingPending(alive);
      if (animated) {
        await this.#loadPreview();
      } else if (prepare) {
        this.#set({ direct: true });
      } else {
        await this.#drawRemaining(alive);
      }
    });
  }

  /** Setzt eine offene Panel-Runde fort. */
  resume(round: PanelRoundWire): void {
    if (isIdle(this.#state)) {
      this.#open(round.schedule_id, round);
      void this.#loadPreview();
    }
  }

  /** Aufgaben, die statt `taskId` dienen könnten (leer, wenn der Tausch gesperrt ist). */
  async replacements(taskId: string): Promise<readonly TaskReplacementWire[]> {
    const roundId = this.#state.roundId;
    if (!canReplace(this.#state) || !roundId) {
      return [];
    }
    return (await this.#client.replacements(roundId, taskId)).replacements;
  }

  /** Tauscht vor dem Start eine Aufgabe der Runde; Fehler des Backends werden angezeigt. */
  async replaceTask(taskId: string, newTaskId: string): Promise<void> {
    const roundId = this.#state.roundId;
    if (!canReplace(this.#state) || !roundId) {
      return;
    }
    await this.#run(async (alive) => {
      const { panel_round: round } = await this.#client.replaceTask(roundId, taskId, newTaskId);
      if (alive()) {
        this.#set({
          phase: DRAW_PHASE.ready,
          taskIds: [...round.results.map((result) => result.task_id), ...round.pending_task_ids],
          preview: undefined,
        });
        await this.#loadPreview();
      }
    });
  }

  /** Zieht die nächste Aufgabe; die Ansicht dreht das Rad danach zum Gewinner. */
  async spin(): Promise<void> {
    const roundId = this.#state.roundId;
    if (this.#state.phase !== DRAW_PHASE.ready || !roundId) {
      return;
    }
    await this.#run(async (alive) => {
      const { result } = await this.#client.spin(roundId);
      if (alive()) {
        this.#set({
          phase: DRAW_PHASE.spinning,
          results: [...this.#state.results, result],
          current: result,
        });
      }
    });
  }

  /** Das Rad steht: das Ergebnis wird angezeigt. */
  landed(): void {
    if (this.#state.phase === DRAW_PHASE.spinning) {
      this.#set({ phase: DRAW_PHASE.revealed });
    }
  }

  /** Weiter zur nächsten Aufgabe oder, nach der letzten, die Runde abschließen. */
  async next(): Promise<void> {
    if (this.#state.phase !== DRAW_PHASE.revealed) {
      return;
    }
    if (this.#pending() > 0) {
      this.#set({ phase: DRAW_PHASE.ready, current: undefined, preview: undefined });
      await this.#loadPreview();
      return;
    }
    await this.#commit();
  }

  /** Zieht alle übrigen Aufgaben ohne Animation und schließt die Runde ab. */
  async drawRest(): Promise<void> {
    if (!isPausedInRound(this.#state) || !this.#state.roundId) {
      return;
    }
    await this.#run((alive) => this.#drawRemaining(alive));
  }

  /** Verwirft eine offene Runde und beginnt wieder bei der Wahl des Zeitplans. */
  async restart(): Promise<void> {
    const { roundId, phase } = this.#state;
    this.#generation += 1;
    this.#set({ ...INITIAL });
    if (roundId && phase !== DRAW_PHASE.done) {
      await this.#client.cancel(roundId).catch(() => undefined);
    }
  }

  /** Zieht alle übrigen Aufgaben der offenen Runde und schließt sie ab (nichts mehr offen: nichts tun). */
  async #drawRemaining(alive: Alive): Promise<void> {
    const { roundId, phase } = this.#state;
    if (!roundId || phase === DRAW_PHASE.done) {
      return;
    }
    const { results } = await this.#client.spinRest(roundId);
    if (alive()) {
      this.#set({ results: [...this.#state.results, ...results], current: undefined });
      await this.#commitRound(roundId, alive);
    }
  }

  /** Die aktuelle Phase, frisch gelesen (sie kann sich während eines Aufrufs ändern). */
  #phase(): DrawPhase {
    return this.#state.phase;
  }

  #pending(): number {
    return this.#state.taskIds.length - this.#state.results.length;
  }

  #open(scheduleId: string, round: PanelRoundWire): void {
    this.#set({
      ...INITIAL,
      phase: DRAW_PHASE.ready,
      scheduleId,
      roundId: round.id,
      taskIds: [...round.results.map((result) => result.task_id), ...round.pending_task_ids],
      results: round.results,
    });
  }

  /** Holt das Rad der nächsten Aufgabe; schlägt es fehl, bleibt das Rad vor dem Drehen leer. */
  async #loadPreview(): Promise<void> {
    const { roundId } = this.#state;
    if (this.#state.phase !== DRAW_PHASE.ready || !roundId) {
      return;
    }
    try {
      const { result } = await this.#client.previewDraw(roundId);
      if (this.#state.roundId === roundId && this.#phase() === DRAW_PHASE.ready) {
        this.#set({ preview: result });
      }
    } catch {
      // Die Vorschau ist nur Anzeige; das Drehen funktioniert auch ohne sie.
    }
  }

  async #finishIfNothingPending(alive: Alive): Promise<void> {
    if (this.#pending() === 0 && this.#state.roundId) {
      await this.#commitRound(this.#state.roundId, alive);
    }
  }

  async #commit(): Promise<void> {
    const roundId = this.#state.roundId;
    if (roundId) {
      await this.#run((alive) => this.#commitRound(roundId, alive));
    }
  }

  async #commitRound(roundId: string, alive: Alive): Promise<void> {
    await this.#client.commit(roundId);
    if (alive()) {
      this.#set({ phase: DRAW_PHASE.done, current: undefined });
    }
  }

  /** Führt einen Schritt aus, der die Phase selbst weiterschaltet; ein Fehler beendet ihn. */
  async #run(step: (alive: Alive) => Promise<void>): Promise<void> {
    const generation = this.#generation;
    const alive: Alive = () => generation === this.#generation;
    this.#set({ phase: DRAW_PHASE.busy });
    try {
      await step(alive);
    } catch (error) {
      if (alive()) {
        this.#set({ phase: DRAW_PHASE.error, errorCode: errorCode(error) });
      }
    }
  }

  #set(patch: Partial<DrawState>): void {
    this.#state = { ...this.#state, ...patch };
    for (const listener of this.#listeners) {
      listener();
    }
  }
}

function errorCode(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'code' in error) {
    const code = error.code;
    if (typeof code === 'string') {
      return code;
    }
  }
  return DRAW_UNKNOWN_ERROR;
}
