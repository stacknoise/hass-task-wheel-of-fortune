import type { ApiClient, PanelRoundWire, TaskDrawWire } from '../api/index.ts';

export type DrawPhase = 'choose' | 'busy' | 'ready' | 'spinning' | 'revealed' | 'done' | 'error';

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
  readonly errorCode: string | undefined;
}

type Listener = () => void;

const INITIAL: DrawState = {
  phase: 'choose',
  scheduleId: undefined,
  roundId: undefined,
  taskIds: [],
  results: [],
  current: undefined,
  errorCode: undefined,
};
const UNKNOWN_ERROR = 'unknown';

/**
 * Ablauf einer manuellen Auslosung: Runde beginnen, je Aufgabe drehen, abschließen.
 *
 * Das Ergebnis jeder Ziehung kommt vom Backend; die Sitzung merkt es sich nur und führt die
 * Ansicht durch die Schritte. Aktionen außerhalb ihrer Phase werden ignoriert (Doppelklick).
 */
export class DrawSession {
  readonly #client: ApiClient;
  readonly #listeners = new Set<Listener>();
  #state: DrawState = INITIAL;

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

  /** Beginnt eine neue Runde für den Zeitplan (eine offene desselben Plans entfällt im Backend). */
  async begin(scheduleId: string): Promise<void> {
    if (!this.#idle()) {
      return;
    }
    await this.#run(async () => {
      this.#open(scheduleId, await this.#client.beginDraw(scheduleId));
      return this.#finishIfNothingPending();
    });
  }

  /** Setzt eine offene Panel-Runde fort. */
  resume(round: PanelRoundWire): void {
    if (this.#idle()) {
      this.#open(round.schedule_id, round);
    }
  }

  /** Zieht die nächste Aufgabe; die Ansicht dreht das Rad danach zum Gewinner. */
  async spin(): Promise<void> {
    const roundId = this.#state.roundId;
    if (this.#state.phase !== 'ready' || !roundId) {
      return;
    }
    await this.#run(async () => {
      const { result } = await this.#client.spin(roundId);
      this.#set({
        phase: 'spinning',
        results: [...this.#state.results, result],
        current: result,
      });
    });
  }

  /** Das Rad steht: das Ergebnis wird angezeigt. */
  landed(): void {
    if (this.#state.phase === 'spinning') {
      this.#set({ phase: 'revealed' });
    }
  }

  /** Weiter zur nächsten Aufgabe oder, nach der letzten, die Runde abschließen. */
  async next(): Promise<void> {
    if (this.#state.phase !== 'revealed') {
      return;
    }
    if (this.#pending() > 0) {
      this.#set({ phase: 'ready', current: undefined });
      return;
    }
    await this.#commit();
  }

  /** Zieht alle übrigen Aufgaben ohne Animation und schließt die Runde ab. */
  async drawRest(): Promise<void> {
    const roundId = this.#state.roundId;
    if ((this.#state.phase !== 'ready' && this.#state.phase !== 'revealed') || !roundId) {
      return;
    }
    await this.#run(async () => {
      const { results } = await this.#client.spinRest(roundId);
      this.#set({ results: [...this.#state.results, ...results], current: undefined });
      await this.#commitRound(roundId);
    });
  }

  /** Verwirft eine offene Runde und beginnt wieder bei der Wahl des Zeitplans. */
  async restart(): Promise<void> {
    const { roundId, phase } = this.#state;
    this.#set({ ...INITIAL });
    if (roundId && phase !== 'done') {
      await this.#client.cancel(roundId).catch(() => undefined);
    }
  }

  #idle(): boolean {
    return this.#state.phase === 'choose' || this.#state.phase === 'error';
  }

  #pending(): number {
    return this.#state.taskIds.length - this.#state.results.length;
  }

  #open(scheduleId: string, round: PanelRoundWire): void {
    this.#set({
      ...INITIAL,
      phase: 'ready',
      scheduleId,
      roundId: round.id,
      taskIds: [...round.results.map((result) => result.task_id), ...round.pending_task_ids],
      results: round.results,
    });
  }

  async #finishIfNothingPending(): Promise<void> {
    if (this.#pending() === 0 && this.#state.roundId) {
      await this.#commitRound(this.#state.roundId);
    }
  }

  async #commit(): Promise<void> {
    const roundId = this.#state.roundId;
    if (roundId) {
      await this.#run(() => this.#commitRound(roundId));
    }
  }

  async #commitRound(roundId: string): Promise<void> {
    await this.#client.commit(roundId);
    this.#set({ phase: 'done', current: undefined });
  }

  /** Führt einen Schritt aus, der die Phase selbst weiterschaltet; ein Fehler beendet ihn. */
  async #run(step: () => Promise<void>): Promise<void> {
    this.#set({ phase: 'busy' });
    try {
      await step();
    } catch (error) {
      this.#set({ phase: 'error', errorCode: errorCode(error) });
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
  return UNKNOWN_ERROR;
}
