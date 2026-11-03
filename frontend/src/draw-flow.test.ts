import { afterEach, describe, expect, it, vi } from 'vitest';

import { FakeHass, EMPTY_SNAPSHOT } from './api/fake-hass.testing.ts';
import type { PanelRoundWire, TaskDrawWire } from './api/index.ts';
import { EVENT_LOCATION_CHANGED, PANEL_ELEMENT_NAME, ROUTES } from './constants/index.ts';
import type { TaskWheelPanel } from './task-wheel-panel.ts';
import './task-wheel-panel.ts';

const PERSONS = [
  { id: 'p1', name: 'Anna', color: '#c05600' },
  { id: 'p2', name: 'Ben', color: '#1a5fd0' },
  { id: 'p3', name: 'Clara', color: '#137333' },
];
const TASKS = [
  { id: 't1', name: 'Bad putzen', points: 3, due_days: 2, allowed: ['p1', 'p2', 'p3'] },
  { id: 't2', name: 'Müll', points: 1, due_days: 1, allowed: ['p1'] },
];

const result = (task: string, winner: string | null): TaskDrawWire => ({
  task_id: task,
  winner_id: winner,
  chance: 0.6,
  segments: winner
    ? [
        { person_id: 'p1', weight: 6, chance: 0.6 },
        { person_id: 'p2', weight: 4, chance: 0.4 },
      ]
    : [],
  exclusions: [{ person_id: 'p3', reason: 'absent' }],
});

const round = (results: TaskDrawWire[], pending: string[]): PanelRoundWire => ({
  id: 'r1',
  schedule_id: 's1',
  expires_at: '2026-11-03T13:00:00+00:00',
  results,
  pending_task_ids: pending,
});

function hassWith(panelRounds: unknown[] = []): FakeHass {
  const hass = new FakeHass();
  hass.snapshot = {
    ...EMPTY_SNAPSHOT,
    persons: PERSONS,
    tasks: TASKS,
    schedules: [{ id: 's1', name: 'Wochenplan', archived: false }],
    panel_rounds: panelRounds as never,
  };
  return hass;
}

async function mount(hass: FakeHass): Promise<{ panel: TaskWheelPanel; view: () => ParentNode }> {
  const panel = document.createElement(PANEL_ELEMENT_NAME) as TaskWheelPanel;
  panel.route = { prefix: '/task-wheel', path: ROUTES.draw };
  panel.language = 'de';
  panel.hass = hass;
  document.body.append(panel);
  let view: Element | null = null;
  await vi.waitFor(() => {
    view = panel.shadowRoot?.querySelector('tw-draw-view') ?? null;
    expect(view?.shadowRoot?.querySelector('select')).toBeTruthy();
  });
  return { panel, view: () => (view as unknown as Element).shadowRoot as ShadowRoot };
}

async function click(view: () => ParentNode, selector: string): Promise<void> {
  await vi.waitFor(() => {
    const button = view().querySelector<HTMLButtonElement>(selector);
    expect(button).not.toBeNull();
    expect(button?.disabled).toBe(false);
  });
  view().querySelector<HTMLButtonElement>(selector)?.click();
}

const text = (view: () => ParentNode): string => (view().textContent ?? '').replace(/\s+/gu, ' ');

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

describe('Auslosung', () => {
  it('führt durch die Runde, zeigt das Ergebnis des Backends und schließt ab', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin', {
      result: result('t1', 'p2'),
      panel_round: round([result('t1', 'p2')], ['t2']),
    });
    const { panel, view } = await mount(hass);
    expect(text(view)).toContain('Wochenplan');

    await click(view, '.button.primary');
    await vi.waitFor(() => {
      expect(text(view)).toContain('0 / 2 verlost');
    });
    expect(text(view)).toContain('Bad putzen');

    await click(view, '.hub');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Ben übernimmt Bad putzen');
    });
    expect(text(view)).toContain('Chance 60 %');
    expect(text(view)).toContain('Abwesend');
    expect(view().querySelector('tw-confetti')).not.toBeNull();
    expect(text(view)).toContain('Aufgabe 1 / 2');

    hass.replies.set('task_wheel/draw/spin', {
      result: result('t2', null),
      panel_round: round([], []),
    });
    await click(view, '.result .button');
    await click(view, '.hub');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Niemand verfügbar für Müll');
      expect(text(view)).toContain('Nicht erlaubt');
    });
    expect(text(view)).toContain('Runde abschließen');

    const navigated = vi.fn();
    panel.addEventListener('tw-tab-select', navigated);
    window.addEventListener(EVENT_LOCATION_CHANGED, vi.fn());
    await click(view, '.result .button');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Alle Aufgaben sind verteilt');
    });
    expect(text(view)).toContain('Nicht verteilbar');
    expect(hass.calls).toContain('task_wheel/draw/commit');

    const buttons = view().querySelectorAll<HTMLButtonElement>('.done .button');
    buttons[0]?.click();
    expect(navigated).toHaveBeenCalledOnce();
    buttons[1]?.click();
    await vi.waitFor(() => {
      expect(view().querySelector('.stage .heading')).not.toBeNull();
    });
  });

  it('verlost den Rest ohne Animation', async () => {
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin_rest', {
      results: [result('t1', 'p1'), result('t2', 'p1')],
      panel_round: round([], []),
    });
    const { view } = await mount(hass);
    await click(view, '.button.primary');
    await click(view, '.actions .button:not(:last-child)');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Alle Aufgaben sind verteilt');
    });
    expect(text(view)).toContain('Anna');
  });

  it('setzt eine offene Runde fort und zeigt Fehler des Backends', async () => {
    const hass = hassWith([round([result('t1', 'p1')], ['t2'])]);
    const { view } = await mount(hass);
    await click(view, '.actions .button:not(.primary)');
    await vi.waitFor(() => {
      expect(text(view)).toContain('1 / 2 verlost');
    });
    expect(text(view)).toContain('Anna');

    hass.replies.set('task_wheel/draw/spin', Object.assign(new Error('x'), { code: 'not_found' }));
    await click(view, '.hub');
    await vi.waitFor(() => {
      expect(view().querySelector('[role="alert"]')?.textContent).toContain('not_found');
    });
    await click(view, '.button.primary');
  });

  it('bietet ohne Zeitplan keinen Start an', async () => {
    const hass = hassWith();
    hass.snapshot = { ...hass.snapshot, schedules: [] };
    const { view } = await mount(hass);
    expect(view().querySelector<HTMLButtonElement>('.button.primary')?.disabled).toBe(true);
    expect(text(view)).toContain('keinen Zeitplan');
  });
});
