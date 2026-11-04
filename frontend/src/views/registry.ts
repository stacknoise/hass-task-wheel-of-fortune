import type { RouteId } from '../constants/index.ts';
import { ROUTES, ROUTE_IDS } from '../constants/index.ts';

type ViewLoader = () => Promise<unknown>;

/** Was das Panel von einer Ansicht braucht: ein Element, dem es die Sprache setzen kann. */
export interface SectionViewElement extends HTMLElement {
  language: string;
}

/** Jede Ansicht wird erst beim ersten Aufruf nachgeladen. */
export const VIEW_LOADERS: Readonly<Record<RouteId, ViewLoader>> = {
  overview: () => import('./overview.ts'),
  draw: () => import('./draw.ts'),
  tasks: () => import('./tasks.ts'),
  persons: () => import('./persons.ts'),
  schedules: () => import('./schedules.ts'),
  history: () => import('./history.ts'),
  statistics: () => import('./statistics.ts'),
  decisions: () => import('./decisions.ts'),
};

/** Der Tab zu einem Pfad des Panels (`/tasks`); unbekannte Pfade ergeben `undefined`. */
export function routeFromPath(path: string | undefined): RouteId | undefined {
  return ROUTE_IDS.find((id) => ROUTES[id] === path);
}
