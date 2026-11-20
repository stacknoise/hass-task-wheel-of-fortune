import { describe, expect, it, vi } from 'vitest';

import { FakeHass } from './api/fake-hass.testing.ts';
import type { PlanPreviewWire, Snapshot } from './api/index.ts';
import {
  ANIMATION_KINDS,
  DEFAULT_ANIMATIONS,
  EVENT_CHANGE,
  PANEL_ELEMENT_NAME,
} from './constants/index.ts';
import type { ScheduleTab } from './constants/index.ts';
import type { TaskWheelPanel } from './task-wheel-panel.ts';
import './task-wheel-panel.ts';

type El = HTMLElement & { updateComplete: Promise<boolean>; [key: string]: unknown };

const SNAPSHOT: Snapshot = {
  persons: [
    {
      id: 'p1',
      name: 'Anna',
      slug: 'anna',
      color: '#4f8cff',
      load: 'full',
      absences: [],
      notify_target: 'notify.anna',
    },
  ],
  tasks: [
    {
      id: 't1',
      name: 'Müll',
      allowed: ['p1'],
      points: 2,
      no_repeat: false,
      respect_absence: true,
      swap_allowed: true,
      min_load: 'paused',
      area_ids: [],
    },
  ],
  schedules: [
    {
      id: 's1',
      name: 'Woche',
      slug: 'woche',
      start: '2026-11-23T17:00:00+00:00',
      interval: { unit: 'day', every: 7 },
      automatic: false,
      run_days: 30,
      entries: [{ task_id: 't1', mode: 'min_count', min_count: 2 }],
      enabled: false,
      notify: true,
      skip_absent: true,
      archived: true,
    },
  ],
  assignments: [],
  rounds: [],
  panel_rounds: [],
  settings: {},
  now: '2026-11-03T12:00:00+00:00',
};

const PLAN: PlanPreviewWire = {
  draws_per_run: 4,
  interval_hours: 168,
  persons: { p1: 1 },
  planned: 2,
  capacity: 4,
  empty_draws: 0,
  overloaded_draws: 0,
  peak: 1,
  tracks: [],
  issues: [],
};

async function open(path: string): Promise<{ hass: FakeHass; view: El }> {
  const hass = new FakeHass();
  hass.snapshot = SNAPSHOT;
  hass.replies.set('task_wheel/schedule/plan_preview', PLAN);
  const panel = document.createElement(PANEL_ELEMENT_NAME) as TaskWheelPanel;
  panel.route = { prefix: '/task-wheel', path };
  panel.hass = hass;
  document.body.append(panel);
  const tag = `tw-${path.slice(1)}-view`;
  const view = await vi.waitFor(() => {
    const found = panel.shadowRoot?.querySelector(tag) as El | null;
    if (!found?.shadowRoot?.querySelector('.layout')) {
      throw new Error('noch nicht da');
    }
    return found;
  });
  return { hass, view };
}

const q = (root: Element | ShadowRoot | null | undefined, selector: string): El =>
  root?.querySelector(selector) as El;

const button = (view: El, selector: string): HTMLButtonElement =>
  q(view.shadowRoot, selector) as unknown as HTMLButtonElement;

async function click(view: El, selector: string): Promise<void> {
  button(view, selector).click();
  await view.updateComplete;
}

function say(child: Element, detail: unknown): void {
  child.dispatchEvent(new CustomEvent(EVENT_CHANGE, { detail, bubbles: true, composed: true }));
}

/** Wechselt im Zeitplan-Editor zu einem Reiter. */
async function showTab(view: El, tab: ScheduleTab): Promise<void> {
  say(q(view.shadowRoot, 'tw-section-tabs'), tab);
  await view.updateComplete;
}

/** Der nächste Befehl (außer Lesen) scheitert wie bei Home Assistant mit `{ code, message }`. */
function failNext(hass: FakeHass, error: { code: string; message: string }): void {
  const original = hass.callWS.bind(hass);
  hass.callWS = <T>(message: { type: string; [field: string]: unknown }): Promise<T> => {
    hass.callWS = original;
    if (message.type.endsWith('snapshot')) {
      return original<T>(message);
    }
    hass.messages.push(message);
    return Promise.reject(Object.assign(new Error(error.message), error));
  };
}

