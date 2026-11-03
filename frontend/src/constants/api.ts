/** Befehle und Feldnamen der WebSocket-API (KONZEPT §6.4). */

export const WS_PREFIX = 'task_wheel/';
export const WS_SNAPSHOT = `${WS_PREFIX}snapshot`;
export const WS_SUBSCRIBE = `${WS_PREFIX}subscribe`;

export const COLLECTIONS = [
  'persons',
  'tasks',
  'schedules',
  'assignments',
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
export const EVENT_CONNECTION_READY = 'ready';
