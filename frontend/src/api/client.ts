import {
  EVENT_CONNECTION_READY,
  FIELD_PANEL_ROUND_ID,
  FIELD_SCHEDULE_ID,
  WS_ACTION_CREATE,
  WS_ACTION_DELETE,
  WS_ACTION_UPDATE,
  WS_DRAW_BEGIN,
  WS_DRAW_CANCEL,
  WS_DRAW_COMMIT,
  WS_DRAW_SPIN,
  WS_DRAW_SPIN_REST,
  WS_PREFIX,
  WS_SNAPSHOT,
  WS_SUBSCRIBE,
} from '../constants/index.ts';
import type { ConfigResource } from '../constants/index.ts';
import type {
  Delta,
  HassApi,
  PanelRoundWire,
  Snapshot,
  SpinReply,
  SpinRestReply,
} from './types.ts';

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

  /** Legt ein Konfigurationsobjekt an (ohne `id`) oder ändert es (mit `id`); liefert das gespeicherte Objekt. */
  saveConfig<T>(resource: ConfigResource, id: string | undefined, object: object): Promise<T> {
    const type = `${WS_PREFIX}${resource}/${id === undefined ? WS_ACTION_CREATE : WS_ACTION_UPDATE}`;
    const message = id === undefined ? { type } : { type, [`${resource}_id`]: id };
    return this.#hass.callWS<T>({ ...message, [resource]: object });
  }

  /** Löscht ein Konfigurationsobjekt. */
  async deleteConfig(resource: ConfigResource, id: string): Promise<void> {
    await this.#hass.callWS<unknown>({
      type: `${WS_PREFIX}${resource}/${WS_ACTION_DELETE}`,
      [`${resource}_id`]: id,
    });
  }

  /** Ruft `listener` nach jedem Wiederaufbau der Verbindung auf. */
  onReconnect(listener: () => void): Unsubscribe {
    const { connection } = this.#hass;
    connection.addEventListener(EVENT_CONNECTION_READY, listener);
    return () => {
      connection.removeEventListener(EVENT_CONNECTION_READY, listener);
    };
  }

  /** Beginnt eine Panel-Runde für den Zeitplan; eine frühere desselben Plans entfällt. */
  beginDraw(scheduleId: string): Promise<PanelRoundWire> {
    return this.#call(WS_DRAW_BEGIN, FIELD_SCHEDULE_ID, scheduleId);
  }

  /** Zieht die nächste Aufgabe; das Ergebnis bestimmt das Backend. */
  spin(panelRoundId: string): Promise<SpinReply> {
    return this.#call(WS_DRAW_SPIN, FIELD_PANEL_ROUND_ID, panelRoundId);
  }

  /** Zieht alle übrigen Aufgaben ohne Animation. */
  spinRest(panelRoundId: string): Promise<SpinRestReply> {
    return this.#call(WS_DRAW_SPIN_REST, FIELD_PANEL_ROUND_ID, panelRoundId);
  }

  /** Schließt die vollständig gezogene Runde ab. */
  commit(panelRoundId: string): Promise<unknown> {
    return this.#call(WS_DRAW_COMMIT, FIELD_PANEL_ROUND_ID, panelRoundId);
  }

  /** Verwirft die Panel-Runde. */
  cancel(panelRoundId: string): Promise<unknown> {
    return this.#call(WS_DRAW_CANCEL, FIELD_PANEL_ROUND_ID, panelRoundId);
  }

  #call<T>(type: string, field: string, id: string): Promise<T> {
    return this.#hass.callWS<T>({ type, [field]: id });
  }
}
