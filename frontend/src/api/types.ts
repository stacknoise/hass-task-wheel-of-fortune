/** Formen der Nachrichten der WebSocket-API (KONZEPT §6.4). */

import type { CollectionName } from '../constants/index.ts';

/** Ein Objekt der Sammlungen; weitere Felder sind je Art verschieden und werden in den Views typisiert. */
export interface WireObject {
  readonly id: string;
  readonly [field: string]: unknown;
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
  readonly locale?: { readonly language?: string };
  callWS<T>(message: { readonly type: string; readonly [field: string]: unknown }): Promise<T>;
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
