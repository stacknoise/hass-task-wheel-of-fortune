import { describe, expect, it } from 'vitest';

import { animationsOf, isAnimationKind, pickAnimation } from './animation.ts';

describe('Animationswahl', () => {
  it('erkennt nur bekannte Arten', () => {
    expect(isAnimationKind('drum')).toBe(true);
    expect(isAnimationKind('confetti')).toBe(false);
    expect(isAnimationKind(3)).toBe(false);
  });

  it('übernimmt gültige Arten und fällt sonst auf das Glücksrad zurück', () => {
    expect(animationsOf(['slot', 'x', 'plinko'])).toEqual(['slot', 'plinko']);
    expect(animationsOf([])).toEqual(['wheel']);
    expect(animationsOf(undefined)).toEqual(['wheel']);
  });

  it('wählt gleichverteilt aus den erlaubten Arten', () => {
    const allowed = ['drum', 'slot', 'plinko', 'spotlight'] as const;
    expect(pickAnimation(allowed, () => 0)).toBe('drum');
    expect(pickAnimation(allowed, () => 0.3)).toBe('slot');
    expect(pickAnimation(allowed, () => 0.99)).toBe('spotlight');
    expect(pickAnimation([], () => 0.5)).toBe('wheel');
  });

  it('nimmt die einzige Art ohne Zufall', () => {
    expect(pickAnimation(['plinko'])).toBe('plinko');
  });
});
