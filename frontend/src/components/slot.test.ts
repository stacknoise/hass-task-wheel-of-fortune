import { afterEach, describe, expect, it, vi } from 'vitest';

import { EVENT_WHEEL_STOP, SLOT_RECOIL_MS, SLOT_SPIN_MS, STAGE_TAGS } from '../constants/index.ts';
import './slot.ts';
import type { TwSlot } from './slot.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.38 },
  { id: 'c', label: 'Clara', color: '#137333', chance: 0.02 },
  { id: 'z', label: 'Null', color: '#000000', chance: 0 },
];

function reducedMotion(reduced: boolean): void {
  vi.stubGlobal('matchMedia', () => ({ matches: reduced }));
}

async function mount(segments = SEGMENTS, random = (): number => 0.5): Promise<TwSlot> {
  const slot = document.createElement(STAGE_TAGS.slot) as TwSlot;
  slot.random = random;
  slot.label = 'Walze';
  slot.segments = segments;
  document.body.append(slot);
  await slot.updateComplete;
  return slot;
}

const winners = (slot: TwSlot): number => slot.shadowRoot?.querySelectorAll('.win').length ?? 0;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-slot', () => {
  it('zeigt je Person Name und Prozent, kleine Zeilen ohne Text, und beschriftet die Grafik', async () => {
    const slot = await mount();
    expect(slot.shadowRoot?.querySelector('svg')?.getAttribute('role')).toBe('img');
    expect(slot.shadowRoot?.querySelector('svg')?.getAttribute('aria-label')).toBe('Walze');
    const names = [...(slot.shadowRoot?.querySelectorAll('text.name') ?? [])].map(
      (n) => n.textContent,
    );
    expect(new Set(names)).toEqual(new Set(['Anna', 'Ben']));
    const chances = [...(slot.shadowRoot?.querySelectorAll('text.chance') ?? [])].map(
      (n) => n.textContent,
    );
    expect(new Set(chances)).toEqual(new Set(['60%', '38%']));
    expect(slot.shadowRoot?.querySelectorAll('rect.cell').length).toBe(3 * 11);
  });

  it('springt bei reduzierter Bewegung direkt zum Gewinner', async () => {
    reducedMotion(true);
    const slot = await mount();
    const stopped = vi.fn();
    slot.addEventListener(EVENT_WHEEL_STOP, stopped);
    await slot.spinTo('b');
    await slot.updateComplete;
    expect(slot.landedId).toBe('b');
    expect(winners(slot)).toBe(1);
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('landet nach der Animation beim Gewinner, egal wo im Segment', async () => {
    reducedMotion(false);
    for (const random of [0, 0.5, 0.999]) {
      for (const id of ['a', 'b', 'c']) {
        const slot = await mount(SEGMENTS, () => random);
        vi.useFakeTimers({
          toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'setTimeout', 'performance'],
        });
        const spin = slot.spinTo(id);
        await vi.advanceTimersByTimeAsync(SLOT_RECOIL_MS + SLOT_SPIN_MS + 1000);
        await spin;
        await slot.updateComplete;
        expect(slot.landedId).toBe(id);
        expect(winners(slot)).toBe(1);
        vi.useRealTimers();
      }
    }
  });

  it('läuft mehrfach hintereinander', async () => {
    reducedMotion(false);
    const slot = await mount();
    vi.useFakeTimers({
      toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'setTimeout', 'performance'],
    });
    for (const id of ['a', 'a', 'c']) {
      const spin = slot.spinTo(id);
      await vi.advanceTimersByTimeAsync(SLOT_RECOIL_MS + SLOT_SPIN_MS + 1000);
      await spin;
      expect(slot.landedId).toBe(id);
    }
  });

  it('bricht bei neuen Segmenten ab und ändert danach nichts mehr', async () => {
    reducedMotion(false);
    const slot = await mount();
    vi.useFakeTimers({
      toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'setTimeout', 'performance'],
    });
    const stopped = vi.fn();
    slot.addEventListener(EVENT_WHEEL_STOP, stopped);
    void slot.spinTo('b');
    await vi.advanceTimersByTimeAsync(SLOT_RECOIL_MS + 100);
    slot.segments = [{ id: 'q', label: 'Quentin', color: '#333333', chance: 1 }];
    await slot.updateComplete;
    await vi.advanceTimersByTimeAsync(SLOT_SPIN_MS + 1000);
    expect(stopped).not.toHaveBeenCalled();
    expect(winners(slot)).toBe(0);
    expect(slot.landedId).toBe('q');
  });

  it('ignoriert unbekannte Gewinner und Personen ohne Chance', async () => {
    reducedMotion(true);
    const slot = await mount();
    const stopped = vi.fn();
    slot.addEventListener(EVENT_WHEEL_STOP, stopped);
    await slot.spinTo('nope');
    await slot.spinTo('z');
    expect(stopped).not.toHaveBeenCalled();
    expect(winners(slot)).toBe(0);
  });

  it('kommt mit einer Person und mit keiner zurecht', async () => {
    reducedMotion(true);
    const single = await mount([{ id: 'a', label: 'Anna', color: '', chance: 1 }]);
    await single.spinTo('a');
    expect(single.landedId).toBe('a');
    const empty = await mount([]);
    await empty.spinTo('a');
    expect(empty.landedId).toBeUndefined();
    expect(empty.shadowRoot?.querySelectorAll('rect.cell')).toHaveLength(0);
  });
});
