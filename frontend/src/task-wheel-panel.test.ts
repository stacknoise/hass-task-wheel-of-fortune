import { describe, expect, it, vi } from 'vitest';

import {
  EVENT_LOCATION_CHANGED,
  PANEL_ELEMENT_NAME,
  PANEL_HEADING_CLASS,
} from './constants/index.ts';
import { FakeHass } from './api/fake-hass.testing.ts';
import { assignment, fakeHass, text } from './views/fixtures.testing.ts';
import type { TaskWheelPanel } from './task-wheel-panel.ts';
import './task-wheel-panel.ts';

const PREFIX = '/task-wheel';

async function mount(hass?: FakeHass, path = ''): Promise<TaskWheelPanel> {
  const element = document.createElement(PANEL_ELEMENT_NAME) as TaskWheelPanel;
  element.route = { prefix: PREFIX, path };
  if (hass) {
    element.hass = hass;
  }
  document.body.append(element);
  await element.updateComplete;
  return element;
}

function tabLabels(element: TaskWheelPanel): string[] {
  const bar = element.shadowRoot?.querySelector('tw-tab-bar');
  return [...(bar?.shadowRoot?.querySelectorAll('a') ?? [])].map((link) => link.textContent);
}

async function settle(element: TaskWheelPanel): Promise<void> {
  await vi.waitFor(async () => {
    await element.updateComplete;
    expect(element.shadowRoot?.querySelector('tw-overview-view, tw-tasks-view')).not.toBeNull();
  });
}

describe('task-wheel-panel', () => {
  it('rendert die Überschrift in der gewählten Sprache', async () => {
    const element = await mount();
    element.language = 'de';
    await element.updateComplete;
    const heading = element.shadowRoot?.querySelector(`.${PANEL_HEADING_CLASS}`);
    expect(heading?.textContent).toBe('Task Wheel of Fortune');
    expect(element.shadowRoot?.querySelector('main')?.textContent).toContain('geladen');
  });

  it('zeigt den Menü-Knopf von Home Assistant nur im schmalen Modus', async () => {
    const element = await mount();
    const button = (): Element | null | undefined =>
      element.shadowRoot?.querySelector('ha-menu-button');
    expect(button()).toBeNull();
    element.narrow = true;
    await element.updateComplete;
    expect(button()).not.toBeNull();
  });

  it('zeigt alle Tabs aus den Mockups in der Sprache von hass', async () => {
    const element = await mount(new FakeHass());
    expect(tabLabels(element)).toEqual([
      'Übersicht',
      'Auslosung',
      'Aufgaben',
      'Personen',
      'Zeitpläne',
      'Historie',
      'Statistik',
    ]);
  });

  it('zeigt nach dem Laden die Ansicht mit dem Snapshot und reagiert auf Deltas', async () => {
    const hass = fakeHass();
    const element = await mount(hass);
    await settle(element);
    const view = element.shadowRoot?.querySelector('tw-overview-view');
    const content = (): string => text(view as Element);
    await vi.waitFor(() => {
      expect(content()).toContain('3 offen');
    });
    hass.emit({ assignments: { upsert: [assignment('a9', 't2', 'p1', 'open')], remove: [] } });
    await vi.waitFor(() => {
      expect(content()).toContain('4 offen');
    });
  });

  it('wechselt den Tab über die Adresse und meldet die Navigation an Home Assistant', async () => {
    const element = await mount(new FakeHass());
    const changed = vi.fn();
    window.addEventListener(EVENT_LOCATION_CHANGED, changed);
    const bar = element.shadowRoot?.querySelector('tw-tab-bar');
    const link = bar?.shadowRoot?.querySelectorAll('a')[2];
    link?.click();
    await element.updateComplete;
    expect(changed).toHaveBeenCalledOnce();
    expect(location.pathname).toBe(`${PREFIX}/tasks`);
    await settle(element);
    expect(element.shadowRoot?.querySelector('tw-tasks-view')).not.toBeNull();
    window.removeEventListener(EVENT_LOCATION_CHANGED, changed);
  });

  it('folgt der Route von Home Assistant und zeigt Fehler an', async () => {
    const hass = new FakeHass();
    hass.failSnapshot = true;
    const element = await mount(hass, '/history');
    await vi.waitFor(async () => {
      await element.updateComplete;
      expect(element.shadowRoot?.querySelector('main')?.textContent).toContain('nicht geladen');
    });
  });

  it('beendet den Store beim Entfernen', async () => {
    const hass = new FakeHass();
    const element = await mount(hass);
    await vi.waitFor(() => {
      expect(hass.listenerCount).toBe(1);
    });
    element.remove();
    expect(hass.listenerCount).toBe(0);
    document.body.append(element);
    await vi.waitFor(() => {
      expect(hass.listenerCount).toBe(1);
    });
  });
});
