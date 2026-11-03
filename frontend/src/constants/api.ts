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

export const KEY_ID = 'id';
export const EVENT_CONNECTION_READY = 'ready';
