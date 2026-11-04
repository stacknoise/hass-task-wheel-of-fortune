import { describe, expect, it } from 'vitest';

import { EVENT_CHANGE, FORM_TAGS } from '../constants/index.ts';
import type { FrequencyWire, TriggerWire } from '../state/index.ts';
import { describeFrequency, describeTrigger } from './summaries.ts';
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

  it('Wochenvorschau und Zeitstrahl zeigen ihre Werte', async () => {
    const preview = await mount(FORM_TAGS.weekPreview, { language: 'de', present: [true, false] });
    expect(preview.shadowRoot?.querySelectorAll('.day.absent')).toHaveLength(1);
    expect(preview.shadowRoot?.textContent).toContain('Mo');
    const line = await mount(FORM_TAGS.timeline, { language: 'de', days: 7, tolerance: 2 });
    expect(line.shadowRoot?.textContent).toContain('frühestens: 5');
    expect(line.shadowRoot?.textContent).toContain('spätestens: 9');
    expect(line.shadowRoot?.textContent).toContain('Ziel: 7');
    const scale = (element: Element): string[] =>
      [...(element.shadowRoot?.querySelectorAll('.days span') ?? [])].map((day) => day.textContent);
    expect(scale(line)).toEqual(['1', '2', '4', '6', '8', '9']);
    const long = await mount(FORM_TAGS.timeline, { language: 'de', days: 365, tolerance: 30 });
    expect(scale(long)).toEqual(['1', '50', '100', '150', '200', '250', '300', '350', '395']);
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

  it('Häufigkeit: Art wechseln und Werte ändern', async () => {
    const editor = await mount(FORM_TAGS.frequencyEditor, {
      language: 'de',
      value: { kind: 'every_round' } satisfies FrequencyWire,
    });
    const seen = changes(editor);
    say(part(editor, 'tw-select'), 'max_per_period');
    expect(seen.at(-1)).toEqual({ kind: 'max_per_period', count: 1, period: 'week', every: 1 });

    editor.value = seen.at(-1);
    await editor.updateComplete;
    say(part(editor, 'tw-stepper'), 3);
    say(part(editor, 'tw-segmented'), 'month');
    expect(seen.slice(-2)).toEqual([
      { kind: 'max_per_period', count: 3, period: 'week', every: 1 },
      { kind: 'max_per_period', count: 1, period: 'month', every: 1 },
    ]);

    editor.value = { kind: 'interval', days: 7, tolerance: 3 };
    await editor.updateComplete;
    const [days, tolerance] = [
      ...(editor.shadowRoot?.querySelectorAll('tw-stepper') ?? []),
    ] as El[];
    say(days as El, 2);
    say(tolerance as El, 1);
    expect(seen.slice(-2)).toEqual([
      { kind: 'interval', days: 2, tolerance: 1 },
      { kind: 'interval', days: 7, tolerance: 1 },
    ]);
    expect(editor.shadowRoot?.querySelector('tw-timeline')).not.toBeNull();
  });

  it('Auslöser: wiederkehrend, einmalig, manuell', async () => {
    const editor = await mount(FORM_TAGS.triggerEditor, {
      language: 'de',
      now: '2026-11-03T12:00:00+00:00',
      value: {
        kind: 'recurring',
        weekdays: [0],
        time: '18:00:00',
        every_n_weeks: 1,
        monthly: false,
        anchor: null,
      } satisfies TriggerWire,
    });
    const seen = changes(editor);
    say(part(editor, 'tw-chip-select'), ['1', '3']);
    say(part(editor, 'tw-field'), '19:30');
    say(part(editor, 'tw-stepper'), 2);
    say(part(editor, 'tw-toggle'), true);
    expect(seen).toMatchObject([
      { weekdays: [1, 3] },
      { time: '19:30' },
      { every_n_weeks: 2, monthly: false },
      { monthly: true, every_n_weeks: 1 },
    ]);

    editor.value = { ...(editor.value as object), every_n_weeks: 2, anchor: null };
    await editor.updateComplete;
    const fields = [...(editor.shadowRoot?.querySelectorAll('tw-field') ?? [])] as El[];
    say(fields[1] as El, '2026-11-09');
    say(fields[1] as El, '');
    expect(seen.slice(-2)).toMatchObject([{ anchor: '2026-11-09' }, { anchor: null }]);

    say(part(editor, 'tw-select'), 'once');
    expect(seen.at(-1)).toMatchObject({ kind: 'once', at: '2026-11-04T12:00:00.000Z' });
    editor.value = seen.at(-1);
    await editor.updateComplete;
    say(part(editor, 'tw-field'), '2026-11-05T08:00');
    say(part(editor, 'tw-select:nth-of-type(2)'), 'archive');
    expect((seen.at(-2) as { at: string }).at.endsWith('Z')).toBe(true);
    expect(seen.at(-1)).toMatchObject({ after: 'archive' });

    say(part(editor, 'tw-select'), 'manual');
    editor.value = seen.at(-1);
    await editor.updateComplete;
    say(part(editor, 'tw-toggle'), true);
    expect(seen.at(-1)).toMatchObject({ remind_after_days: 7 });
    editor.value = seen.at(-1);
    await editor.updateComplete;
    say(part(editor, 'tw-stepper'), 3);
    say(part(editor, 'tw-toggle'), false);
    expect(seen.slice(-2)).toMatchObject([{ remind_after_days: 3 }, { remind_after_days: null }]);
  });

  it('Kurztexte für Karten', () => {
    expect(describeFrequency({ kind: 'every_round' }, 'de')).toBe('jede Runde');
    expect(
      describeFrequency({ kind: 'max_per_period', count: 2, period: 'week', every: 1 }, 'de'),
    ).toBe('max. 2× je Woche');
    expect(
      describeFrequency({ kind: 'max_per_period', count: 5, period: 'month', every: 2 }, 'de'),
    ).toBe('max. 5× in 2 Monaten');
    expect(describeFrequency({ kind: 'interval', days: 7, tolerance: 1 }, 'en')).toBe(
      'every 7 days ± 1',
    );
    expect(
      describeTrigger(
        {
          kind: 'recurring',
          weekdays: [0, 3],
          time: '18:30:00',
          every_n_weeks: 1,
          monthly: false,
          anchor: null,
        },
        'de',
      ),
    ).toBe('Mo Do um 18:30');
    expect(describeTrigger({ kind: 'manual', remind_after_days: null }, 'de')).toBe('nur manuell');
    expect(
      describeTrigger({ kind: 'once', at: '2026-11-03T12:00:00Z', after: 'archive' }, 'en'),
    ).toContain('once on');
  });
});
