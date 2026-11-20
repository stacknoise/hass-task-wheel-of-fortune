import { describe, expect, it } from 'vitest';

import { EVENT_CHANGE, EVENT_GOTO_TASK, FORM_TAGS } from '../constants/index.ts';
import type { EntryWire, PlanPreviewWire } from '../state/index.ts';
import { describeInterval, describeSpan } from './summaries.ts';
import './index.ts';

type El = HTMLElement & { updateComplete: Promise<boolean>; [key: string]: unknown };

async function mount(tag: string, props: Record<string, unknown> = {}): Promise<El> {
  const element = document.createElement(tag) as El;
  Object.assign(element, props);
  document.body.append(element);
  await element.updateComplete;
  return element;
}

function changes(element: HTMLElement): unknown[] {
  const seen: unknown[] = [];
  element.addEventListener(EVENT_CHANGE, (event) => {
    seen.push((event as CustomEvent).detail);
  });
  return seen;
}

function part(element: El, selector: string): El {
  const found = element.shadowRoot?.querySelector(selector);
  if (!found) {
    throw new Error(`nicht gefunden: ${selector}`);
  }
  return found as El;
}

/** Simuliert die Meldung eines Bausteins in der Maske eines Editors. */
function say(child: El, detail: unknown): void {
  child.dispatchEvent(new CustomEvent(EVENT_CHANGE, { detail, bubbles: true, composed: true }));
}

describe('Formularbausteine', () => {
  it('Feld meldet Eingaben und zeigt einen Fehler', async () => {
    const field = await mount(FORM_TAGS.field, {
      label: 'Name',
      value: 'a',
      error: 'kaputt',
      maxlength: 5,
    });
    const seen = changes(field);
    const input = part(field, 'input') as unknown as HTMLInputElement;
    input.value = 'ab';
    input.dispatchEvent(new Event('input'));
    expect(seen).toEqual(['ab']);
    expect(part(field, '.error').textContent).toBe('kaputt');
    expect(input.getAttribute('maxlength')).toBe('5');
  });

  it('Schalter meldet den neuen Zustand', async () => {
    const toggle = await mount(FORM_TAGS.toggle, { label: 'Aktiv' });
    const seen = changes(toggle);
    const box = part(toggle, 'input') as unknown as HTMLInputElement;
    box.checked = true;
    box.dispatchEvent(new Event('change'));
    expect(seen).toEqual([true]);
  });

  it('Stepper bleibt zwischen Minimum und Maximum', async () => {
    const stepper = await mount(FORM_TAGS.stepper, { value: 1, min: 1, max: 2 });
    const seen = changes(stepper);
    const [minus, plus] = [...(stepper.shadowRoot?.querySelectorAll('button') ?? [])];
    expect(minus?.disabled).toBe(true);
    plus?.click();
    expect(seen).toEqual([2]);
    stepper.value = 2;
    await stepper.updateComplete;
    expect(plus?.disabled).toBe(true);
    minus?.click();
    expect(seen).toEqual([2, 1]);
  });

  it('Chip-Auswahl schaltet Chips um und meldet in Reihenfolge der Optionen', async () => {
    const chips = await mount(FORM_TAGS.chipSelect, {
      options: [
        { id: 'a', label: 'A', color: '#fff' },
        { id: 'b', label: 'B' },
      ],
      selected: ['b'],
      error: 'leer',
    });
    const seen = changes(chips);
    const [first, second] = [...(chips.shadowRoot?.querySelectorAll('button') ?? [])];
    expect(second?.getAttribute('aria-pressed')).toBe('true');
    first?.click();
    second?.click();
    expect(seen).toEqual([['a', 'b'], []]);
    expect(part(chips, '.error').textContent).toBe('leer');
  });

  it('Segment-Umschalter meldet die Wahl', async () => {
    const bar = await mount(FORM_TAGS.segmented, {
      options: [
        { id: 'x', label: 'X' },
        { id: 'y', label: 'Y' },
      ],
      value: 'x',
    });
    const seen = changes(bar);
    const [, second] = [...(bar.shadowRoot?.querySelectorAll('button') ?? [])];
    second?.click();
    expect(seen).toEqual(['y']);
  });

  it('Dropdown zeigt die Wahl an und meldet Änderungen', async () => {
    const select = await mount(FORM_TAGS.select, {
      options: [
        { id: 'x', label: 'X' },
        { id: 'y', label: 'Y' },
      ],
      value: 'y',
    });
    const seen = changes(select);
    const box = part(select, 'select') as unknown as HTMLSelectElement;
    expect(box.value).toBe('y');
    box.value = 'x';
    box.dispatchEvent(new Event('change'));
    expect(seen).toEqual(['x']);
  });

  it('Wochenvorschau zeigt ihre Werte', async () => {
    const preview = await mount(FORM_TAGS.weekPreview, { language: 'de', present: [true, false] });
    expect(preview.shadowRoot?.querySelectorAll('.day.absent')).toHaveLength(1);
    expect(preview.shadowRoot?.textContent).toContain('Mo');
  });
});

