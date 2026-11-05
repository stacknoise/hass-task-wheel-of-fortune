import { afterEach, describe, expect, it, vi } from 'vitest';

import { COMPONENT_TAGS, EVENT_WHEEL_STOP, SPIN_DURATION_MS } from '../constants/index.ts';
import './wheel.ts';
import type { TwWheel } from './wheel.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.38 },
  { id: 'c', label: 'Clara', color: '#137333', chance: 0.02 },
];

function reducedMotion(reduced: boolean): void {
  vi.stubGlobal('matchMedia', () => ({ matches: reduced }));
}

async function mount(segments = SEGMENTS): Promise<TwWheel> {
  const wheel = document.createElement(COMPONENT_TAGS.wheel) as TwWheel;
  wheel.segments = segments;
  document.body.append(wheel);
  await wheel.updateComplete;
  return wheel;
}

const rotation = (wheel: TwWheel): string =>
  wheel.shadowRoot?.querySelector<SVGGElement>('.rotor')?.style.transform ?? '';

describe('tw-wheel Beschriftung', () => {
  it('zeigt nur Namen, keine Prozentzahlen', async () => {
    const wheel = await mount();
    expect(wheel.shadowRoot?.querySelector('svg')?.textContent).not.toContain('%');
    expect(wheel.shadowRoot?.querySelector('.chance')).toBeNull();
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-wheel', () => {
  it('zeichnet je Segment ein Stück; zu kleine bleiben unbeschriftet', async () => {
    const wheel = await mount();
    expect(wheel.shadowRoot?.querySelectorAll('path.wedge')).toHaveLength(3);
    const names = [...(wheel.shadowRoot?.querySelectorAll('text.name') ?? [])].map(
      (node) => node.textContent,
    );
    expect(names).toEqual(['Anna', 'Ben']);
  });

  it('zeigt ohne Segmente ein leeres Rad und mit einem einzigen einen Vollkreis', async () => {
    const empty = await mount([]);
    expect(empty.shadowRoot?.querySelector('.empty')).not.toBeNull();
    expect(empty.shadowRoot?.querySelector('.rotor')).toBeNull();
    const single = await mount([{ id: 'a', label: 'Anna', color: '#c05600', chance: 1 }]);
    expect(single.shadowRoot?.querySelector('circle.wedge')).not.toBeNull();
  });

  it('springt bei reduzierter Bewegung ohne Übergang zum Gewinner', async () => {
    reducedMotion(true);
    const wheel = await mount();
    const stopped = vi.fn();
    wheel.addEventListener(EVENT_WHEEL_STOP, stopped);
    await wheel.spinTo('b');
    await wheel.updateComplete;
    expect(rotation(wheel)).toMatch(/^rotate\(/u);
    expect(wheel.shadowRoot?.querySelector<SVGGElement>('.rotor')?.style.transition).toBe('none');
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('animiert mit Übergang und meldet das Ende nach der Dauer', async () => {
    reducedMotion(false);
    const wheel = await mount();
    vi.useFakeTimers();
    const stopped = vi.fn();
    wheel.addEventListener(EVENT_WHEEL_STOP, stopped);
    const spin = wheel.spinTo('a');
    await vi.advanceTimersByTimeAsync(0);
    expect(stopped).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(SPIN_DURATION_MS + 1000);
    await spin;
    expect(stopped).toHaveBeenCalledOnce();
    expect(wheel.shadowRoot?.querySelector<SVGGElement>('.rotor')?.style.transition).toContain(
      `${String(SPIN_DURATION_MS)}ms`,
    );
  });

  it('endet früher, wenn der Übergang gemeldet wird', async () => {
    reducedMotion(false);
    const wheel = await mount();
    const spin = wheel.spinTo('a');
    await vi.waitFor(() => {
      expect(rotation(wheel)).not.toBe('rotate(0deg)');
    });
    wheel.shadowRoot?.querySelector('.rotor')?.dispatchEvent(new Event('transitionend'));
    await spin;
  });

  it('ignoriert unbekannte Segmente und setzt die Drehung bei neuen Segmenten zurück', async () => {
    reducedMotion(true);
    const wheel = await mount();
    await wheel.spinTo('unbekannt');
    expect(rotation(wheel)).toBe('rotate(0deg)');
    await wheel.spinTo('a');
    await wheel.updateComplete;
    wheel.segments = [...SEGMENTS];
    await wheel.updateComplete;
    expect(rotation(wheel)).toBe('rotate(0deg)');
  });
});
