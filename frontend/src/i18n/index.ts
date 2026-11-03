import { DEFAULT_LANGUAGE } from '../constants/index.ts';
import { de } from './de.ts';
import { en } from './en.ts';

export type TextKey = keyof typeof de;

const TEXTS: Readonly<Record<string, Readonly<Record<TextKey, string>>>> = { de, en };
const LANGUAGE_SEPARATOR = '-';

/** Basissprache eines Gebietsschemas (`de-AT` ⇒ `de`). */
function baseLanguage(language: string): string {
  return language.split(LANGUAGE_SEPARATOR)[0] ?? language;
}

/** Liefert den Text zu einem Schlüssel in der gewünschten Sprache (Rückfall: Englisch). */
export function translate(key: TextKey, language: string): string {
  const texts = TEXTS[baseLanguage(language)] ?? TEXTS[DEFAULT_LANGUAGE];
  return (texts ?? en)[key];
}
