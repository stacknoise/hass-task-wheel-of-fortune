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
  {
    id: 't1',
    name: 'Bad putzen',
    points: 3,
    allowed: ['p1', 'p2', 'p3'],
    frequency: { kind: 'every_round' },
  },
  {
    id: 't2',
    name: 'Müll',
    points: 1,
    allowed: ['p1'],
    frequency: { kind: 'every_round' },
  },
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
  unplaceable_task_ids: [],
  participant_ids: [],
});

function hassWith(panelRounds: unknown[] = [], animations?: string[]): FakeHass {
  const hass = new FakeHass();
  hass.snapshot = {
    ...EMPTY_SNAPSHOT,
    persons: PERSONS,
    tasks: TASKS,
    schedules: [{ id: 's1', name: 'Wochenplan', archived: false, animations }],
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

/** Öffnet die Frage nach Gilt-ab und Frist und bestätigt sie. */
async function start(view: () => ParentNode, selector = '.button.primary'): Promise<void> {
  await click(view, selector);
  await vi.waitFor(() => {
    expect(
      view().querySelector('tw-draw-start-dialog')?.shadowRoot?.querySelector('.primary'),
    ).not.toBeNull();
  });
  view()
    .querySelector('tw-draw-start-dialog')
    ?.shadowRoot?.querySelector<HTMLButtonElement>('.primary')
    ?.click();
}

const text = (view: () => ParentNode): string => (view().textContent ?? '').replace(/\s+/gu, ' ');

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

describe('Auslosung', () => {
  it('warnt vor dem Start, wenn nicht alle Aufgaben vergeben werden können', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', {
      ...round([], ['t1', 't2']),
      unplaceable_task_ids: ['t2'],
    });
    hass.replies.set('task_wheel/draw/preview', { result: result('t1', null) });
    const { view } = await mount(hass);

    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Nicht alle Aufgaben lassen sich verteilen');
    });
    expect(view().querySelector('.stage.warning li')?.textContent).toContain('Müll');
    expect(view().querySelector('tw-stage')).toBeNull();

    await click(view, '.stage.warning .primary');
    await vi.waitFor(() => {
      expect(view().querySelector('.stage.warning')).toBeNull();
      expect(view().querySelector('tw-stage')).not.toBeNull();
    });
  });

  it('führt durch die Runde, zeigt das Ergebnis des Backends und schließt ab', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/preview', {
      result: { ...result('t1', null), segments: result('t1', 'p1').segments },
    });
    hass.replies.set('task_wheel/draw/spin', {
      result: result('t1', 'p2'),
      panel_round: round([result('t1', 'p2')], ['t2']),
    });
    const { panel, view } = await mount(hass);
    expect(text(view)).toContain('Wochenplan');

    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('0 / 2 verlost');
    });
    expect(text(view)).toContain('Bad putzen');

    // Das Rad ist schon vor dem Drehen gefüllt, die Personen zeigen ihre Chance.
    const wheel = (): ParentNode =>
      view().querySelector('tw-stage')?.shadowRoot?.querySelector('tw-wheel')
        ?.shadowRoot as ShadowRoot;
    await vi.waitFor(() => {
      expect(wheel().querySelectorAll('path.wedge')).toHaveLength(3);
    });
    expect(text(view)).not.toContain('60 %');

    await click(view, '.hub');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Ben übernimmt Bad putzen');
    });
    // Nach dem Anhalten bleibt die Drehung erhalten (kein Zurückspringen beim Neuzeichnen).
    const rotor = wheel().querySelector<SVGGElement>('.rotor');
    expect(rotor?.style.transform).not.toBe('rotate(0deg)');
    expect(text(view)).not.toContain('Chance');
    expect(text(view)).not.toContain('Abwesend');
    expect(text(view)).not.toContain('Nicht erlaubt');
    expect(view().querySelector('tw-confetti')).not.toBeNull();
    expect(text(view)).toContain('Aufgabe 1 / 2');

    hass.replies.set('task_wheel/draw/spin', {
      result: result('t2', null),
      panel_round: round([], []),
    });
    await click(view, '.result .button');
    // Für „Müll“ bleibt nur Anna übrig: die Ziehung läuft ohne Klick auf „Drehen“.
    await vi.waitFor(() => {
      expect(text(view)).toContain('Niemand verfügbar für Müll');
      expect(text(view)).not.toContain('Nicht erlaubt');
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

    // Nach dem Abschluss gibt es kein „Abbrechen“ mehr, nur „Neue Auslosung starten“.
    expect(view().querySelector('.card .actions .button')).toBeNull();
    const buttons = view().querySelectorAll<HTMLButtonElement>('.done .button');
    buttons[0]?.click();
    expect(navigated).toHaveBeenCalledOnce();
    buttons[1]?.click();
    await vi.waitFor(() => {
      expect(view().querySelector('.stage .heading')).not.toBeNull();
    });
  });

  it('spielt die Animation auch ab, wenn nur eine Person möglich ist (außer bei der letzten Aufgabe)', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    const single = (task: string): TaskDrawWire => ({
      ...result(task, 'p1'),
      segments: [{ person_id: 'p1', weight: 1, chance: 1 }],
    });
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', round([], ['t2', 't1']));
    hass.replies.set('task_wheel/draw/preview', { result: { ...single('t2'), winner_id: null } });
    hass.replies.set('task_wheel/draw/spin', {
      result: single('t2'),
      panel_round: round([single('t2')], ['t1']),
    });
    const { view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('0 / 2 verlost');
    });
    await click(view, '.hub');
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(text(view)).not.toContain('übernimmt');
    expect(view().querySelector('.result')).toBeNull();
  }, 15_000);

  it('tauscht als Admin vor dem Start eine Aufgabe gegen eine machbare', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith();
    hass.snapshot = {
      ...hass.snapshot,
      tasks: [
        ...TASKS,
        { ...TASKS[0], id: 't3', name: 'Garage', area_ids: ['kueche', 'bad'] },
        { ...TASKS[0], id: 't4', name: 'Keller' },
      ],
    };
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/preview', { result: result('t1', null) });
    hass.replies.set('task_wheel/draw/replacements', {
      replacements: [
        { task_id: 't3', doable: true },
        { task_id: 't4', doable: false },
      ],
    });
    hass.replies.set('task_wheel/draw/replace_task', { panel_round: round([], ['t3', 't2']) });
    const { view } = await mount(hass);
    await start(view);
    await click(view, '.task .button');
    const dialog = (): ParentNode => view().querySelector('tw-dialog') as unknown as ParentNode;
    await vi.waitFor(() => {
      expect(dialog().textContent).toContain('Keller');
    });
    const radios = dialog().querySelectorAll<HTMLInputElement>('input[type=radio]');
    expect(radios).toHaveLength(2);
    expect(radios[1]?.disabled).toBe(true);
    expect(dialog().textContent).toContain('Nicht wählbar');
    // Die Räume stehen im Dialog neben den Aufgaben (mehrere Räume je Aufgabe).
    expect(dialog().querySelectorAll('tw-room')).toHaveLength(2);
    dialog().querySelector<HTMLButtonElement>('.button.primary')?.click();
    const list = (): string => view().querySelector('ul')?.textContent ?? '';
    await vi.waitFor(() => {
      expect(list()).toContain('Garage');
    });
    expect(list()).not.toContain('Bad putzen');
    expect(hass.messages.find((m) => m.type === 'task_wheel/draw/replace_task')).toMatchObject({
      panel_round_id: 'r1',
      task_id: 't1',
      new_task_id: 't3',
    });
  });

  it('startet die erste Auslosung nie von allein, auch nicht nach einem Austausch', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith();
    // „Müll“ (t2) hat nur eine mögliche Person; der Admin muss dennoch selbst drehen.
    hass.replies.set('task_wheel/draw/begin', round([], ['t2', 't1']));
    hass.replies.set('task_wheel/draw/preview', { result: result('t2', null) });
    const { view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('0 / 2 verlost');
    });
    await vi.waitFor(() => {
      expect(view().querySelector('.task .button')).not.toBeNull();
    });
    expect(hass.messages.some((m) => m.type === 'task_wheel/draw/spin')).toBe(false);
  });

  it('bietet Nicht-Admins keinen Austausch an', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith();
    (hass as { user: { is_admin: boolean } }).user.is_admin = false;
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/preview', { result: result('t1', null) });
    const { view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('0 / 2 verlost');
    });
    expect(view().querySelector('.task .button')).toBeNull();
  });

  it('verlost den Rest ohne Animation', async () => {
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin_rest', {
      results: [result('t1', 'p1'), result('t2', 'p1')],
      panel_round: round([], []),
    });
    const { view } = await mount(hass);
    await start(view);
    await click(view, '.actions .button:not(:last-child)');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Alle Aufgaben sind verteilt');
    });
    expect(text(view)).toContain('Anna');
  });

  it('zeigt Admins ohne Animation erst die Vorbereitung und verteilt dann direkt', async () => {
    const hass = hassWith([], []);
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin_rest', {
      results: [result('t1', 'p1'), result('t2', 'p1')],
      panel_round: round([], []),
    });
    const { view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Die Runde steht bereit');
    });
    expect(hass.calls).not.toContain('task_wheel/draw/spin_rest');
    expect(view().querySelector('.task .button')).not.toBeNull();
    await click(view, '.actions .button:not(:last-child)');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Alle Aufgaben sind verteilt');
    });
    expect(hass.calls).not.toContain('task_wheel/draw/spin');
  });

  it('zeigt ohne Animation sofort die Aufgabenliste mit den Zuteilungen', async () => {
    const hass = hassWith([], []);
    (hass as { user: { is_admin: boolean } }).user.is_admin = false;
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin_rest', {
      results: [result('t1', 'p1'), result('t2', 'p1')],
      panel_round: round([], []),
    });
    const { view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Alle Aufgaben sind verteilt');
    });
    expect(text(view)).toContain('Anna');
    expect(hass.calls).not.toContain('task_wheel/draw/spin');
    expect(hass.calls).not.toContain('task_wheel/draw/preview');
  });

  it('setzt eine offene Runde fort und zieht die letzte Aufgabe ohne Drehen', async () => {
    const hass = hassWith([round([result('t1', 'p1')], ['t2'])]);
    hass.replies.set('task_wheel/draw/spin', {
      result: result('t2', null),
      panel_round: round([], []),
    });
    const { view } = await mount(hass);
    await click(view, '.actions .button:not(.primary)');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Niemand verfügbar für Müll');
    });
    expect(text(view)).toContain('Anna');
    expect(hass.calls.filter((call) => call === 'task_wheel/draw/spin')).toHaveLength(1);
  });

  it('zeigt Fehler des Backends mit ihrem Code', async () => {
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', Object.assign(new Error('x'), { code: 'not_found' }));
    const { view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      expect(view().querySelector('[role="alert"]')?.textContent).toContain('not_found');
    });
  });

  it('bietet ohne Zeitplan keinen Start an', async () => {
    const hass = hassWith();
    hass.snapshot = { ...hass.snapshot, schedules: [] };
    const { view } = await mount(hass);
    expect(view().querySelector<HTMLButtonElement>('.button.primary')?.disabled).toBe(true);
    expect(text(view)).toContain('keinen Zeitplan');
  });

  it('zeigt die Animation des Zeitplans und setzt den Knopf darunter', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith([], ['drum']);
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/preview', {
      result: { ...result('t1', null), segments: result('t1', 'p1').segments },
    });
    const { view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      const stage = view().querySelector('tw-stage');
      expect(stage?.shadowRoot?.querySelector('tw-drum')).not.toBeNull();
    });
    expect(view().querySelector('.wheel-box.below .hub.below')).not.toBeNull();
  });

  it('behält die laufende Runde beim Wechsel des Tabs', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const hass = hassWith();
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    const { panel, view } = await mount(hass);
    await start(view);
    await vi.waitFor(() => {
      expect(text(view)).toContain('0 / 2 verlost');
    });

    panel.route = { prefix: '/task-wheel', path: ROUTES.tasks };
    await vi.waitFor(() => {
      expect(panel.shadowRoot?.querySelector('tw-draw-view')).toBeNull();
    });
    panel.route = { prefix: '/task-wheel', path: ROUTES.draw };
    await vi.waitFor(() => {
      expect(panel.shadowRoot?.querySelector('tw-draw-view')).not.toBeNull();
    });
    await vi.waitFor(() => {
      expect(text(view)).toContain('0 / 2 verlost');
    });
  });
});
