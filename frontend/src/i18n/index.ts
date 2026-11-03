import { de } from './de.ts';
import { en } from './en.ts';

export type TextKey = keyof typeof de;

const TEXTS: Readonly<Record<string, Readonly<Record<TextKey, string>>>> = { de, en };

/** Liefert den Text zu einem Schlüssel in der gewünschten Sprache (Rückfall: Englisch). */
export function translate(key: TextKey, language: string): string {
  return (TEXTS[language] ?? en)[key];
}
