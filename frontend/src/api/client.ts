import { EVENT_CONNECTION_READY, WS_SNAPSHOT, WS_SUBSCRIBE } from '../constants/index.ts';
import type { Delta, HassApi, Snapshot } from './types.ts';

export type Unsubscribe = () => void;

/** Typisierter Zugang zur WebSocket-API des Backends. */
export class ApiClient {
  readonly #hass: HassApi;

  constructor(hass: HassApi) {
    this.#hass = hass;
  }

  /** Der aktuelle Gesamtstand. */
  snapshot(): Promise<Snapshot> {
    return this.#hass.callWS<Snapshot>({ type: WS_SNAPSHOT });
  }

  /** Meldet das Abonnement an; danach kommen nur noch Änderungen je Objekt. */
  async subscribe(onDelta: (delta: Delta) => void): Promise<Unsubscribe> {
    const stop = await this.#hass.connection.subscribeMessage<Delta>(onDelta, {
      type: WS_SUBSCRIBE,
    });
    return () => {
      void stop();
    };
  }

  /** Ruft `listener` nach jedem Wiederaufbau der Verbindung auf. */
  onReconnect(listener: () => void): Unsubscribe {
    const { connection } = this.#hass;
    connection.addEventListener(EVENT_CONNECTION_READY, listener);
    return () => {
      connection.removeEventListener(EVENT_CONNECTION_READY, listener);
    };
  }
}