describe('Editoren', () => {
  it('Abwesenheiten: hinzufügen, ändern, Art wechseln, entfernen; Vorschau folgt', async () => {
    const editor = await mount(FORM_TAGS.absenceEditor, {
      language: 'de',
      today: '2026-11-03',
      value: [],
    });
    const seen = changes(editor);
    expect(editor.shadowRoot?.textContent).toContain('Immer anwesend');
    (editor.shadowRoot?.querySelector('.actions button') as HTMLButtonElement).click();
    expect(seen.at(-1)).toEqual([{ kind: 'once', start: '2026-11-03', end: '2026-11-03' }]);

    editor.value = seen.at(-1);
    await editor.updateComplete;
    const [start] = [...(editor.shadowRoot?.querySelectorAll('tw-field') ?? [])] as El[];
    say(start as El, '2026-11-02');
    expect((seen.at(-1) as { start: string }[])[0]?.start).toBe('2026-11-02');

    say(part(editor, 'tw-select'), 'weekly_days');
    expect(seen.at(-1)).toEqual([{ kind: 'weekly_days', weekdays: [5, 6] }]);
    say(part(editor, 'tw-select'), 'week_rhythm');
    editor.value = seen.at(-1);
    await editor.updateComplete;

    say(part(editor, 'tw-stepper'), 1);
    expect(seen.at(-1)).toMatchObject([{ cycle_weeks: 1, present_weeks: [0] }]);
    say(part(editor, 'tw-chip-select'), ['0']);
    say(part(editor, '.rule > tw-select'), '2');
    (editor.shadowRoot?.querySelector('.head button') as HTMLButtonElement).click();
    expect(seen.at(-1)).toEqual([]);
  });

  it('Abwesenheit: Wochentage', async () => {
    const editor = await mount(FORM_TAGS.absenceEditor, {
      language: 'en',
      today: '2026-11-03',
      value: [{ kind: 'weekly_days', weekdays: [5] }],
    });
    const seen = changes(editor);
    say(part(editor, 'tw-chip-select'), ['0', '6']);
    expect(seen).toEqual([[{ kind: 'weekly_days', weekdays: [0, 6] }]]);
  });

  it('Abwesenheit: wiederkehrend mit optionalem Ende', async () => {
    const editor = await mount(FORM_TAGS.absenceEditor, {
      language: 'en',
      today: '2026-11-03',
      value: [
        { kind: 'recurring', weekdays: [2], interval_weeks: 2, start: '2026-11-04', end: null },
      ],
    });
    const seen = changes(editor);
    say(part(editor, 'tw-stepper'), 3);
    expect(seen.at(-1)).toMatchObject([{ kind: 'recurring', interval_weeks: 3, end: null }]);
    const fields = [...(editor.shadowRoot?.querySelectorAll('tw-field') ?? [])] as El[];
    say(fields[1] as El, '2027-01-06');
    expect(seen.at(-1)).toMatchObject([{ end: '2027-01-06' }]);
    say(fields[1] as El, '');
    expect(seen.at(-1)).toMatchObject([{ end: null }]);
  });

  it('Zeitplan-Aufgaben: wählen, Mindestanzahl und jede Auslosung ändern', async () => {
    const tasks = [
      { id: 'a', label: 'Bad' },
      { id: 'b', label: 'Müll' },
    ];
    const editor = await mount(FORM_TAGS.entryEditor, {
      language: 'de',
      tasks,
      runDays: 30,
      value: [{ task_id: 'b', mode: 'min_count', min_count: 2 }] satisfies EntryWire[],
    });
    const seen = changes(editor);
    const toggles = [...(editor.shadowRoot?.querySelectorAll('.name > tw-toggle') ?? [])] as El[];
    say(toggles[0] as El, true);
    expect(seen.at(-1)).toEqual([
      { task_id: 'a', mode: 'min_count', min_count: 1 },
      { task_id: 'b', mode: 'min_count', min_count: 2 },
    ]);
    say(toggles[1] as El, false);
    expect(seen.at(-1)).toEqual([]);

    expect(editor.shadowRoot?.textContent).toContain('ca. alle 15 Tage');
    say(part(editor, 'tw-stepper'), 3);
    expect(seen.at(-1)).toEqual([{ task_id: 'b', mode: 'min_count', min_count: 3 }]);
    part(editor, '.every').click();
    expect(seen.at(-1)).toEqual([{ task_id: 'b', mode: 'every_draw', min_count: 2 }]);

    editor.value = [{ task_id: 'b', mode: 'every_draw', min_count: 2 }];
    await editor.updateComplete;
    expect(editor.shadowRoot?.querySelector('tw-stepper')).toBeNull();
    expect(editor.shadowRoot?.textContent).toContain('in jeder Auslosung');
    part(editor, '.every').click();
    expect(seen.at(-1)).toEqual([{ task_id: 'b', mode: 'min_count', min_count: 2 }]);
  });

  it('Zeitplan-Aufgaben: suchen, filtern und nach Raum eingrenzen', async () => {
    const room = (name: string): { name: string; deleted: boolean } => ({ name, deleted: false });
    const editor = await mount(FORM_TAGS.entryEditor, {
      language: 'de',
      runDays: 30,
      tasks: [
        { id: 'a', label: 'Bad putzen', rooms: [room('Bad')] },
        { id: 'b', label: 'Müll rausbringen', rooms: [room('Küche'), room('Flur')] },
        { id: 'c', label: 'Staub wischen', rooms: [room('Flur')] },
      ],
      value: [{ task_id: 'b', mode: 'min_count', min_count: 2 }] satisfies EntryWire[],
    });
    const names = (): string[] =>
      [...(editor.shadowRoot?.querySelectorAll('.row tw-toggle') ?? [])].map(
        (toggle) => (toggle as unknown as { label: string }).label,
      );
    const search = part(editor, 'input[type="search"]') as unknown as HTMLInputElement;
    expect(names()).toEqual(['Bad putzen', 'Müll rausbringen', 'Staub wischen']);

    search.value = 'flur';
    search.dispatchEvent(new Event('input'));
    await editor.updateComplete;
    expect(names()).toEqual(['Müll rausbringen', 'Staub wischen']);

    search.value = '';
    search.dispatchEvent(new Event('input'));
    say(part(editor, 'tw-segmented'), 'selected');
    await editor.updateComplete;
    expect(names()).toEqual(['Müll rausbringen']);
    say(part(editor, 'tw-segmented'), 'open');
    await editor.updateComplete;
    expect(names()).toEqual(['Bad putzen', 'Staub wischen']);
    say(part(editor, 'tw-segmented'), 'all');

    const rooms = [
      ...(editor.shadowRoot?.querySelectorAll('.rooms button') ?? []),
    ] as HTMLElement[];
    expect(rooms.map((button) => button.textContent.trim())).toEqual(['Bad', 'Flur', 'Küche']);
    rooms[1]?.click();
    await editor.updateComplete;
    expect(names()).toEqual(['Müll rausbringen', 'Staub wischen']);
    rooms[1]?.click();
    search.value = 'kein Treffer';
    search.dispatchEvent(new Event('input'));
    await editor.updateComplete;
    expect(names()).toEqual([]);
    expect(editor.shadowRoot?.textContent).toContain('Keine Aufgabe passt zu Suche und Filter.');
  });

  it('Reiter melden die Wahl, auch mit den Pfeiltasten', async () => {
    const tabs = await mount(FORM_TAGS.sectionTabs, {
      label: 'Bereiche',
      active: 'b',
      tabs: [
        { id: 'a', label: 'A' },
        { id: 'b', label: 'B', badge: 2, warn: true },
        { id: 'c', label: 'C' },
      ],
    });
    const seen = changes(tabs);
    expect(tabs.shadowRoot?.querySelector('.badge.warn')?.textContent).toBe('2');
    expect(part(tabs, '[aria-selected="true"]').textContent).toContain('B');
    (part(tabs, '#c') as unknown as HTMLButtonElement).click();
    expect(seen.at(-1)).toBe('c');
    const key = (name: string): void => {
      part(tabs, '.tabs').dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true }));
    };
    key('ArrowRight');
    expect(seen.at(-1)).toBe('c');
    key('ArrowLeft');
    expect(seen.at(-1)).toBe('a');
    key('x');
    expect(seen).toHaveLength(3);
    tabs.active = 'c';
    await tabs.updateComplete;
    seen.length = 0;
    key('ArrowRight');
    expect(seen).toEqual([]);
  });

  it('Auswertung zeigt Zahlen, Personen, Abstände und Hinweise', async () => {
    const preview: PlanPreviewWire = {
      draws_per_run: 4,
      interval_hours: 168,
      persons: { p1: 2 },
      planned: 6,
      capacity: 4,
      empty_draws: 1,
      overloaded_draws: 2,
      peak: 3,
      tracks: [
        { task_id: 'a', every_draw: false, wanted: 2, positions: [0, 2], gap_min: 2, gap_max: 2 },
        {
          task_id: 'b',
          every_draw: true,
          wanted: 4,
          positions: [0, 1, 2, 3],
          gap_min: 1,
          gap_max: 1,
        },
      ],
      issues: [
        { code: 'no_person', blocking: true, params: {} },
        { code: 'too_often', blocking: false, params: { task_id: 'a', wanted: 9, draws: 4 } },
        { code: 'unbekannt', blocking: false, params: {} },
      ],
    };
    const element = await mount(FORM_TAGS.planPreview, {
      language: 'de',
      runDays: 30,
      preview,
      tasks: [
        {
          id: 'a',
          label: 'Bad',
          rooms: [
            { name: 'Bad', deleted: false },
            { name: 'Flur', deleted: false },
          ],
        },
      ],
      people: [{ id: 'p1', label: 'Anna', color: '#e03131' }],
    });
    const text = element.shadowRoot?.textContent ?? '';
    expect(element.shadowRoot?.querySelectorAll('.kpi')).toHaveLength(3);
    expect(element.shadowRoot?.querySelectorAll('.kpi.warn')).toHaveLength(2);
    expect(element.shadowRoot?.querySelectorAll('.person')).toHaveLength(1);
    expect(element.shadowRoot?.querySelector('.person')?.textContent).toMatch(/Anna\s+2/u);
    expect(element.shadowRoot?.querySelector('.issue .go')).not.toBeNull();
    // Zuerst nur die Aufgabe, die ein Hinweis nennt; „Alle“ zeigt auch die übrigen.
    expect(element.shadowRoot?.querySelectorAll('.track')).toHaveLength(1);
    expect(element.shadowRoot?.querySelectorAll('.track tw-room')).toHaveLength(2);
    expect(text).toContain('2 Wochen');
    say(part(element, 'tw-segmented'), 'all');
    await element.updateComplete;
    expect(element.shadowRoot?.textContent).toContain('jede Auslosung');
    expect(element.shadowRoot?.querySelectorAll('.bar')).toHaveLength(2);
    expect(element.shadowRoot?.querySelectorAll('.dot.ghost').length).toBeGreaterThan(0);
    expect(element.shadowRoot?.querySelectorAll('.issue.blocking')).toHaveLength(1);
    expect(text).toContain('„Bad“ steht auf mindestens 9×');
    expect(text).toContain('Unbekannter Fehler.');
    const goto: string[] = [];
    element.addEventListener(EVENT_GOTO_TASK, (event) => {
      goto.push((event as CustomEvent<string>).detail);
    });
    (part(element, '.issue .go') as unknown as HTMLButtonElement).click();
    expect(goto).toEqual(['Bad']);

    element.preview = { ...preview, issues: [], tracks: [], persons: {} };
    await element.updateComplete;
    expect(element.shadowRoot?.querySelector('.issue.ok')).not.toBeNull();
    expect(element.shadowRoot?.textContent).toContain('Noch keine Aufgabe gewählt.');
    element.preview = undefined;
    await element.updateComplete;
    expect(element.shadowRoot?.textContent.trim()).toBe('');
  });

  it('Kurztexte für Karten und Abstände', () => {
    expect(describeInterval({ unit: 'day', every: 7 }, 'de')).toBe('alle 7 Tage');
    expect(describeInterval({ unit: 'week', every: 1 }, 'de')).toBe('jede Woche');
    expect(describeInterval({ unit: 'hour', every: 12 }, 'en')).toBe('every 12 hours');
    expect(describeSpan(336, 'de')).toBe('2 Wochen');
    expect(describeSpan(72, 'de')).toBe('3 Tage');
    expect(describeSpan(60, 'de')).toBe('2,5 Tage');
    expect(describeSpan(36, 'de')).toBe('36 Stunden');
    expect(describeSpan(5, 'en')).toBe('5 hours');
    expect(describeSpan(1, 'en')).toBe('1 hour');
  });
});