/** Der letzte Befehl, der etwas ändert (die Vorschau-Abfragen zählen nicht). */
const lastChange = (hass: FakeHass): FakeHass['messages'][number] | undefined =>
  hass.messages.filter((message) => !message.type.endsWith('preview')).at(-1);

/** Bestätigt die Rückfrage zum Löschen im Popup. */
async function confirmDelete(view: El): Promise<void> {
  const dialog = q(view.shadowRoot, 'tw-confirm-dialog');
  await dialog.updateComplete;
  (dialog.shadowRoot?.querySelector('.danger') as HTMLButtonElement).click();
  await view.updateComplete;
}

async function addNew(view: El): Promise<void> {
  await click(view, '.top .primary');
}

describe('Personen', () => {
  it('bietet Benachrichtigungsziele zum Suchen an', async () => {
    const { view } = await open('/persons');
    await addNew(view);
    const field = [...q(view.shadowRoot, 'section.editor').querySelectorAll('tw-field')].at(
      -1,
    ) as El;
    await (field as unknown as { updateComplete: Promise<unknown> }).updateComplete;
    const options = [...(field.shadowRoot?.querySelectorAll('datalist option') ?? [])].map(
      (option) => [option.getAttribute('value'), option.getAttribute('label')].join('|'),
    );
    expect(options).toEqual([
      'notify.handy_anna|Handy Anna',
      'notify.kueche|notify.kueche',
      'notify.mobile_app_ben|mobile_app_ben',
    ]);
  });

  it('legt eine Person an', async () => {
    const { hass, view } = await open('/persons');
    expect(view.shadowRoot?.textContent).toContain('Anna');
    await addNew(view);
    const editor = q(view.shadowRoot, 'section.editor');
    say(q(editor, 'tw-field'), 'Berta');
    say(q(editor, 'tw-select'), 'half');
    await view.updateComplete;
    button(view, 'section.editor .swatch:nth-child(2)').click();
    say(q(editor, 'tw-absence-editor'), [{ kind: 'weekly_days', weekdays: [5] }]);
    say([...editor.querySelectorAll('tw-field')].at(-1) as El, ' notify.berta ');
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(lastChange(hass)?.type).toBe('task_wheel/person/create');
    });
    expect(lastChange(hass)?.['person']).toEqual({
      name: 'Berta',
      color: '#e8590c',
      load: 'half',
      absences: [{ kind: 'weekly_days', weekdays: [5] }],
      notify_target: 'notify.berta',
    });
    await vi.waitFor(() => {
      expect(view.shadowRoot?.querySelector('section.editor')).toBeNull();
    });
  });

  it('zeigt die Anwesenheitsvorschau des Backends und fragt bei jeder Änderung der Regeln neu', async () => {
    const { hass, view } = await open('/persons');
    hass.replies.set('task_wheel/availability/preview', { present: [true, false, true] });
    await addNew(view);
    const editor = q(view.shadowRoot, 'section.editor');
    const absences = [{ kind: 'weekly_days', weekdays: [1] }];
    say(q(editor, 'tw-absence-editor'), absences);
    const days = async (): Promise<number> => {
      await view.updateComplete;
      const preview = q(q(editor, 'tw-absence-editor').shadowRoot, 'tw-week-preview');
      return preview.shadowRoot?.querySelectorAll('.day').length ?? 0;
    };
    await vi.waitFor(async () => {
      expect(await days()).toBe(3);
    });
    const asked = hass.messages.filter((m) => m.type === 'task_wheel/availability/preview');
    expect(asked.at(-1)?.['absences']).toEqual(absences);

    hass.replies.set('task_wheel/availability/preview', new Error('ungültig'));
    say(q(editor, 'tw-absence-editor'), [...absences, { kind: 'weekly_days', weekdays: [2] }]);
    await vi.waitFor(() => {
      expect(
        hass.messages.filter((m) => m.type === 'task_wheel/availability/preview'),
      ).toHaveLength(asked.length + 1);
    });
    expect(await days()).toBe(3);
  });

  it('zeigt Fehler des Backends am Feld und im Hinweis', async () => {
    const { hass, view } = await open('/persons');
    await addNew(view);
    failNext(hass, { code: 'invalid_format', message: 'notify_target: invalid_format' });
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(q(view.shadowRoot, '.banner').textContent).toContain('notify_target');
    });
    expect(view.shadowRoot?.querySelector('section.editor')).not.toBeNull();
    expect(q(view.shadowRoot, 'section.editor').innerHTML).toBeDefined();
  });

  it('öffnet eine Karte auch mit der Tastatur und benennt sie nach dem Objekt', async () => {
    const { view } = await open('/persons');
    const card = q(view.shadowRoot, '.card');
    expect(card.getAttribute('role')).toBe('button');
    expect(card.getAttribute('aria-label')).toBeTruthy();
    card.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    await view.updateComplete;
    expect(view.shadowRoot?.querySelector('tw-dialog')).not.toBeNull();
  });

  it('ändert eine Person und löscht sie erst nach Bestätigung', async () => {
    const { hass, view } = await open('/persons');
    await click(view, '.card');
    say(q(view.shadowRoot, 'section.editor tw-field'), 'Anna B.');
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/person/update');
    });
    expect(hass.messages.at(-1)?.['person_id']).toBe('p1');

    await click(view, '.card');
    await click(view, '.buttons .danger');
    expect(hass.messages.at(-1)?.type).toBe('task_wheel/person/update');
    expect(q(view.shadowRoot, 'tw-confirm-dialog').getAttribute('question')).toContain('Wirklich');
    await confirmDelete(view);
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/person/delete');
    });
  });

  it('meldet, dass eine Person noch verwendet wird', async () => {
    const { hass, view } = await open('/persons');
    await click(view, '.card');
    failNext(hass, { code: 'in_use', message: 'in_use' });
    await click(view, '.buttons .danger');
    await confirmDelete(view);
    await vi.waitFor(() => {
      expect(q(view.shadowRoot, '.banner').textContent).toContain('verwendet');
    });
  });

  it('bricht ab und verwirft Entwürfe', async () => {
    const { view } = await open('/persons');
    await addNew(view);
    await click(view, '.buttons .secondary');
    expect(view.shadowRoot?.querySelector('tw-dialog')).toBeNull();
  });

  it('öffnet das Formular im Dialog und schließt es mit Escape', async () => {
    const { view } = await open('/persons');
    await addNew(view);
    const dialog = q(view.shadowRoot, 'tw-dialog');
    expect(dialog.getAttribute('label')).toBeTruthy();
    await dialog.updateComplete;
    dialog.shadowRoot
      ?.querySelector('.dialog')
      ?.dispatchEvent(new Event('cancel', { cancelable: true }));
    await view.updateComplete;
    expect(view.shadowRoot?.querySelector('tw-dialog')).toBeNull();
  });

  it('bricht die Löschrückfrage ab', async () => {
    const { view } = await open('/persons');
    await click(view, '.card');
    await click(view, '.buttons .danger');
    const ask = q(view.shadowRoot, 'tw-confirm-dialog');
    await ask.updateComplete;
    (ask.shadowRoot?.querySelectorAll('button')[1] as HTMLButtonElement).click();
    await view.updateComplete;
    expect(view.shadowRoot?.querySelector('tw-confirm-dialog')).toBeNull();
    expect(view.shadowRoot?.querySelector('tw-dialog')).not.toBeNull();
  });
});

