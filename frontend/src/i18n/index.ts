import { DEFAULT_LANGUAGE } from '../constants/index.ts';
import { de } from './de.ts';
import { en } from './en.ts';

export type TextKey = keyof typeof de;

const TEXTS: Readonly<Record<string, Readonly<Record<TextKey, string>>>> = { de, en };
const LANGUAGE_SEPARATOR = '-';
const PLACEHOLDER = /\{(\w+)\}/g;

/** Basissprache eines Gebietsschemas (`de-AT` ⇒ `de`). */
function baseLanguage(language: string): string {
  return language.split(LANGUAGE_SEPARATOR)[0] ?? language;
}

export type TextParams = Readonly<Record<string, string | number>>;

/**
 * Liefert den Text zu einem Schlüssel in der gewünschten Sprache (Rückfall: Englisch);
 * `{name}` im Text wird durch den Wert `name` aus `params` ersetzt.
 */
export function translate(key: TextKey, language: string, params?: TextParams): string {
  const texts = TEXTS[baseLanguage(language)] ?? TEXTS[DEFAULT_LANGUAGE];
  const text = (texts ?? en)[key];
  return params
    ? text.replace(PLACEHOLDER, (whole, name: string) => String(params[name] ?? whole))
    : text;
}
