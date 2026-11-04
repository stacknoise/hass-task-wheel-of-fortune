import { ANIMATION_KINDS, DEFAULT_ANIMATIONS } from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';

/** Ist `value` eine bekannte Animationsart? */
export function isAnimationKind(value: unknown): value is AnimationKind {
  return ANIMATION_KINDS.some((kind) => kind === value);
}

/**
 * Die gültigen Arten aus der Antwort des Backends. Eine leere Liste heißt „keine Animation“;
 * fehlt das Feld (älterer Zeitplan), gilt der Standard.
 */
export function animationsOf(value: unknown): readonly AnimationKind[] {
  return Array.isArray(value) ? value.filter(isAnimationKind) : DEFAULT_ANIMATIONS;
}

/**
 * Wählt die Animation einer Auslosung zufällig aus den erlaubten Arten des Zeitplans.
 * Das betrifft nur die Optik: der Gewinner steht im Backend fest.
 */
export function pickAnimation(
  allowed: readonly AnimationKind[],
  random: () => number = Math.random,
): AnimationKind | undefined {
  return allowed[Math.floor(random() * allowed.length)];
}
