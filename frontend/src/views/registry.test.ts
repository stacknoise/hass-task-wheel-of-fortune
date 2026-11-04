import { describe, expect, it } from 'vitest';

import { ROUTES, ROUTE_IDS, VIEW_TAGS } from '../constants/index.ts';
import { VIEW_LOADERS, routeFromPath } from './registry.ts';

describe('routeFromPath', () => {
  it('findet den Tab zum Pfad', () => {
    expect(routeFromPath(ROUTES.tasks)).toBe('tasks');
  });

  it('kennt unbekannte Pfade nicht', () => {
    expect(routeFromPath('/unbekannt')).toBeUndefined();
    expect(routeFromPath(undefined)).toBeUndefined();
  });
});

describe('VIEW_LOADERS', () => {
  it.each(ROUTE_IDS)('lädt die Ansicht %s und registriert ihr Element', async (id) => {
    await VIEW_LOADERS[id]();
    expect(customElements.get(VIEW_TAGS[id])).toBeDefined();
  });
});

describe('Ansicht ohne Store', () => {
  it('rendert nichts, solange kein Stand da ist', async () => {
    await VIEW_LOADERS.history();
    const view = document.createElement(VIEW_TAGS.history);
    document.body.append(view);
    await (view as unknown as { updateComplete: Promise<boolean> }).updateComplete;
    expect(view.shadowRoot?.querySelector('tw-stat, p')).toBeNull();
  });
});
