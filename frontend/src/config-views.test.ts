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

async function addNew(view: El): Promise<void> {
  await click(view, '.top .primary');
}

describe('Personen', () => {
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
    await click(view, 'section.editor .primary');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/person/create');
    });
    expect(hass.messages.at(-1)?.['person']).toEqual({
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

  it('zeigt Fehler des Backends am Feld und im Hinweis', async () => {
    const { hass, view } = await open('/persons');
    await addNew(view);
    failNext(hass, { code: 'invalid_format', message: 'notify_target: invalid_format' });
    await click(view, 'section.editor .primary');
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
    await click(view, 'section.editor .primary');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/person/update');
    });
    expect(hass.messages.at(-1)?.['person_id']).toBe('p1');

    await click(view, '.card');
    await click(view, '.danger');
    expect(hass.messages.at(-1)?.type).toBe('task_wheel/person/update');
    expect(q(view.shadowRoot, '.danger').textContent).toContain('Wirklich');
    await click(view, '.danger');
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)?.type).toBe('task_wheel/person/delete');
    });
  });

  it('meldet, dass eine Person noch verwendet wird', async () => {
    const { hass, view } = await open('/persons');
    await click(view, '.card');
    failNext(hass, { code: 'in_use', message: 'in_use' });
    await click(view, '.danger');
    await click(view, '.danger');
    await vi.waitFor(() => {
      expect(q(view.shadowRoot, '.banner').textContent).toContain('verwendet');
    });
  });

  it('bricht ab und verwirft Entwürfe', async () => {
    const { view } = await open('/persons');
    await addNew(view);
    await click(view, 'section.editor .secondary');
    expect(view.shadowRoot?.querySelector('section.editor')).toBeNull();
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
    await click(view, 'section.editor .primary');
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
    });
  });

  it('bearbeitet eine Aufgabe und zeigt Prüffehler am Feld', async () => {
    const { hass, view } = await open('/tasks');
    await click(view, '.card');
    failNext(hass, { code: 'empty', message: 'allowed: empty' });
    await click(view, 'section.editor .primary');
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
    await click(view, 'section.editor .primary');
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

  it('legt einen neuen Zeitplan an und zeigt Auslöserfehler', async () => {
    const { hass, view } = await open('/schedules');
    await addNew(view);
    say(q(view.shadowRoot, 'section.editor tw-field'), 'Neu');
    failNext(hass, { code: 'required', message: 'trigger.time: required' });
    await click(view, 'section.editor .primary');
    await vi.waitFor(() => {
      expect(view.shadowRoot?.textContent).toContain('trigger.time');
    });
    expect(hass.messages.some((message) => message.type === 'task_wheel/schedule/create')).toBe(
      true,
    );
  });
});
