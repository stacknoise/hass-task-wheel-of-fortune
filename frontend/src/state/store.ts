import type { ApiClient, Delta, Snapshot, Unsubscribe } from '../api/index.ts';
import { applyDelta } from './delta.ts';
import { sortSnapshot } from './sort.ts';

export type LoadStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface StoreState {
  readonly status: LoadStatus;
  readonly snapshot: Snapshot | undefined;
}

type Listener = () => void;

const INITIAL_STATE: StoreState = { status: 'idle', snapshot: undefined };

/**
 * Hält den Stand des Panels: erst Abonnement, dann Snapshot, danach Deltas.
 *
 * Deltas, die vor dem Snapshot eintreffen, sind in ihm bereits enthalten (eine Verbindung, feste
 * Reihenfolge) und werden verworfen.
 */
export class Store {
  readonly #client: ApiClient;
  readonly #listeners = new Set<Listener>();
  #state: StoreState = INITIAL_STATE;
  #ready = false;
  #unwatch: Unsubscribe | undefined;
  #unsubscribe: Unsubscribe | undefined;
  /** Zählt Ladeversuche und Beenden; ein veralteter Ladevorgang gibt sein Abonnement sofort zurück. */
  #generation = 0;

  constructor(client: ApiClient) {
    this.#client = client;
  }

  /** Der Zugang zur API für Befehle (Auslosen, Erledigen …). */
  get client(): ApiClient {
    return this.#client;
  }

  get state(): StoreState {
    return this.#state;
  }

  /** Meldet einen Zuhörer an, der nach jeder Änderung des Standes aufgerufen wird. */
  listen(listener: Listener): Unsubscribe {
    this.#listeners.add(listener);
    return () => {
      this.#listeners.delete(listener);
    };
  }

  /** Lädt den Stand und hält ihn aktuell, auch nach einem Verbindungsabbruch. */
  async start(): Promise<void> {
    this.#unwatch = this.#client.onReconnect(() => void this.#load());
    await this.#load();
  }

  /** Lädt den Stand erneut (nach einem Fehler); ein laufender Ladevorgang wird abgelöst. */
  async reload(): Promise<void> {
    await this.#load();
  }

  /** Beendet Abonnement und Wiederverbindungs-Beobachtung. */
  stop(): void {
    this.#generation += 1;
    this.#unwatch?.();
    this.#unsubscribe?.();
    this.#unwatch = undefined;
    this.#unsubscribe = undefined;
    this.#ready = false;
  }

  async #load(): Promise<void> {
    const generation = ++this.#generation;
    this.#ready = false;
    this.#unsubscribe?.();
    this.#unsubscribe = undefined;
    this.#set({ status: 'loading', snapshot: this.#state.snapshot });
    try {
      const unsubscribe = await this.#client.subscribe((delta) => {
        this.#apply(delta);
      });
      if (generation !== this.#generation) {
        unsubscribe();
        return;
      }
      this.#unsubscribe = unsubscribe;
      const snapshot = await this.#client.snapshot();
      if (generation !== this.#generation) {
        return;
      }
      this.#ready = true;
      this.#set({ status: 'ready', snapshot: this.#sorted(snapshot) });
    } catch {
      if (generation === this.#generation) {
        this.#set({ status: 'error', snapshot: this.#state.snapshot });
      }
    }
  }

  #apply(delta: Delta): void {
    const { snapshot } = this.#state;
    if (this.#ready && snapshot) {
      this.#set({ status: 'ready', snapshot: this.#sorted(applyDelta(snapshot, delta)) });
    }
  }

  #sorted(snapshot: Snapshot): Snapshot {
    return sortSnapshot(snapshot, this.#client.language());
  }

  #set(state: StoreState): void {
    this.#state = state;
    for (const listener of this.#listeners) {
      listener();
    }
  }
}
