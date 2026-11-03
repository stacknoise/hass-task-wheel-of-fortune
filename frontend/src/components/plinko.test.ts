import { afterEach, describe, expect, it, vi } from 'vitest';

import { EVENT_WHEEL_STOP, STAGE_TAGS } from '../constants/index.ts';
import { MotionToken } from './motion.ts';
import './plinko.ts';
import type { TwPlinko } from './plinko.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.38 },
  { id: 'c', label: 'Clara', color: '#137333', chance: 0.02 },
  { id: 'z', label: 'Null', color: '#000000', chance: 0 },
];
const LONG_RUN_MS = 20_000;

function reducedMotion(reduced: boolean): void {
  vi.stubGlobal('matchMedia', () => ({ matches: reduced }));
}

async function mount(segments = SEGMENTS, random = (): number => 0.5): Promise<TwPlinko> {
  const plinko = document.createElement(STAGE_TAGS.plinko) as TwPlinko;
  plinko.random = random;
  plinko.label = 'Plinko';
  plinko.segments = segments;
  document.body.append(plinko);
  await plinko.updateComplete;
  return plinko;
}

const texts = (plinko: TwPlinko, selector: string): (string | null)[] =>
  [...(plinko.shadowRoot?.querySelectorAll(selector) ?? [])].map((node) => node.textContent);

const winners = (plinko: TwPlinko): number =>
  plinko.shadowRoot?.querySelectorAll('.win').length ?? 0;

function fakeTime(): void {
  vi.useFakeTimers({
    toFake: [
      'requestAnimationFrame',
      'cancelAnimationFrame',
      'setTimeout',
      'clearTimeout',
      'performance',
    ],
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-plinko', () => {
  it('zeigt je Fach Prozent (schmale ohne Namen) und beschriftet die Grafik', async () => {
    const plinko = await mount();
    const svg = plinko.shadowRoot?.querySelector('svg');
    expect(svg?.getAttribute('role')).toBe('img');
    expect(svg?.getAttribute('aria-label')).toBe('Plinko');
    expect(texts(plinko, 'text.name')).toEqual(['Anna', 'Ben']);
    expect(texts(plinko, 'text.chance')).toEqual(['60 %', '38 %']);
    expect(plinko.shadowRoot?.querySelectorAll('rect.bin')).toHaveLength(3);
    expect(plinko.shadowRoot?.querySelectorAll('circle.peg').length).toBeGreaterThan(50);
  });

  it('springt bei reduzierter Bewegung direkt zum Gewinner', async () => {
    reducedMotion(true);
    const plinko = await mount();
    const stopped = vi.fn();
    plinko.addEventListener(EVENT_WHEEL_STOP, stopped);
    await plinko.spinTo('b');
    await plinko.updateComplete;
    expect(plinko.landedId).toBe('b');
    expect(winners(plinko)).toBe(1);
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('landet nach der Animation im Fach des Gewinners, egal welcher Zufall', async () => {
    reducedMotion(false);
    for (const random of [0, 0.5, 0.999]) {
      for (const id of ['a', 'b', 'c']) {
        const plinko = await mount(SEGMENTS, () => random);
        fakeTime();
        const spin = plinko.spinTo(id);
        await vi.advanceTimersByTimeAsync(LONG_RUN_MS);
        await spin;
        await plinko.updateComplete;
        expect(plinko.landedId).toBe(id);
        expect(winners(plinko)).toBe(1);
        vi.useRealTimers();
      }
    }
  });

  it('lässt getroffene Stifte aufleuchten und danach wieder verlöschen', async () => {
    reducedMotion(false);
    const plinko = await mount();
    fakeTime();
    const spin = plinko.spinTo('a');
    let lit = 0;
    for (let step = 0; step < 100; step++) {
      await vi.advanceTimersByTimeAsync(50);
      await plinko.updateComplete;
      lit = Math.max(lit, plinko.shadowRoot?.querySelectorAll('circle.peg.lit').length ?? 0);
    }
    await vi.advanceTimersByTimeAsync(LONG_RUN_MS);
    await spin;
    await plinko.updateComplete;
    expect(lit).toBeGreaterThan(0);
    expect(plinko.shadowRoot?.querySelectorAll('circle.peg.lit')).toHaveLength(0);
  });

  it('bricht bei neuen Segmenten ab und ändert danach nichts mehr', async () => {
    reducedMotion(false);
    const plinko = await mount();
    fakeTime();
    const stopped = vi.fn();
    plinko.addEventListener(EVENT_WHEEL_STOP, stopped);
    void plinko.spinTo('a');
    await vi.advanceTimersByTimeAsync(800);
    plinko.segments = [{ id: 'n', label: 'Neu', color: '#000000', chance: 1 }];
    await plinko.updateComplete;
    const before = plinko.shadowRoot?.innerHTML;
    await vi.advanceTimersByTimeAsync(LONG_RUN_MS);
    await plinko.updateComplete;
    expect(plinko.shadowRoot?.innerHTML).toBe(before);
    expect(stopped).not.toHaveBeenCalled();
    expect(winners(plinko)).toBe(0);
  });

  it('ignoriert eine unbekannte id', async () => {
    reducedMotion(true);
    const plinko = await mount();
    const stopped = vi.fn();
    plinko.addEventListener(EVENT_WHEEL_STOP, stopped);
    await plinko.spinTo('gibt-es-nicht');
    await plinko.spinTo('z');
    expect(stopped).not.toHaveBeenCalled();
    expect(winners(plinko)).toBe(0);
  });

  it('spielt für eine unbekannte id nichts ab', async () => {
    const plinko = await mount();
    const stage = plinko as unknown as { play(id: string, token: MotionToken): Promise<void> };
    await stage.play('gibt-es-nicht', new MotionToken());
    expect(plinko.landedId).toBe('a');
    expect(winners(plinko)).toBe(0);
  });

  it('kommt mit einem Segment und ohne Segmente zurecht', async () => {
    reducedMotion(true);
    const single = await mount([{ id: 'a', label: 'Anna', color: '', chance: 1 }]);
    await single.spinTo('a');
    await single.updateComplete;
    expect(single.landedId).toBe('a');
    expect(texts(single, 'text.chance')).toEqual(['100 %']);
    const empty = await mount([]);
    await empty.spinTo('a');
    expect(empty.landedId).toBeUndefined();
    expect(empty.shadowRoot?.querySelectorAll('rect.bin')).toHaveLength(0);
    expect(empty.shadowRoot?.querySelectorAll('circle.peg').length).toBeGreaterThan(0);
  });
});
