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
  /** Das Rad der nächsten Aufgabe vor dem Drehen (Segmente und Ausschlüsse, ohne Gewinner). */
  readonly preview: TaskDrawWire | undefined;
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
  preview: undefined,
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

  /**
   * Beginnt eine neue Runde für den Zeitplan (eine offene desselben Plans entfällt im Backend).
   * Ohne Animation (`animated` falsch) wird sofort alles gezogen und die Runde abgeschlossen.
   */
  async begin(scheduleId: string, animated = true): Promise<void> {
    if (!this.#idle()) {
      return;
    }
    await this.#run(async () => {
      this.#open(scheduleId, await this.#client.beginDraw(scheduleId));
      await this.#finishIfNothingPending();
      if (animated) {
        await this.#loadPreview();
      } else {
        await this.#drawRemaining();
      }
    });
  }

  /** Setzt eine offene Panel-Runde fort. */
  resume(round: PanelRoundWire): void {
    if (this.#idle()) {
      this.#open(round.schedule_id, round);
      void this.#loadPreview();
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
      this.#set({ phase: 'ready', current: undefined, preview: undefined });
      await this.#loadPreview();
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
    await this.#run(() => this.#drawRemaining());
  }

  /** Zieht alle übrigen Aufgaben der offenen Runde und schließt sie ab (nichts mehr offen: nichts tun). */
  async #drawRemaining(): Promise<void> {
    const { roundId, phase } = this.#state;
    if (!roundId || phase === 'done') {
      return;
    }
    const { results } = await this.#client.spinRest(roundId);
    this.#set({ results: [...this.#state.results, ...results], current: undefined });
    await this.#commitRound(roundId);
  }

  /** Verwirft eine offene Runde und beginnt wieder bei der Wahl des Zeitplans. */
  async restart(): Promise<void> {
    const { roundId, phase } = this.#state;
    this.#set({ ...INITIAL });
    if (roundId && phase !== 'done') {
      await this.#client.cancel(roundId).catch(() => undefined);
    }
  }

  /** Die aktuelle Phase, frisch gelesen (sie kann sich während eines Aufrufs ändern). */
  #phase(): DrawPhase {
    return this.#state.phase;
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

  /** Holt das Rad der nächsten Aufgabe; schlägt es fehl, bleibt das Rad vor dem Drehen leer. */
  async #loadPreview(): Promise<void> {
    const { roundId } = this.#state;
    if (this.#state.phase !== 'ready' || !roundId) {
      return;
    }
    try {
      const { result } = await this.#client.previewDraw(roundId);
      if (this.#state.roundId === roundId && this.#phase() === 'ready') {
        this.#set({ preview: result });
      }
    } catch {
      // Die Vorschau ist nur Anzeige; das Drehen funktioniert auch ohne sie.
    }
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
