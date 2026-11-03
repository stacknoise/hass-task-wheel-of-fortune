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

const ERROR_PREFIX = 'error.';
const UNKNOWN_ERROR: TextKey = 'error.unknown';

/** Text zu einem Fehlerschlüssel des Backends (`out_of_range`); unbekannte Schlüssel ergeben den allgemeinen Text. */
export function translateError(code: string, language: string): string {
  const key = `${ERROR_PREFIX}${code}`;
  return translate(key in de ? (key as TextKey) : UNKNOWN_ERROR, language);
}

/** Setzt Platzhalter wie `{count}` in einem Text ein. */
export function fill(text: string, values: Readonly<Record<string, string | number>>): string {
  return Object.entries(values).reduce(
    (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
    text,
  );
}
