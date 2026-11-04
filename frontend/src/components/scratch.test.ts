import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  EVENT_STAGE_START,
  EVENT_WHEEL_STOP,
  SCRATCH_COIN_MS,
  SCRATCH_COIN_START_MS,
  SCRATCH_HOLD_MS,
  STAGE_TAGS,
} from '../constants/index.ts';
import './scratch.ts';
import type { TwScratch } from './scratch.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '', chance: 0.4 },
];
const COIN_TOTAL_MS = SCRATCH_COIN_START_MS + SCRATCH_COIN_MS + SCRATCH_HOLD_MS;

/** Jedes Bildpunkt-Alpha liefert `alpha`; so lässt sich „frei gerubbelt“ vorgeben. */
let alpha = 255;
const strokes = vi.fn();

function fakeContext(): unknown {
  return {
    createLinearGradient: () => ({ addColorStop: vi.fn() }),
    fillRect: vi.fn(),
    fillText: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: strokes,
    getImageData: () => ({ data: new Uint8ClampedArray(4 * 37 * 20).fill(alpha) }),
  };
}

async function mount(language = 'de'): Promise<TwScratch> {
  const element = document.createElement(STAGE_TAGS.scratch) as TwScratch;
  element.segments = SEGMENTS;
  element.language = language;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

const canvases = (element: TwScratch): HTMLCanvasElement[] => [
  ...(element.shadowRoot?.querySelectorAll('canvas') ?? []),
];

function pointer(type: string, init: PointerEventInit = {}): PointerEvent {
  const event = new MouseEvent(type, { clientX: 10, clientY: 10, bubbles: true, ...init });
  return Object.assign(event, { pointerId: 1 }) as unknown as PointerEvent;
}

function scratch(canvas: HTMLCanvasElement): void {
  canvas.setPointerCapture = vi.fn();
  canvas.dispatchEvent(pointer('pointerdown'));
  canvas.dispatchEvent(pointer('pointermove', { clientX: 40, clientY: 30 }));
  canvas.dispatchEvent(pointer('pointerup'));
}

beforeEach(() => {
  alpha = 255;
  strokes.mockClear();
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
    () => fakeContext() as CanvasRenderingContext2D,
  );
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
  document.body.replaceChildren();
});

describe('tw-scratch', () => {
  it('zeigt je Person ein verdecktes Los mit Hinweis', async () => {
    const element = await mount();
    expect(canvases(element)).toHaveLength(2);
    expect(element.shadowRoot?.querySelector('.hint')?.textContent).toContain('rubbeln');
    expect(element.shadowRoot?.querySelector('.win')).toBeNull();
    expect(element.openedIds.size).toBe(0);
  });

  it('deckt bei reduzierter Bewegung nur das Gewinnerlos auf', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const element = await mount('en');
    const stopped = vi.fn();
    element.addEventListener(EVENT_WHEEL_STOP, stopped);
    await element.spinTo('b');
    await element.updateComplete;
    expect(element.shadowRoot?.querySelector('.win')?.getAttribute('data-id')).toBe('b');
    expect(element.shadowRoot?.querySelector('.win b')?.textContent).toBe('Winner!');
    expect(element.shadowRoot?.querySelector('.lose')).toBeNull();
    expect(stopped).toHaveBeenCalledOnce();
  });

  it('rubbelt automatisch mit der Münze direkt das Gewinnerlos frei', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    const element = await mount();
    vi.useFakeTimers({ toFake: ['setTimeout', 'requestAnimationFrame', 'cancelAnimationFrame'] });
    const spin = element.spinTo('a');
    await vi.advanceTimersByTimeAsync(COIN_TOTAL_MS + SCRATCH_COIN_MS);
    await spin;
    await element.updateComplete;
    expect(strokes).toHaveBeenCalled();
    expect([...element.openedIds]).toEqual(['a']);
    expect(element.shadowRoot?.querySelector('.win')?.getAttribute('data-id')).toBe('a');
  });

  it('startet beim ersten Rubbeln die Auslosung und endet, wenn das Gewinnerlos frei ist', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false }));
    const element = await mount();
    const started = vi.fn();
    element.addEventListener(EVENT_STAGE_START, started);
    const [first, second] = canvases(element) as [HTMLCanvasElement, HTMLCanvasElement];
    scratch(first);
    scratch(first);
    expect(started).toHaveBeenCalledOnce();
    expect(element.openedIds.size).toBe(0);
    let done = false;
    const spin = element.spinTo('b').then(() => {
      done = true;
    });
    await vi.waitFor(() => {
      expect(element.shadowRoot?.querySelector('canvas')).not.toBeNull();
    });
    expect(done).toBe(false);
    alpha = 0;
    scratch(second);
    await spin;
    await element.updateComplete;
    expect(done).toBe(true);
    expect(element.shadowRoot?.querySelector('.win')?.getAttribute('data-id')).toBe('b');
  });

  it('zeigt ein schon frei gerubbeltes Los erst nach der Ziehung als Niete', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const element = await mount();
    alpha = 0;
    scratch(canvases(element)[0] as HTMLCanvasElement);
    await element.updateComplete;
    expect(element.openedIds.has('a')).toBe(true);
    expect(element.shadowRoot?.querySelector('.lose')).toBeNull();
    await element.spinTo('b');
    await element.updateComplete;
    expect(element.shadowRoot?.querySelector('.lose')?.getAttribute('data-id')).toBe('a');
    expect(element.shadowRoot?.querySelector('.win')?.getAttribute('data-id')).toBe('b');
  });

  it('lässt ein nur wenig gerubbeltes Los zu', async () => {
    const element = await mount();
    scratch(canvases(element)[0] as HTMLCanvasElement);
    expect(element.openedIds.size).toBe(0);
  });

  it('setzt sich bei neuer Aufgabe zurück', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const element = await mount();
    await element.spinTo('a');
    element.taskName = 'Müll rausbringen';
    await element.updateComplete;
    expect(element.openedIds.size).toBe(0);
    expect(element.shadowRoot?.querySelector('.win')).toBeNull();
  });
});
