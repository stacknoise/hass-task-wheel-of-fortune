import { describe, expect, it, vi } from 'vitest';

import { EVENT_CHANGE } from '../constants/index.ts';
import { DEADLINE_DEFAULT } from '../state/index.ts';
import type { DeadlineWire } from '../state/index.ts';
import './deadline-editor.ts';
import { describeDeadline } from './summaries.ts';
import type { TwDeadlineEditor } from './deadline-editor.ts';

async function mount(value: DeadlineWire): Promise<TwDeadlineEditor> {
  const editor = document.createElement('tw-deadline-editor') as TwDeadlineEditor;
  editor.language = 'de';
  editor.value = value;
  document.body.append(editor);
  await editor.updateComplete;
  return editor;
}

const say = (root: ParentNode, selector: string, detail: unknown): void => {
  root
    .querySelector(selector)
    ?.dispatchEvent(new CustomEvent(EVENT_CHANGE, { detail, bubbles: true, composed: true }));
};

describe('TwDeadlineEditor', () => {
  it('zeigt Versatz, Wochentag und Uhrzeit nur dort, wo die Art sie braucht', async () => {
    const editor = await mount(DEADLINE_DEFAULT);
    const root = editor.shadowRoot as ShadowRoot;
    expect(root.querySelectorAll('tw-duration-input')).toHaveLength(1);
    expect(root.querySelector('tw-field')).toBeNull();
    editor.value = { ...DEADLINE_DEFAULT, start: 'offset' };
    await editor.updateComplete;
    expect(root.querySelectorAll('tw-duration-input')).toHaveLength(2);
    editor.value = { ...DEADLINE_DEFAULT, start: 'weekday' };
    await editor.updateComplete;
    expect(root.querySelectorAll('tw-select')).toHaveLength(2);
    expect(root.querySelector('tw-field')).not.toBeNull();
  });

  it('meldet die geänderte Frist', async () => {
    const editor = await mount(DEADLINE_DEFAULT);
    const seen = vi.fn();
    editor.addEventListener(EVENT_CHANGE, (event) => {
      seen((event as CustomEvent).detail);
    });
    say(editor.shadowRoot as ShadowRoot, 'tw-select', 'next_day');
    expect(seen).toHaveBeenCalledWith({ ...DEADLINE_DEFAULT, start: 'next_day' });
    say(editor.shadowRoot as ShadowRoot, 'tw-duration-input', { amount: 4, unit: 'hour' });
    expect(seen).toHaveBeenLastCalledWith({
      ...DEADLINE_DEFAULT,
      duration: 4,
      duration_unit: 'hour',
    });
  });

  it('fasst die Frist in einem Satz zusammen', () => {
    expect(describeDeadline(DEADLINE_DEFAULT, 'de')).toBe('Frist: ab Auslosung, 7 Tage');
    expect(
      describeDeadline(
        { ...DEADLINE_DEFAULT, start: 'next_day', duration: 1, duration_unit: 'hour' },
        'en',
      ),
    ).toBe('Deadline: from the next day 10:00, 1 hour');
    expect(describeDeadline({ ...DEADLINE_DEFAULT, start: 'weekday', weekday: 2 }, 'de')).toContain(
      'Mi 10:00',
    );
  });
});
