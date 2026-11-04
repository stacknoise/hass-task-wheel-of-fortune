import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  EVENT_WHEEL_STOP,
  OSCAR_CARD_MS,
  OSCAR_CURTAIN_MS,
  OSCAR_ENVELOPE_MS,
  OSCAR_FLAP_MS,
  OSCAR_HOLD_MS,
  OSCAR_NOMINEE_TOTAL_MS,
  OSCAR_PAUSE_MS,
  STAGE_TAGS,
} from '../constants/index.ts';
import './oscar.ts';
import type { TwOscar } from './oscar.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '', chance: 0.4 },
];
const TOTAL_MS =
  OSCAR_CURTAIN_MS +
  OSCAR_NOMINEE_TOTAL_MS +
  OSCAR_ENVELOPE_MS +
  OSCAR_FLAP_MS +
  OSCAR_CARD_MS +
  OSCAR_PAUSE_MS +
  OSCAR_HOLD_MS;

async function mount(language = 'de'): Promise<TwOscar> {
  const element = document.createElement(STAGE_TAGS.oscar) as TwOscar;
  element.segments = SEGMENTS;
  element.taskName = 'Bad putzen';
  element.language = language;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

const award = (element: TwOscar): string =>
  element.shadowRoot?.querySelector('.award')?.textContent.replace(/\s+/g, ' ').trim() ?? '';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-oscar', () => {
  it('beginnt mit geschlossenem Vorhang und zeigt die Nominierten', async () => {
    const element = await mount();
    expect(element.phase).toBe('closed');
    expect(element.shadowRoot?.querySelectorAll('.nominee')).toHaveLength(2);
    expect(element.shadowRoot?.querySelector('.award')).toBeNull();
  });

  it('zeigt bei reduzierter Bewegung sofort die Verkündung', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const element = await mount();
    const stopped = vi.fn();
    element.addEventListener(EVENT_WHEEL_STOP, stopped);
    await element.spinTo('b');
    await element.updateComplete;
    expect(element.phase).toBe('win');
    expect(award(element)).toBe('„Bad putzen“ geht an Ben');
    expect(element.shadowRoot?.querySelector('tw-confetti')).toBeNull();
    expect(element.shadowRoot?.querySelectorAll('.lose')).toHaveLength(1);
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('durchläuft Vorhang, Scheinwerfer, Umschlag und Verkündung', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    const element = await mount('en');
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    const spin = element.spinTo('a');
    await vi.advanceTimersByTimeAsync(OSCAR_CURTAIN_MS + 1);
    await element.updateComplete;
    expect(element.phase).toBe('nominees');
    expect(element.shadowRoot?.querySelectorAll('.lit')).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(OSCAR_NOMINEE_TOTAL_MS);
    await element.updateComplete;
    expect(element.phase).toBe('envelope');
    expect(element.shadowRoot?.querySelector('.card')?.textContent).toBe('And the task goes to …');
    await vi.advanceTimersByTimeAsync(TOTAL_MS);
    await spin;
    await element.updateComplete;
    expect(element.phase).toBe('win');
    expect(award(element)).toBe('“Bad putzen” goes to Anna');
    expect(element.shadowRoot?.querySelector('tw-confetti')).not.toBeNull();
  });

  it('setzt sich bei neuen Segmenten zurück', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const element = await mount();
    await element.spinTo('a');
    element.segments = [...SEGMENTS];
    await element.updateComplete;
    expect(element.phase).toBe('closed');
  });
});
