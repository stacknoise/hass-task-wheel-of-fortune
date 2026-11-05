import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { REASON_PREFIX } from '../constants/index.ts';
import { de } from './de.ts';
import { en } from './en.ts';
import { insightsDe } from './insights.de.ts';
import { ERROR_PREFIX } from './index.ts';
import { insightsEn } from './insights.en.ts';

const SOURCE_ROOT = join(import.meta.dirname, '..');
const I18N_DIR = 'i18n';
/** Beginn dynamisch gebildeter Schlüssel: `tab.${id}` ⇒ `tab.`. */
const DYNAMIC_PREFIX = /['`]([\w.]+)\$\{/gu;

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === I18N_DIR ? [] : sourceFiles(path);
    }
    return /\.ts$/u.test(entry.name) && !/\.test\.ts$|\.testing\.ts$/u.test(entry.name)
      ? [path]
      : [];
  });
}

describe('Übersetzungsschlüssel', () => {
  it('sind in Deutsch und Englisch gleich', () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(de).sort());
    expect(Object.keys(insightsEn).sort()).toEqual(Object.keys(insightsDe).sort());
  });

  it('werden alle im Code verwendet', () => {
    const code = sourceFiles(SOURCE_ROOT)
      .map((file) => readFileSync(file, 'utf8'))
      .join('\n');
    const prefixes = [
      ERROR_PREFIX,
      REASON_PREFIX,
      ...[...code.matchAll(DYNAMIC_PREFIX)].flatMap((match) => match[1] ?? []),
    ];
    const unused = Object.keys(de).filter(
      (key) =>
        !code.includes(`'${key}'`) &&
        !code.includes(`"${key}"`) &&
        !prefixes.some((prefix) => key.startsWith(prefix)),
    );
    expect(unused).toEqual([]);
  });

  it('haben in beiden Sprachen dieselben Platzhalter', () => {
    const placeholders = (text: string): string[] => (text.match(/\{\w+\}/gu) ?? []).sort();
    const texts = { ...de } as Record<string, string>;
    const english = { ...en } as Record<string, string>;
    for (const [key, text] of Object.entries(texts)) {
      expect(placeholders(english[key] ?? ''), key).toEqual(placeholders(text));
    }
  });
});
