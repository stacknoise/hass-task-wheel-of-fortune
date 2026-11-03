import { WEEKDAYS } from '../constants/index.ts';
import type { Weekday } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import type { ChipOption } from './chip-select.ts';

/** Textschlüssel der Wochentage. */
export const WEEKDAY_TEXT: Readonly<Record<Weekday, TextKey>> = {
  0: 'weekday.0',
  1: 'weekday.1',
  2: 'weekday.2',
  3: 'weekday.3',
  4: 'weekday.4',
  5: 'weekday.5',
  6: 'weekday.6',
};

/** Chips für die sieben Wochentage (Kennung = Zahl, Montag = 0). */
export function weekdayOptions(language: string): readonly ChipOption[] {
  return WEEKDAYS.map((day) => ({
    id: String(day),
    label: translate(WEEKDAY_TEXT[day], language),
  }));
}

/** Chips für die Wochen 1 bis `count` eines Rhythmus (Kennung = Index ab 0). */
export function weekOptions(count: number, language: string): readonly ChipOption[] {
  const prefix = translate('absence.week_n', language);
  return Array.from({ length: count }, (_, index) => ({
    id: String(index),
    label: `${prefix} ${String(index + 1)}`,
  }));
}

/** Kennungen (Text) als Zahlen und zurück. */
export const toNumbers = (ids: readonly string[]): readonly number[] => ids.map(Number);
export const toIds = (numbers: readonly number[]): readonly string[] => numbers.map(String);
