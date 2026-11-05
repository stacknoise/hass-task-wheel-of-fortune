/** Formen der Nachrichten der WebSocket-API (KONZEPT §6.4). */

import type { CollectionName } from '../constants/index.ts';

/** Ein Objekt der Sammlungen; weitere Felder sind je Art verschieden und werden in den Views typisiert. */
export interface WireObject {
  readonly id: string;
  readonly [field: string]: unknown;
}

/** Wann die Aufgaben einer manuellen Auslosung gelten und wie lange sie Zeit haben (Pflicht). */
export interface DrawWindowRequest {
  readonly starts_at: string;
  readonly duration: number;
  readonly duration_unit: string;
  /** Bestätigt, dass der nächste reguläre Lauf des Zeitplans entfällt. */
  readonly replace_next: boolean;
}

export type Settings = Readonly<Record<string, unknown>>;

export type Collections = { readonly [name in CollectionName]: readonly WireObject[] };

export interface Snapshot extends Collections {
  readonly settings: Settings;
  readonly now: string;
}

export interface CollectionDelta {
  readonly upsert: readonly WireObject[];
  readonly remove: readonly string[];
}

export type Delta = { readonly [name in CollectionName]?: CollectionDelta } & {
  readonly settings?: Settings;
};

/** Der Teil von `hass.connection`, den der Client braucht. */
export interface HassConnection {
  // Der Typparameter spiegelt die Signatur von Home Assistant.
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters
  subscribeMessage<T>(
    callback: (message: T) => void,
    message: { readonly type: string },
  ): Promise<() => unknown>;
  addEventListener(type: string, listener: () => void): void;
  removeEventListener(type: string, listener: () => void): void;
}

/** Der Teil des `hass`-Objekts, den das Panel braucht. */
export interface HassApi {
  readonly connection: HassConnection;
  readonly language?: string;
  /** Der angemeldete Benutzer (Home Assistant). */
  readonly user?: { readonly is_admin?: boolean };
  readonly locale?: { readonly language?: string };
  /** Alle Entitäten (nur die Kennungen und Anzeigenamen braucht das Panel). */
  readonly states?: Readonly<
    Record<string, { readonly attributes?: { readonly friendly_name?: unknown } }>
  >;
  /** Alle Bereiche (Räume) von Home Assistant nach Kennung. */
  readonly areas?: Readonly<Record<string, { readonly name?: unknown }>>;
  /** Alle Dienste je Bereich. */
  readonly services?: Readonly<Record<string, Readonly<Record<string, unknown>>>>;
  callWS<T>(message: { readonly type: string; readonly [field: string]: unknown }): Promise<T>;
}

/** Ein Home-Assistant-Bereich (Raum): Kennung und Anzeigename. */
export interface AreaOption {
  readonly id: string;
  readonly label: string;
}

/** Ein mögliches Benachrichtigungsziel: Kennung und Anzeigename. */
export interface NotifyTarget {
  readonly id: string;
  readonly label: string;
}

/** Ein Segment im Rad: Person und normierte Chance (Summe aller Chancen = 1). */
export interface WireSegment {
  readonly person_id: string;
  readonly weight: number;
  readonly chance: number;
}

/** Eine Person, die nicht im Rad ist, und der Grund (Schlüssel `ExclusionReason`). */
export interface WireExclusion {
  readonly person_id: string;
  readonly reason: string;
}

/** Ergebnis der Ziehung einer Aufgabe; ohne Gewinner ist die Aufgabe nicht verteilbar. */
export interface TaskDrawWire {
  readonly task_id: string;
  readonly winner_id: string | null;
  readonly chance: number;
  readonly segments: readonly WireSegment[];
  readonly exclusions: readonly WireExclusion[];
}

/** Offene Panel-Runde: bisherige Ergebnisse und die noch zu ziehenden Aufgaben. */
export interface PanelRoundWire {
  readonly id: string;
  readonly schedule_id: string;
  readonly expires_at: string;
  readonly results: readonly TaskDrawWire[];
  readonly pending_task_ids: readonly string[];
  /** Vor dem Start: Aufgaben, die sich nicht alle vergeben lassen (je Person höchstens eine). */
  readonly unplaceable_task_ids: readonly string[];
}

/** Eine Aufgabe, die der Admin vor dem Start gegen eine der Runde tauschen könnte. */
export interface TaskReplacementWire {
  readonly task_id: string;
  /** Mit den anwesenden Personen machbar. */
  readonly doable: boolean;
}

export interface ReplacementsReply {
  readonly replacements: readonly TaskReplacementWire[];
}

export interface ReplaceTaskReply {
  readonly panel_round: PanelRoundWire;
}

export interface SpinReply {
  readonly result: TaskDrawWire;
  readonly panel_round: PanelRoundWire;
}

export interface SpinRestReply {
  readonly results: readonly TaskDrawWire[];
  readonly panel_round: PanelRoundWire;
}

export interface PreviewReply {
  readonly result: TaskDrawWire;
}
