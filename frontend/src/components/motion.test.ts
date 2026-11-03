import { afterEach, describe, expect, it, vi } from 'vitest';

import { MotionToken, easeInOut, lerp, prefersReducedMotion, randomBetween } from './motion.ts';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('Bewegung', () => {
  it('rechnet Übergänge', () => {
    expect(lerp(10, 20, 0.5)).toBe(15);
    expect(easeInOut(0)).toBe(0);
    expect(easeInOut(0.5)).toBe(0.5);
    expect(easeInOut(1)).toBe(1);
    expect(easeInOut(0.25)).toBeLessThan(0.25);
    expect(easeInOut(0.75)).toBeGreaterThan(0.75);
    expect(randomBetween(2, 4, () => 0.5)).toBe(3);
  });

  it('liest die Einstellung zu reduzierter Bewegung', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    expect(prefersReducedMotion()).toBe(true);
  });

  it('wartet und bricht ab', async () => {
    vi.useFakeTimers();
    const token = new MotionToken();
    const done = vi.fn();
    void token.sleep(100).then(done);
    await vi.advanceTimersByTimeAsync(99);
    expect(done).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(done).toHaveBeenCalledOnce();
    void token.sleep(100).then(done);
    token.cancel();
    await vi.advanceTimersByTimeAsync(500);
    expect(done).toHaveBeenCalledOnce();
    expect(token.dead).toBe(true);
  });

  it('ruft die Bildfolge bis zum Ende auf und hört nach dem Abbruch auf', async () => {
    let now = 0;
    const queue: FrameRequestCallback[] = [];
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) =>
      queue.push(callback),
    );
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
    const token = new MotionToken();
    const steps: number[] = [];
    const finished = token.frames(100, (progress) => steps.push(progress));
    while (queue.length > 0) {
      now += 50;
      queue.shift()?.(now);
    }
    await finished;
    expect(steps.at(-1)).toBe(1);

    const stopped = new MotionToken();
    const calls: number[] = [];
    void stopped.frames(100, (progress) => calls.push(progress));
    stopped.cancel();
    queue.shift()?.(10);
    expect(calls).toEqual([]);
  });
});
