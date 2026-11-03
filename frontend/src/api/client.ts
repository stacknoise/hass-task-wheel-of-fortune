import {
  EVENT_CONNECTION_READY,
  FIELD_ASSIGNMENT_ID,
  FIELD_ROUND_ID,
  FIELD_MONTHS,
  FIELD_PANEL_ROUND_ID,
  FIELD_SCHEDULE_ID,
  WS_ACTION_CREATE,
  WS_ACTION_DELETE,
  WS_ACTION_UPDATE,
  FIELD_TO_PERSON_ID,
  FIELD_WEEKS,
  WS_ASSIGNMENT_COMPLETE,
  WS_ASSIGNMENT_SWAP,
  WS_ROUND_DELETE,
  WS_DRAW_BEGIN,
  WS_DRAW_CANCEL,
  WS_DRAW_COMMIT,
  WS_DRAW_PREVIEW,
  WS_DRAW_SPIN,
  WS_DRAW_SPIN_REST,
  WS_PREFIX,
  WS_HISTORY_LIST,
  WS_SNAPSHOT,
  WS_STATISTICS_GET,
  WS_SUBSCRIBE,
} from '../constants/index.ts';
import type { ConfigResource } from '../constants/index.ts';
import type { HistoryPage, HistoryQuery, StatisticsReport } from './models.ts';
import type {
  Delta,
  HassApi,
  PanelRoundWire,
  PreviewReply,
  Snapshot,
  SpinReply,
  SpinRestReply,
  WireObject,
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

  /** Eine Seite der Historie (neueste Runde zuerst), optional für eine Person. */
  history(query: HistoryQuery = {}): Promise<HistoryPage> {
    return this.#hass.callWS<HistoryPage>({ type: WS_HISTORY_LIST, ...query });
  }

  /** Auswertung der letzten Kalendermonate und Wochen. */
  statistics(months: number, weeks: number): Promise<StatisticsReport> {
    return this.#hass.callWS<StatisticsReport>({
      type: WS_STATISTICS_GET,
      [FIELD_MONTHS]: months,
      [FIELD_WEEKS]: weeks,
    });
  }

  /** Erledigt die Zuteilung. */
  complete(assignmentId: string): Promise<WireObject> {
    return this.#hass.callWS<WireObject>({
      type: WS_ASSIGNMENT_COMPLETE,
      [FIELD_ASSIGNMENT_ID]: assignmentId,
    });
  }

  /** Tauscht die Zuteilung gegen einen Joker auf eine andere Person. */
  swap(assignmentId: string, toPersonId: string): Promise<WireObject> {
    return this.#hass.callWS<WireObject>({
      type: WS_ASSIGNMENT_SWAP,
      [FIELD_ASSIGNMENT_ID]: assignmentId,
      [FIELD_TO_PERSON_ID]: toPersonId,
    });
  }

  /** Löscht die Auslosung samt Zuteilungen; Punkte und Statistik werden zurückgerechnet. */
  async deleteRound(roundId: string): Promise<void> {
    await this.#hass.callWS<unknown>({ type: WS_ROUND_DELETE, [FIELD_ROUND_ID]: roundId });
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

  /** Das Rad der nächsten Aufgabe (Segmente, Ausschlüsse) ohne Ziehung. */
  previewDraw(panelRoundId: string): Promise<PreviewReply> {
    return this.#call(WS_DRAW_PREVIEW, FIELD_PANEL_ROUND_ID, panelRoundId);
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
