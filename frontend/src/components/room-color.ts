import { ROOM_COLORS } from '../constants/index.ts';

/** Stabiler Farbton (0–359°) eines Raums aus seinem Namen; gleicher Name, gleicher Farbton. */
export function roomHue(name: string): number {
  let hash = 0;
  for (const char of name) {
    hash =
      (hash * ROOM_COLORS.hashMultiplier + (char.codePointAt(0) ?? 0)) % ROOM_COLORS.hashModulo;
  }
  const step = ROOM_COLORS.hueDegrees / ROOM_COLORS.hueBuckets;
  return (hash % ROOM_COLORS.hueBuckets) * step;
}
