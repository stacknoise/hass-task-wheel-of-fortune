import {
  EVENT_CONNECTION_READY,
  FIELD_ASSIGNMENT_ID,
  FIELD_MONTHS,
  FIELD_TO_PERSON_ID,
  FIELD_WEEKS,
  WS_ASSIGNMENT_COMPLETE,
  WS_ASSIGNMENT_SWAP,
  WS_HISTORY_LIST,
  WS_SNAPSHOT,
  WS_STATISTICS_GET,
  WS_SUBSCRIBE,
} from '../constants/index.ts';
import type { HistoryPage, HistoryQuery, StatisticsReport } from './models.ts';
import type { Delta, HassApi, Snapshot, WireObject } from './types.ts';

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

  /** Ruft `listener` nach jedem Wiederaufbau der Verbindung auf. */
  onReconnect(listener: () => void): Unsubscribe {
    const { connection } = this.#hass;
    connection.addEventListener(EVENT_CONNECTION_READY, listener);
    return () => {
      connection.removeEventListener(EVENT_CONNECTION_READY, listener);
    };
  }
}
