/** Namen des Panels und seiner Bausteine. */

export const PANEL_ELEMENT_NAME = 'task-wheel-panel';
export const PANEL_HEADING_CLASS = 'tw-heading';
export const DEFAULT_LANGUAGE = 'en';

export const COMPONENT_TAGS = {
  tabBar: 'tw-tab-bar',
  stat: 'tw-stat',
  chips: 'tw-chips',
  avatar: 'tw-avatar',
  badge: 'tw-badge',
  room: 'tw-room',
  wheel: 'tw-wheel',
  confetti: 'tw-confetti',
  confirmAction: 'tw-confirm-action',
  confirmDialog: 'tw-confirm-dialog',
  dialog: 'tw-dialog',
  actionMenu: 'tw-action-menu',
} as const;

export const VIEW_TAGS = {
  overview: 'tw-overview-view',
  draw: 'tw-draw-view',
  tasks: 'tw-tasks-view',
  persons: 'tw-persons-view',
  schedules: 'tw-schedules-view',
  history: 'tw-history-view',
  statistics: 'tw-statistics-view',
  decisions: 'tw-decisions-view',
} as const;

/** Ereignis von `tw-confirm-action`, wenn die Löschung bestätigt wurde. */
export const EVENT_CONFIRM = 'tw-confirm';
/** Ereignis von `tw-confirm-dialog`, wenn die Rückfrage abgebrochen wurde. */
export const EVENT_CANCEL = 'tw-cancel';
/** Ereignis von `tw-action-menu` mit der Kennung der gewählten Aktion als `detail`. */
export const EVENT_ACTION = 'tw-action';
export const EVENT_TAB_SELECT = 'tw-tab-select';
export const EVENT_LOCATION_CHANGED = 'location-changed';

/** Breite in Pixeln, bis zu der Dialoge das Fenster ausfüllen (Smartphone). */
export const DIALOG_COMPACT_MAX_WIDTH = 600;
/** Höchste Breite eines Dialogs auf größeren Bildschirmen, in `em`. */
export const DIALOG_MAX_WIDTH_EM = 40;
/** Nummer der Maustaste für einen gewöhnlichen Klick. */
export const PRIMARY_BUTTON = 0;
/** Tasten für Dialoge und Menüs. */
export const KEY_ESCAPE = 'Escape';
export const KEY_TAB = 'Tab';
export const ACTIVATION_KEYS: readonly string[] = ['Enter', ' '];
export const KEY_ARROW_DOWN = 'ArrowDown';
export const KEY_ARROW_UP = 'ArrowUp';
export const KEY_HOME = 'Home';
export const KEY_END = 'End';
