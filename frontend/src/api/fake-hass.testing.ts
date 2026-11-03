import type { Delta, HassApi, Snapshot } from './index.ts';

function person(id: string): Record<string, unknown> & { id: string } {
  return {
    id,
    name: id,
    slug: id,
    color: '#4f8cff',
    load: 'full',
    absences: [],
    notify_target: null,
  };
}

export const EMPTY_SNAPSHOT: Snapshot = {
  persons: [person('p1'), person('p2')],
  tasks: [
    {
      id: 't1',
      name: 'Aufgabe',
      allowed: ['p1', 'p2'],
      frequency: { kind: 'every_round' },
      points: 1,
      due_days: 7,
      no_repeat: false,
      respect_absence: true,
      swap_allowed: true,
    },
  ],
  schedules: [],
  assignments: [],
  panel_rounds: [],
  settings: {},
  now: '2026-11-03T12:00:00+00:00',
};

/** Ein `hass`-Ersatz, der Snapshot und Deltas kontrolliert liefert. */
export class FakeHass implements HassApi {
  readonly language = 'de';
  readonly calls: string[] = [];
  snapshot: Snapshot = EMPTY_SNAPSHOT;
  failSnapshot = false;
  unsubscribed = 0;
  #onDelta: ((delta: Delta) => void) | undefined;
  readonly #listeners = new Set<() => void>();

  readonly connection = {
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters
    subscribeMessage: <T>(callback: (message: T) => void, message: { type: string }) => {
      this.calls.push(message.type);
      this.#onDelta = callback as unknown as (delta: Delta) => void;
      return Promise.resolve(() => {
        this.unsubscribed += 1;
      });
    },
    addEventListener: (_type: string, listener: () => void) => {
      this.#listeners.add(listener);
    },
    removeEventListener: (_type: string, listener: () => void) => {
      this.#listeners.delete(listener);
    },
  };

  /** Alle Nachrichten mit Feldern, in der Reihenfolge der Aufrufe. */
  readonly messages: { type: string; [field: string]: unknown }[] = [];
  /** Fehler, mit dem der nächste Aufruf eines Befehls ungleich `snapshot` scheitert. */
  rejectNext: unknown;

  callWS<T>(message: { type: string; [field: string]: unknown }): Promise<T> {
    this.calls.push(message.type);
    this.messages.push(message);
    if (this.rejectNext !== undefined && !message.type.endsWith('snapshot')) {
      const error = this.rejectNext;
      this.rejectNext = undefined;
      // Home Assistant lehnt mit einfachen Objekten ab (`{ code, message }`), nicht mit `Error`.
      // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors
      return Promise.reject(error);
    }
    return this.failSnapshot
      ? Promise.reject(new Error('offline'))
      : Promise.resolve(this.snapshot as unknown as T);
  }

  emit(delta: Delta): void {
    this.#onDelta?.(delta);
  }

  reconnect(): void {
    for (const listener of this.#listeners) {
      listener();
    }
  }

  get listenerCount(): number {
    return this.#listeners.size;
  }
}
