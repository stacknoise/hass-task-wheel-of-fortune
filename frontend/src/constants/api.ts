/** Befehle und Feldnamen der WebSocket-API (KONZEPT §6.4). */

export const WS_PREFIX = 'task_wheel/';
export const WS_SNAPSHOT = `${WS_PREFIX}snapshot`;
export const WS_SUBSCRIBE = `${WS_PREFIX}subscribe`;
export const WS_AVAILABILITY_PREVIEW = `${WS_PREFIX}availability/preview`;
export const WS_ROUND_DELETE = `${WS_PREFIX}round/delete`;
export const WS_DRAW_BEGIN = `${WS_PREFIX}draw/begin`;
export const WS_DRAW_PREVIEW = `${WS_PREFIX}draw/preview`;
export const WS_DRAW_SPIN = `${WS_PREFIX}draw/spin`;
export const WS_DRAW_SPIN_REST = `${WS_PREFIX}draw/spin_rest`;
export const WS_DRAW_COMMIT = `${WS_PREFIX}draw/commit`;
export const WS_DRAW_CANCEL = `${WS_PREFIX}draw/cancel`;

export const FIELD_ABSENCES = 'absences';
export const FIELD_SCHEDULE_ID = 'schedule_id';
export const FIELD_ROUND_ID = 'round_id';
export const FIELD_PANEL_ROUND_ID = 'panel_round_id';
export const REPLY_PRESENT = 'present';
export const REPLY_RESULT = 'result';
export const REPLY_RESULTS = 'results';
export const REPLY_PANEL_ROUND = 'panel_round';

export const COLLECTIONS = [
  'persons',
  'tasks',
  'schedules',
  'assignments',
  'rounds',
  'panel_rounds',
] as const;
export type CollectionName = (typeof COLLECTIONS)[number];

/** Konfigurierbare Arten; der Name ist Teil des Befehls (`task_wheel/person/create`) und des Nachrichtenfelds. */
export const CONFIG_RESOURCES = ['person', 'task', 'schedule'] as const;
export type ConfigResource = (typeof CONFIG_RESOURCES)[number];
export const WS_ACTION_CREATE = 'create';
export const WS_ACTION_UPDATE = 'update';
export const WS_ACTION_DELETE = 'delete';

export const KEY_ID = 'id';
export const KEY_NAME = 'name';

/** Sammlungen, die das Panel alphabetisch nach Namen zeigt. */
export const SORTED_COLLECTIONS = ['persons', 'tasks', 'schedules'] as const;

/** Namen vergleichen: Groß-/Kleinschreibung und Akzente zählen nicht, Zahlen nach ihrem Wert. */
export const COLLATION_OPTIONS: Intl.CollatorOptions = { sensitivity: 'base', numeric: true };
export const EVENT_CONNECTION_READY = 'ready';
