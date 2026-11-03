import { describe, expect, it, vi } from 'vitest';

import { FakeHass } from './api/fake-hass.testing.ts';
import type { Snapshot } from './api/index.ts';
import { EVENT_CHANGE, PANEL_ELEMENT_NAME } from './constants/index.ts';
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
      frequency: { kind: 'every_round' },
      points: 2,
      due_days: 7,
      no_repeat: false,
      respect_absence: true,
      swap_allowed: true,
      min_load: 'paused',
    },
  ],
  schedules: [
    {
      id: 's1',
      name: 'Woche',
      slug: 'woche',
      trigger: { kind: 'manual', remind_after_days: null },
      task_ids: ['t1'],
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

async function open(path: string): Promise<{ hass: FakeHass; view: El }> {
  const hass = new FakeHass();
  hass.snapshot = SNAPSHOT;
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
  hass.messages.filter((message) => !message.type.endsWith('/preview')).at(-1);

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
      ?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
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
    expect(view.shadowRoot?.textContent).toContain('jede Runde');
    await addNew(view);
    const editor = q(view.shadowRoot, 'section.editor');
    say(q(editor, 'tw-field'), 'Bad putzen');
    say(q(editor, 'tw-chip-select'), ['p1']);
    say(q(editor, 'tw-frequency-editor'), { kind: 'interval', days: 7, tolerance: 1 });
    const [points, due] = [...editor.querySelectorAll('tw-stepper')];
    say(points as El, 5);
    say(due as El, 3);
    for (const toggle of editor.querySelectorAll('tw-toggle')) {
      say(toggle, false);
    }
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/task/create');
    });
    expect(hass.messages.at(-1)?.['task']).toEqual({
      name: 'Bad putzen',
      allowed: ['p1'],
      frequency: { kind: 'interval', days: 7, tolerance: 1 },
      points: 5,
      due_days: 3,
      no_repeat: false,
      respect_absence: false,
      swap_allowed: false,
      min_load: 'paused',
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
    await click(view, '.card');
    expect(q(view.shadowRoot, 'section.editor').textContent).toContain('schedule: woche');
    const toggles = [...(view.shadowRoot?.querySelectorAll('section.editor tw-toggle') ?? [])];
    say(toggles[0] as El, true);
    say(q(view.shadowRoot, 'tw-trigger-editor'), { kind: 'manual', remind_after_days: 3 });
    say(q(view.shadowRoot, 'tw-chip-select'), []);
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/schedule/update');
    });
    expect(hass.messages.at(-1)?.['schedule']).toMatchObject({
      enabled: true,
      archived: false,
      task_ids: [],
      trigger: { kind: 'manual', remind_after_days: 3 },
    });
  });

  it('wählt die Animationen per Mehrfachauswahl und speichert sie', async () => {
    const { hass, view } = await open('/schedules');
    await click(view, '.card');
    const selects = [...(view.shadowRoot?.querySelectorAll('section.editor tw-chip-select') ?? [])];
    expect(selects).toHaveLength(2);
    const animations = selects[1] as El;
    expect((animations as unknown as { options: unknown[] }).options).toHaveLength(5);
    say(animations, ['drum', 'plinko']);
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/schedule/update');
    });
    expect(hass.messages.at(-1)?.['schedule']).toMatchObject({ animations: ['drum', 'plinko'] });
  });

  it('legt einen neuen Zeitplan an und zeigt Auslöserfehler', async () => {
    const { hass, view } = await open('/schedules');
    await addNew(view);
    say(q(view.shadowRoot, 'section.editor tw-field'), 'Neu');
    failNext(hass, { code: 'required', message: 'trigger.time: required' });
    await click(view, '.buttons .primary');
    await vi.waitFor(() => {
      expect(view.shadowRoot?.textContent).toContain('trigger.time');
    });
    expect(hass.messages.some((message) => message.type === 'task_wheel/schedule/create')).toBe(
      true,
    );
  });
});
