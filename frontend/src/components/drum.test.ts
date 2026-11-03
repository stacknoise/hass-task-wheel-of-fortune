import { afterEach, describe, expect, it, vi } from 'vitest';

import { EVENT_WHEEL_STOP, STAGE_TAGS } from '../constants/index.ts';
import { DRUM_TOTAL_MS } from './drum-geometry.ts';
import './drum.ts';
import type { TwDrum } from './drum.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.38 },
  { id: 'c', label: 'Clara', color: '#137333', chance: 0.02 },
  { id: 'z', label: 'Zero', color: '#000000', chance: 0 },
];

function reducedMotion(reduced: boolean): void {
  vi.stubGlobal('matchMedia', () => ({ matches: reduced }));
}

function seeded(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

async function mount(segments = SEGMENTS): Promise<TwDrum> {
  const drum = document.createElement(STAGE_TAGS.drum) as TwDrum;
  drum.random = seeded(42);
  drum.segments = segments;
  document.body.append(drum);
  await drum.updateComplete;
  return drum;
}

const svgOf = (drum: TwDrum): Element | null | undefined => drum.shadowRoot?.querySelector('svg');
const balls = (drum: TwDrum): Element[] => [...(drum.shadowRoot?.querySelectorAll('.ball') ?? [])];

async function runAnimation(drum: TwDrum, id: string): Promise<void> {
  const spin = drum.spinTo(id);
  await vi.advanceTimersByTimeAsync(DRUM_TOTAL_MS + 500);
  await spin;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-drum', () => {
  it('zeigt drei Kugeln je Person und die Chancen als Prozent', async () => {
    const drum = await mount();
    expect(balls(drum)).toHaveLength(9);
    const legend = [...(drum.shadowRoot?.querySelectorAll('.legend') ?? [])].map(
      (node) => node.textContent,
    );
    expect(legend).toEqual(['Anna 60 %', 'Ben 38 %', 'Clara 2 %']);
    expect(svgOf(drum)?.getAttribute('role')).toBe('img');
    expect(svgOf(drum)?.getAttribute('aria-label')).toBe('');
    drum.label = 'Lostrommel';
    await drum.updateComplete;
    expect(svgOf(drum)?.getAttribute('aria-label')).toBe('Lostrommel');
    expect(drum.landedId).toBeUndefined();
  });

  it('zeigt bei reduzierter Bewegung direkt den Gewinner in der Ablage', async () => {
    reducedMotion(true);
    const drum = await mount();
    const stopped = vi.fn();
    drum.addEventListener(EVENT_WHEEL_STOP, stopped);
    await drum.spinTo('b');
    await drum.updateComplete;
    expect(drum.landedId).toBe('b');
    expect(svgOf(drum)?.getAttribute('data-landed')).toBe('b');
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('spielt die Animation und endet mit dem vorgegebenen Gewinner', async () => {
    reducedMotion(false);
    const drum = await mount();
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    const stopped = vi.fn();
    drum.addEventListener(EVENT_WHEEL_STOP, stopped);
    const spin = drum.spinTo('c');
    await vi.advanceTimersByTimeAsync(1000);
    expect(stopped).not.toHaveBeenCalled();
    expect(drum.landedId).toBeUndefined();
    await vi.advanceTimersByTimeAsync(DRUM_TOTAL_MS);
    await spin;
    await drum.updateComplete;
    expect(stopped).toHaveBeenCalledOnce();
    expect(drum.landedId).toBe('c');
    expect(svgOf(drum)?.getAttribute('data-landed')).toBe('c');
  });

  it.each(['a', 'b', 'c'])('landet bei jedem Zufall beim Gewinner %s', async (id) => {
    reducedMotion(false);
    const drum = await mount();
    drum.random = Math.random;
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    await runAnimation(drum, id);
    expect(drum.landedId).toBe(id);
  });

  it('kann nacheinander mit verschiedenen Gewinnern laufen', async () => {
    reducedMotion(false);
    const drum = await mount();
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    await runAnimation(drum, 'a');
    await runAnimation(drum, 'b');
    expect(drum.landedId).toBe('b');
    const out = balls(drum).filter((ball) => ball.getAttribute('data-out') === 'true');
    expect(out).toHaveLength(1);
  });

  it('bricht bei neuen Segmenten ab und ändert danach nichts mehr', async () => {
    reducedMotion(false);
    const drum = await mount();
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    const stopped = vi.fn();
    drum.addEventListener(EVENT_WHEEL_STOP, stopped);
    void drum.spinTo('a');
    await vi.advanceTimersByTimeAsync(1000);
    drum.segments = [SEGMENTS[0] ?? { id: 'a', label: '', color: '', chance: 1 }];
    await drum.updateComplete;
    const before = drum.shadowRoot?.innerHTML;
    await vi.advanceTimersByTimeAsync(DRUM_TOTAL_MS * 2);
    expect(drum.shadowRoot?.innerHTML).toBe(before);
    expect(stopped).not.toHaveBeenCalled();
    expect(balls(drum)).toHaveLength(3);
  });

  it('ignoriert unbekannte Gewinner und Segmente ohne Chance', async () => {
    reducedMotion(true);
    const drum = await mount();
    await drum.spinTo('unbekannt');
    await drum.spinTo('z');
    expect(drum.landedId).toBeUndefined();
  });

  it('funktioniert mit einem Segment und ohne Segmente', async () => {
    reducedMotion(true);
    const single = await mount([{ id: 'a', label: 'Anna', color: '#c05600', chance: 1 }]);
    await single.spinTo('a');
    expect(single.landedId).toBe('a');
    const empty = await mount([]);
    expect(balls(empty)).toHaveLength(0);
    await empty.spinTo('a');
    expect(empty.landedId).toBeUndefined();
  });

  it('verwendet Math.random, wenn nichts ersetzt wurde', () => {
    const drum = document.createElement(STAGE_TAGS.drum) as TwDrum;
    expect(drum.random).toBe(Math.random);
  });
});
