import { FALLBACK_COLOR } from '../constants/index.ts';

const HEX_COLOR = /^#[0-9a-f]{6}$/i;

/**
 * Lässt nur Farben der Form `#rrggbb` durch, alles andere ergibt die Ersatzfarbe. Das Backend
 * prüft das ebenfalls; der Client verlässt sich nicht darauf, weil Farben in Stilangaben landen.
 */
export function safeColor(value: unknown): string {
  return typeof value === 'string' && HEX_COLOR.test(value) ? value : FALLBACK_COLOR;
}
