import {
  OSCAR_HALF,
  OSCAR_NOMINEE_GAP_CQW,
  OSCAR_NOMINEE_STEP_CQW,
  OSCAR_WINDOW_CQW,
} from '../constants/index.ts';

/** Wie viele Nominierte nebeneinander ganz ins Fenster zwischen den Vorhängen passen. */
export const OSCAR_VISIBLE_COUNT = Math.max(
  1,
  Math.floor((OSCAR_WINDOW_CQW + OSCAR_NOMINEE_GAP_CQW) / OSCAR_NOMINEE_STEP_CQW),
);

/**
 * Index (auch halbe Werte), der in der Fenstermitte steht. Passen alle hinein, bleibt die Gruppe zentriert;
 * sonst steht die hervorgehobene Person (`lit`, -1 = keine) mittig, begrenzt, damit am Rand kein Leerraum entsteht.
 */
export function oscarCenterIndex(count: number, lit: number): number {
  const middle = (count - 1) * OSCAR_HALF;
  if (count <= OSCAR_VISIBLE_COUNT) {
    return middle;
  }
  const reach = (OSCAR_VISIBLE_COUNT - 1) * OSCAR_HALF;
  return Math.min(Math.max(lit, reach), count - 1 - reach);
}
