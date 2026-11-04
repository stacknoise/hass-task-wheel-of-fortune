import { COLLATION_OPTIONS } from '../constants/index.ts';

const collators = new Map<string, Intl.Collator>();

/** Sprachabhängiger Vergleich für Namen: ohne Groß-/Kleinschreibung, Zahlen nach ihrem Wert. */
export function compareText(language: string): (a: string, b: string) => number {
  let collator = collators.get(language);
  if (collator === undefined) {
    collator = new Intl.Collator(language, COLLATION_OPTIONS);
    collators.set(language, collator);
  }
  return collator.compare;
}
