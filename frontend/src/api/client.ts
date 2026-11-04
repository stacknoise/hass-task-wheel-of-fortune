import {
  EVENT_CONNECTION_READY,
  FIELD_ABSENCES,
  FIELD_ASSIGNMENT_ID,
  FIELD_ROUND_ID,
  FIELD_MONTHS,
  FIELD_NEW_TASK_ID,
  FIELD_PANEL_ROUND_ID,
  FIELD_SCHEDULE_ID,
  FIELD_TASK_ID,
  WS_ACTION_CREATE,
  WS_ACTION_DELETE,
  WS_ACTION_UPDATE,
  FIELD_TO_PERSON_ID,
  REPLY_PRESENT,
  FIELD_WEEKS,
  NOTIFY_DOMAIN,
  NOTIFY_PREFIX,
  NOTIFY_SEND_MESSAGE,
  WS_ASSIGNMENT_COMPLETE,
  WS_ASSIGNMENT_SKIP,
  WS_AVAILABILITY_PREVIEW,
  WS_ASSIGNMENT_SWAP,
  WS_ROUND_DELETE,
  WS_DRAW_BEGIN,
  WS_DRAW_CANCEL,
  WS_DRAW_COMMIT,
  WS_DRAW_PREVIEW,
  WS_DRAW_REPLACE_TASK,
  WS_DRAW_REPLACEMENTS,
  WS_DRAW_SPIN,
  WS_DRAW_SPIN_REST,
  WS_PREFIX,
  WS_HISTORY_LIST,
  WS_SNAPSHOT,
  WS_STATISTICS_GET,
  WS_SUBSCRIBE,
  DEFAULT_LANGUAGE,
} from '../constants/index.ts';
import { compareText } from './collate.ts';
import type { ConfigResource } from '../constants/index.ts';
import type { AbsenceWire } from './config-types.ts';
import type { HistoryPage, HistoryQuery, StatisticsReport } from './models.ts';
import type {
  Delta,
  AreaOption,
  HassApi,
  NotifyTarget,
  PanelRoundWire,
  PreviewReply,
  ReplaceTaskReply,
  ReplacementsReply,
  Snapshot,
  SpinReply,
  SpinRestReply,
  WireObject,
} from './types.ts';

export type Unsubscribe = () => void;

/** Ein berechneter Wert samt den Quellen (nach Identität) und der Sprache, aus denen er entstand. */
class Memo<T> {
  readonly #sources: readonly unknown[];
  readonly language: string;
  readonly value: T;

  constructor(language: string, source: unknown, value: T, ...more: readonly unknown[]) {
    this.language = language;
    this.#sources = [source, ...more];
    this.value = value;
  }

  matches(language: string, ...sources: readonly unknown[]): boolean {
    return (
      language === this.language &&
      sources.length === this.#sources.length &&
      sources.every((source, index) => source === this.#sources[index])
    );
  }
}

/** Typisierter Zugang zur WebSocket-API des Backends. */
export class ApiClient {
  #hass: HassApi;
  #areasCache: Memo<readonly AreaOption[]> | undefined;
  #targetsCache: Memo<readonly NotifyTarget[]> | undefined;

  constructor(hass: HassApi) {
    this.#hass = hass;
  }

  /** Übernimmt das aktuelle `hass`-Objekt (Home Assistant ersetzt es bei jeder Änderung). */
  useHass(hass: HassApi): void {
    this.#hass = hass;
  }

  /**
   * Räume aus Home Assistant (Bereiche), nach Name sortiert; ohne Namen gilt die Kennung. Solange
   * Home Assistant dieselbe Registratur und Sprache meldet, kommt dieselbe Liste zurück.
   */
  areas(): readonly AreaOption[] {
    const language = this.language();
    const source = this.#hass.areas;
    if (this.#areasCache?.matches(language, source)) {
      return this.#areasCache.value;
    }
    const compare = compareText(language);
    const value = Object.entries(source ?? {})
      .map(([id, area]) => ({ id, label: typeof area.name === 'string' ? area.name : id }))
      .sort((a, b) => compare(a.label, b.label));
    this.#areasCache = new Memo(language, source, value);
    return value;
  }

  /** Sprache des Panels (Gebietsschema von Home Assistant, sonst Englisch). */
  language(): string {
    return this.#hass.locale?.language ?? this.#hass.language ?? DEFAULT_LANGUAGE;
  }

  /** Benachrichtigungsziele aus Home Assistant: `notify`-Entitäten und -Dienste, sortiert. */
  notifyTargets(): readonly NotifyTarget[] {
    const language = this.language();
    const { states, services } = this.#hass;
    if (this.#targetsCache?.matches(language, states, services)) {
      return this.#targetsCache.value;
    }
    const entities = Object.entries(states ?? {})
      .filter(([id]) => id.startsWith(NOTIFY_PREFIX))
      .map(([id, state]) => {
        const name = state.attributes?.friendly_name;
        return { id, label: typeof name === 'string' ? name : id };
      });
    const serviceTargets = Object.keys(services?.[NOTIFY_DOMAIN] ?? {})
      .filter((name) => name !== NOTIFY_SEND_MESSAGE)
      .map((name) => ({ id: `${NOTIFY_PREFIX}${name}`, label: name }));
    const unique = new Map([...serviceTargets, ...entities].map((target) => [target.id, target]));
    const compare = compareText(language);
    const value = [...unique.values()].sort((a, b) => compare(a.id, b.id));
    this.#targetsCache = new Memo(language, states, value, services);
    return value;
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

  /** Anwesenheit der nächsten Wochen (ab Montag) für Abwesenheitsregeln; gerechnet wird im Backend. */
  async availabilityPreview(absences: readonly AbsenceWire[]): Promise<readonly boolean[]> {
    const reply = await this.#hass.callWS<Record<typeof REPLY_PRESENT, readonly boolean[]>>({
      type: WS_AVAILABILITY_PREVIEW,
      [FIELD_ABSENCES]: absences,
    });
    return reply[REPLY_PRESENT];
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

  /** Markiert die Zuteilung als „Bleibt unerledigt“ (zählt in der Statistik wie verpasst). */
  skip(assignmentId: string): Promise<WireObject> {
    return this.#hass.callWS<WireObject>({
      type: WS_ASSIGNMENT_SKIP,
      [FIELD_ASSIGNMENT_ID]: assignmentId,
    });
  }

  /** Tauscht die Zuteilung gegen die offene Zuteilung der Zielperson (gleiche Auslosung). */
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

  /** Ist der angemeldete Benutzer Administrator (nur dann darf er Aufgaben austauschen)? */
  isAdmin(): boolean {
    return this.#hass.user?.is_admin === true;
  }

  /** Aufgaben des Zeitplans, die vor dem Start gegen eine der Runde getauscht werden könnten. */
  replacements(panelRoundId: string): Promise<ReplacementsReply> {
    return this.#call(WS_DRAW_REPLACEMENTS, FIELD_PANEL_ROUND_ID, panelRoundId);
  }

  /** Tauscht vor dem Start (nur Administratoren) eine Aufgabe der Runde gegen eine andere. */
  replaceTask(panelRoundId: string, taskId: string, newTaskId: string): Promise<ReplaceTaskReply> {
    return this.#hass.callWS<ReplaceTaskReply>({
      type: WS_DRAW_REPLACE_TASK,
      [FIELD_PANEL_ROUND_ID]: panelRoundId,
      [FIELD_TASK_ID]: taskId,
      [FIELD_NEW_TASK_ID]: newTaskId,
    });
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
