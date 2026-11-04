import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  EVENT_WHEEL_STOP,
  NEWS_END_HOLD_MS,
  NEWS_FINAL_IN_MS,
  NEWS_HOLD_MS,
  NEWS_IN_MS,
  NEWS_OUT_MS,
  NEWS_STAMP_MS,
  STAGE_TAGS,
} from '../constants/index.ts';
import './news.ts';
import type { TwNews } from './news.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.5 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.3 },
  { id: 'c', label: 'Clara', color: '', chance: 0.2 },
];
const TOTAL_MS =
  2 * (NEWS_IN_MS + NEWS_HOLD_MS + NEWS_OUT_MS) +
  NEWS_FINAL_IN_MS +
  NEWS_STAMP_MS +
  NEWS_END_HOLD_MS;

async function mount(language = 'de'): Promise<TwNews> {
  const element = document.createElement(STAGE_TAGS.news) as TwNews;
  element.segments = SEGMENTS;
  element.taskName = 'Bad putzen';
  element.language = language;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

const text = (element: TwNews, selector: string): string =>
  element.shadowRoot?.querySelector(selector)?.textContent.trim() ?? '';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-news', () => {
  it('zeigt vor dem Start die Titelseite ohne Meldung', async () => {
    const element = await mount();
    expect(text(element, '.mast')).toBe('HAUS-KURIER');
    expect(text(element, '.head')).toBe('Gleich wird gedruckt …');
    expect(element.stamped).toBe(false);
  });

  it('zeigt bei reduzierter Bewegung sofort die Meldung mit Stempel', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const element = await mount();
    const stopped = vi.fn();
    element.addEventListener(EVENT_WHEEL_STOP, stopped);
    await element.spinTo('b');
    await element.updateComplete;
    expect(text(element, '.head')).toBe('EXTRA: Ben übernimmt Bad putzen!');
    expect(text(element, '.sub')).toBe('Chance war 30 % – es ist amtlich');
    expect(element.stamped).toBe(true);
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('zeigt erst Gerüchte über andere und endet mit dem Gewinner', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    const element = await mount('en');
    element.random = () => 0;
    vi.useFakeTimers({
      toFake: ['setTimeout', 'clearTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'],
    });
    const spin = element.spinTo('c');
    await vi.advanceTimersByTimeAsync(NEWS_IN_MS);
    await element.updateComplete;
    expect(text(element, '.head')).toBe('Rumour: Anna gets off the hook?');
    expect(element.stamped).toBe(false);
    await vi.advanceTimersByTimeAsync(TOTAL_MS);
    await spin;
    await element.updateComplete;
    expect(text(element, '.head')).toBe('EXTRA: Clara takes Bad putzen!');
    expect(element.stamped).toBe(true);
  });

  it('bricht bei neuen Segmenten ab', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    const element = await mount();
    vi.useFakeTimers({
      toFake: ['setTimeout', 'clearTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'],
    });
    const stopped = vi.fn();
    element.addEventListener(EVENT_WHEEL_STOP, stopped);
    void element.spinTo('a');
    await vi.advanceTimersByTimeAsync(NEWS_IN_MS);
    element.segments = SEGMENTS.slice(0, 2);
    await element.updateComplete;
    await vi.advanceTimersByTimeAsync(TOTAL_MS);
    expect(stopped).not.toHaveBeenCalled();
    expect(text(element, '.head')).toBe('Gleich wird gedruckt …');
  });
});
