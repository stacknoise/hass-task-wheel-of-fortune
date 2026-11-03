import type { Delta, HassApi, Snapshot } from './index.ts';

export const EMPTY_SNAPSHOT: Snapshot = {
  persons: [{ id: 'p1' }, { id: 'p2' }],
  tasks: [{ id: 't1' }],
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
  readonly messages: { type: string }[] = [];
  /** Antworten je Befehl; ohne Eintrag liefert `callWS` den Snapshot. */
  replies: Record<string, unknown> = {};
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

  callWS<T>(message: { type: string }): Promise<T> {
    this.calls.push(message.type);
    this.messages.push(message);
    if (this.failSnapshot) {
      return Promise.reject(new Error('offline'));
    }
    const reply = message.type in this.replies ? this.replies[message.type] : this.snapshot;
    return Promise.resolve(reply as T);
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
