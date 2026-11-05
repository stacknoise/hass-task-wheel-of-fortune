import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  EVENT_WHEEL_STOP,
  SPOTLIGHT_DELAY_SPAN_MS,
  SPOTLIGHT_HOLD_MS,
  SPOTLIGHT_MIN_DELAY_MS,
  SPOTLIGHT_STEPS,
  STAGE_TAGS,
} from '../constants/index.ts';
import './spotlight.ts';
import type { TwSpotlight } from './spotlight.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.38 },
  { id: 'c', label: 'Clara', color: '', chance: 0.02 },
  { id: 'z', label: 'Zero', color: '#000000', chance: 0 },
];
const TOTAL_MS =
  SPOTLIGHT_STEPS * (SPOTLIGHT_MIN_DELAY_MS + SPOTLIGHT_DELAY_SPAN_MS) + SPOTLIGHT_HOLD_MS;

function reducedMotion(reduced: boolean): void {
  vi.stubGlobal('matchMedia', () => ({ matches: reduced }));
}

async function mount(segments = SEGMENTS): Promise<TwSpotlight> {
  const element = document.createElement(STAGE_TAGS.spotlight) as TwSpotlight;
  element.segments = segments;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

const root = (element: TwSpotlight): Element | null | undefined =>
  element.shadowRoot?.querySelector('.tiles');
const tiles = (element: TwSpotlight): Element[] => [
  ...(element.shadowRoot?.querySelectorAll('.tile') ?? []),
];

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-spotlight', () => {
  it('zeigt je Person eine Kachel ohne Prozent und beschriftet die Grafik', async () => {
    const element = await mount();
    expect(tiles(element)).toHaveLength(3);
    const texts = tiles(element).map((tile) => tile.textContent.replace(/\s+/g, ' ').trim());
    expect(texts).toEqual(['Anna', 'Ben', 'Clara']);
    expect(root(element)?.getAttribute('role')).toBe('img');
    expect(root(element)?.getAttribute('aria-label')).toBe('');
    element.label = 'Scheinwerfer';
    await element.updateComplete;
    expect(root(element)?.getAttribute('aria-label')).toBe('Scheinwerfer');
    expect(element.landedId).toBeUndefined();
    expect(element.shadowRoot?.querySelector('.final')).toBeNull();
  });

  it('zeigt bei reduzierter Bewegung direkt den Gewinner', async () => {
    reducedMotion(true);
    const element = await mount();
    const stopped = vi.fn();
    element.addEventListener(EVENT_WHEEL_STOP, stopped);
    await element.spinTo('b');
    await element.updateComplete;
    expect(element.landedId).toBe('b');
    expect(root(element)?.getAttribute('data-landed')).toBe('b');
    expect(root(element)?.classList.contains('still')).toBe(true);
    expect(element.shadowRoot?.querySelector('.final')?.getAttribute('data-id')).toBe('b');
    expect(element.shadowRoot?.querySelectorAll('.lose')).toHaveLength(2);
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('springt über die Kacheln und bleibt beim vorgegebenen Gewinner stehen', async () => {
    reducedMotion(false);
    const element = await mount();
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    const stopped = vi.fn();
    element.addEventListener(EVENT_WHEEL_STOP, stopped);
    const spin = element.spinTo('c');
    await vi.advanceTimersByTimeAsync(SPOTLIGHT_MIN_DELAY_MS * 3);
    await element.updateComplete;
    expect(element.shadowRoot?.querySelectorAll('.on')).toHaveLength(1);
    expect(element.landedId).toBeUndefined();
    expect(stopped).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(TOTAL_MS);
    await spin;
    await element.updateComplete;
    expect(element.landedId).toBe('c');
    expect(element.shadowRoot?.querySelector('.final')?.getAttribute('data-id')).toBe('c');
    expect(stopped).toHaveBeenCalledOnce();
  });

  it.each(['a', 'b', 'c'])('landet bei jedem Zufall beim Gewinner %s', async (id) => {
    reducedMotion(false);
    const element = await mount();
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    const spin = element.spinTo(id);
    await vi.advanceTimersByTimeAsync(TOTAL_MS);
    await spin;
    expect(element.landedId).toBe(id);
  });

  it('startet eine zweite Auslosung mit frischem Zustand', async () => {
    reducedMotion(false);
    const element = await mount();
    element.random = () => 0;
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    for (const id of ['a', 'b']) {
      const spin = element.spinTo(id);
      await vi.advanceTimersByTimeAsync(TOTAL_MS);
      await spin;
      expect(element.landedId).toBe(id);
    }
  });

  it('bricht bei neuen Segmenten ab und ändert danach nichts mehr', async () => {
    reducedMotion(false);
    const element = await mount();
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    const stopped = vi.fn();
    element.addEventListener(EVENT_WHEEL_STOP, stopped);
    void element.spinTo('a');
    await vi.advanceTimersByTimeAsync(SPOTLIGHT_MIN_DELAY_MS * 4);
    element.segments = [{ id: 'a', label: 'Anna', color: '#c05600', chance: 1 }];
    await element.updateComplete;
    const before = element.shadowRoot?.innerHTML;
    await vi.advanceTimersByTimeAsync(TOTAL_MS * 2);
    expect(element.shadowRoot?.innerHTML).toBe(before);
    expect(stopped).not.toHaveBeenCalled();
    expect(element.landedId).toBeUndefined();
    expect(tiles(element)).toHaveLength(1);
  });

  it('ignoriert unbekannte Gewinner und Segmente ohne Chance', async () => {
    reducedMotion(true);
    const element = await mount();
    await element.spinTo('unbekannt');
    await element.spinTo('z');
    expect(element.landedId).toBeUndefined();
  });

  it('funktioniert mit einem Segment und ohne Segmente', async () => {
    reducedMotion(true);
    const single = await mount([{ id: 'a', label: 'Anna', color: '#c05600', chance: 1 }]);
    await single.spinTo('a');
    expect(single.landedId).toBe('a');
    expect(tiles(single)).toHaveLength(1);
    const empty = await mount([]);
    expect(tiles(empty)).toHaveLength(0);
    await empty.spinTo('a');
    expect(empty.landedId).toBeUndefined();
  });

  it('verwendet Math.random, wenn nichts ersetzt wurde', () => {
    const element = document.createElement(STAGE_TAGS.spotlight) as TwSpotlight;
    expect(element.random).toBe(Math.random);
  });
});
