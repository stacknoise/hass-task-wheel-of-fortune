/** Tabs des Panels (Reihenfolge wie in den Mockups) und ihre Pfade. */

export const ROUTES = {
  overview: '/overview',
  draw: '/draw',
  tasks: '/tasks',
  persons: '/persons',
  schedules: '/schedules',
  history: '/history',
  statistics: '/statistics',
} as const;

export type RouteId = keyof typeof ROUTES;

export const ROUTE_IDS = Object.keys(ROUTES) as readonly RouteId[];
export const DEFAULT_ROUTE: RouteId = 'overview';
