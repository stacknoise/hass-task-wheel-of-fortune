import { ANIMATION_KINDS, DEFAULT_ANIMATIONS } from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';

/** Ist `value` eine bekannte Animationsart? */
export function isAnimationKind(value: unknown): value is AnimationKind {
  return ANIMATION_KINDS.some((kind) => kind === value);
}

/** Die gültigen Arten aus der Antwort des Backends; ohne gültige gilt der Standard. */
export function animationsOf(value: unknown): readonly AnimationKind[] {
  const kinds = Array.isArray(value) ? value.filter(isAnimationKind) : [];
  return kinds.length > 0 ? kinds : DEFAULT_ANIMATIONS;
}

/**
 * Wählt die Animation einer Auslosung zufällig aus den erlaubten Arten des Zeitplans.
 * Das betrifft nur die Optik: der Gewinner steht im Backend fest.
 */
export function pickAnimation(
  allowed: readonly AnimationKind[],
  random: () => number = Math.random,
): AnimationKind {
  const pool = allowed.length > 0 ? allowed : DEFAULT_ANIMATIONS;
  return pool[Math.floor(random() * pool.length)] ?? DEFAULT_ANIMATIONS[0] ?? 'wheel';
}