describe('Aufgaben', () => {
  it('legt eine Aufgabe mit allen Feldern an', async () => {
    const { hass, view } = await open('/tasks');
    expect(view.shadowRoot?.textContent).toContain('Zeitpläne: 1');
    await addNew(view);
    const editor = q(view.shadowRoot, 'section.editor');
    expect(editor.textContent).toContain('Noch in keinem Zeitplan');
    expect(editor.querySelector('tw-frequency-editor')).toBeNull();
    say(q(editor, 'tw-field'), 'Bad putzen');
    say(q(editor, 'tw-chip-select'), ['p1']);
    say(q(editor, 'tw-stepper'), 5);
    for (const toggle of editor.querySelectorAll('tw-toggle')) {
      say(toggle, false);
    }
    const area = editor.querySelectorAll('tw-chip-select')[1] as El;
    expect((area['options'] as readonly { id: string }[]).map((option) => option.id)).toEqual([
      'bad',
      'kueche',
    ]);
    say(area, ['bad', 'kueche']);
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/task/create');
    });
    expect(hass.messages.at(-1)?.['task']).toEqual({
      name: 'Bad putzen',
      allowed: ['p1'],
      points: 5,
      no_repeat: false,
      respect_absence: false,
      swap_allowed: false,
      min_load: 'paused',
      area_ids: ['bad', 'kueche'],
    });
  });

  it('bearbeitet eine Aufgabe und zeigt Prüffehler am Feld', async () => {
    const { hass, view } = await open('/tasks');
    await click(view, '.card');
    failNext(hass, { code: 'empty', message: 'allowed: empty' });
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(q(view.shadowRoot, 'tw-chip-select').getAttribute('error')).toBeDefined();
    });
    const chips = q(view.shadowRoot, 'tw-chip-select');
    expect(chips.error).toBe('Darf nicht leer sein.');
  });
});

