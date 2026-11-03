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
  wheel: 'tw-wheel',
  confetti: 'tw-confetti',
} as const;

export const VIEW_TAGS = {
  overview: 'tw-overview-view',
  draw: 'tw-draw-view',
  tasks: 'tw-tasks-view',
  persons: 'tw-persons-view',
  schedules: 'tw-schedules-view',
  history: 'tw-history-view',
  statistics: 'tw-statistics-view',
} as const;

export const EVENT_TAB_SELECT = 'tw-tab-select';
export const EVENT_LOCATION_CHANGED = 'location-changed';
