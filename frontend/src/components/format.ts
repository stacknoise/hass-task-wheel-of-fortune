import { EMPTY_TEXT } from '../constants/index.ts';

/** Eine Zahl als Text für Attribute und Pfade. */
export function numberText(value: number): string {
  return String(value);
}

const segmenter = new Intl.Segmenter();

/** Erstes sichtbares Zeichen eines Namens in Großschreibung; Emoji und Zeichenfolgen bleiben ganz. */
export function initialOf(name: string): string {
  const first = segmenter.segment(name.trim())[Symbol.iterator]().next();
  return first.done ? EMPTY_TEXT : first.value.segment.toLocaleUpperCase();
}