describe('Zeitpläne', () => {
  it('zeigt Beispiel, hebt die Archivierung beim Aktivieren auf und speichert', async () => {
    const { hass, view } = await open('/schedules');
    expect(view.shadowRoot?.textContent).toContain('Archiviert');
    expect(view.shadowRoot?.textContent).toContain('alle 7 Tage, manuell');
    expect(view.shadowRoot?.textContent).toContain('Lauf: 30 Tage · 1 Aufgaben');
    await click(view, '.card');
    await showTab(view, 'options');
    expect(q(view.shadowRoot, 'section.editor').textContent).toContain('schedule: woche');
    const toggles = [...(view.shadowRoot?.querySelectorAll('section.editor tw-toggle') ?? [])];
    say(toggles[0] as El, true);
    await showTab(view, 'tasks');
    say(q(view.shadowRoot, 'tw-entry-editor'), []);
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(lastChange(hass)?.type).toBe('task_wheel/schedule/update');
    });
    expect(lastChange(hass)?.['schedule']).toEqual({
      name: 'Woche',
      start: '2026-11-23T17:00:00+00:00',
      interval: { unit: 'day', every: 7 },
      automatic: false,
      run_days: 30,
      entries: [],
      enabled: true,
      notify: true,
      skip_absent: true,
      archived: false,
      animations: [...DEFAULT_ANIMATIONS],
    });
  });

  it('stellt Beginn, Intervall, Art der Auslosung und Lauf ein', async () => {
    const { hass, view } = await open('/schedules');
    await click(view, '.card');
    const editor = q(view.shadowRoot, 'section.editor');
    say(q(editor, 'tw-field[type="datetime-local"]'), '2026-12-01T08:30');
    say(q(editor, '.pair tw-stepper'), 2);
    await view.updateComplete;
    say(q(editor, '.pair tw-select'), 'week');
    say(q(editor, 'tw-segmented'), 'automatic');
    say(q(editor, 'tw-stepper:not(.pair tw-stepper)'), 14);
    await view.updateComplete;
    expect(editor.textContent).toContain('Das System lost zur Startzeit');
    expect(editor.textContent).toContain('Ausgelost wird alle 2 Wochen.');
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(lastChange(hass)?.type).toBe('task_wheel/schedule/update');
    });
    const sent = lastChange(hass)?.['schedule'] as { start: string };
    expect(sent).toMatchObject({
      interval: { unit: 'week', every: 2 },
      automatic: true,
      run_days: 14,
    });
    expect(sent.start.endsWith('Z')).toBe(true);
  });

  it('rechnet die Planung im Backend nach und sperrt das Speichern bei blockierenden Hinweisen', async () => {
    const { hass, view } = await open('/schedules');
    hass.replies.set('task_wheel/schedule/plan_preview', {
      ...PLAN,
      issues: [{ code: 'no_person', blocking: true, params: {} }],
    });
    await click(view, '.card');
    await showTab(view, 'tasks');
    say(q(view.shadowRoot, 'tw-entry-editor'), [
      { task_id: 't1', mode: 'every_draw', min_count: 1 },
    ]);
    await vi.waitFor(() => {
      expect(button(view, '.buttons .primary').disabled).toBe(true);
    });
    const plan = hass.messages.filter((message) => message.type.endsWith('plan_preview')).at(-1);
    expect(plan).toMatchObject({
      interval: { unit: 'day', every: 7 },
      run_days: 30,
      entries: [{ task_id: 't1', mode: 'every_draw' }],
    });
    expect(q(view.shadowRoot, 'section.editor').textContent).not.toContain('Keine Person');
    expect(q(view.shadowRoot, '.status button').textContent).toContain('1 Hinweis');
    await click(view, '.status button');
    expect(q(view.shadowRoot, 'tw-plan-preview').shadowRoot?.textContent).toContain(
      'Keine Person kann die gewählten Aufgaben übernehmen',
    );

    hass.replies.set('task_wheel/schedule/plan_preview', { ...PLAN, issues: [] });
    await showTab(view, 'tasks');
    say(q(view.shadowRoot, 'tw-entry-editor'), []);
    await vi.waitFor(() => {
      expect(button(view, '.buttons .primary').disabled).toBe(false);
    });
  });

  it('wählt die Animationen per Mehrfachauswahl und speichert sie', async () => {
    const { hass, view } = await open('/schedules');
    await click(view, '.card');
    await showTab(view, 'options');
    const selects = [...(view.shadowRoot?.querySelectorAll('section.editor tw-chip-select') ?? [])];
    expect(selects).toHaveLength(1);
    const animations = selects[0] as El;
    expect((animations as unknown as { options: unknown[] }).options).toHaveLength(
      ANIMATION_KINDS.length,
    );
    say(animations, ['drum', 'plinko']);
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(lastChange(hass)?.type).toBe('task_wheel/schedule/update');
    });
    expect(lastChange(hass)?.['schedule']).toMatchObject({ animations: ['drum', 'plinko'] });
  });

  it('teilt den Editor in Reiter mit Zähler und startet immer auf dem Ablauf', async () => {
    const { view } = await open('/schedules');
    await click(view, '.card');
    const tabs = q(view.shadowRoot, 'tw-section-tabs') as unknown as {
      tabs: { id: string; badge?: number }[];
      active: string;
    };
    expect(tabs.tabs.map((tab) => tab.id)).toEqual(['basics', 'tasks', 'review', 'options']);
    expect(tabs.tabs.find((tab) => tab.id === 'tasks')?.badge).toBe(1);
    expect(tabs.active).toBe('basics');
    expect(q(view.shadowRoot, 'section.editor tw-entry-editor')).toBeNull();
    await showTab(view, 'tasks');
    expect(q(view.shadowRoot, 'section.editor tw-entry-editor')).not.toBeNull();
    expect(q(view.shadowRoot, 'section.editor tw-field')).toBeNull();
    await click(view, '.buttons .secondary');
    await click(view, '.card');
    expect((q(view.shadowRoot, 'tw-section-tabs') as unknown as { active: string }).active).toBe(
      'basics',
    );
  });

  it('springt von einem Hinweis zur Aufgabe in der Liste', async () => {
    const { hass, view } = await open('/schedules');
    hass.replies.set('task_wheel/schedule/plan_preview', {
      ...PLAN,
      issues: [
        { code: 'too_often', blocking: false, params: { task_id: 't1', wanted: 9, draws: 4 } },
      ],
    });
    await click(view, '.card');
    await vi.waitFor(() => {
      expect(q(view.shadowRoot, '.status button').textContent).toContain('1 Hinweis');
    });
    await click(view, '.status button');
    const plan = q(view.shadowRoot, 'tw-plan-preview');
    (plan.shadowRoot?.querySelector('.issue .go') as HTMLButtonElement).click();
    await view.updateComplete;
    const entries = q(view.shadowRoot, 'tw-entry-editor');
    await entries.updateComplete;
    expect(
      (entries.shadowRoot?.querySelector('input[type="search"]') as HTMLInputElement).value,
    ).toBe('Müll');
  });

  it('legt einen neuen Zeitplan an und zeigt Fehler am Intervall', async () => {
    const { hass, view } = await open('/schedules');
    await addNew(view);
    say(q(view.shadowRoot, 'section.editor tw-field'), 'Neu');
    failNext(hass, { code: 'out_of_range', message: 'interval.every: out_of_range' });
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(view.shadowRoot?.textContent).toContain('Wert außerhalb des erlaubten Bereichs.');
    });
    expect(hass.messages.some((message) => message.type === 'task_wheel/schedule/create')).toBe(
      true,
    );
  });
});
