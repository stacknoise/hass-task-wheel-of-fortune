/** Datums- und Zeitwerte zwischen Leitung (ISO-Text) und Eingabefeldern; reine Funktionen. */

import { DATE_LENGTH, MS_PER_DAY, TIME_INPUT_LENGTH, WEEKDAY_COUNT } from '../constants/index.ts';

const UTC_SUFFIX = 'T00:00:00Z';
const PAD_LENGTH = 2;
const PAD_CHAR = '0';
const MONDAY_SHIFT = 6;

/** Der Kalendertag eines ISO-Zeitpunkts oder Datums (`2026-11-03T12:00:00+00:00` ⇒ `2026-11-03`). */
export function dayOf(iso: string): string {
  return iso.slice(0, DATE_LENGTH);
}

/** Tage seit 1970 für ein Datum `JJJJ-MM-TT` (UTC, damit Sommerzeit nicht stört). */
export function dayNumber(date: string): number {
  return Math.floor(Date.parse(`${dayOf(date)}${UTC_SUFFIX}`) / MS_PER_DAY);
}

/** Das Datum `JJJJ-MM-TT` zu einer Tageszahl. */
export function dateOfDay(day: number): string {
  return new Date(day * MS_PER_DAY).toISOString().slice(0, DATE_LENGTH);
}

/** Wochentag eines Tages, Montag = 0 (wie im Backend). */
export function weekdayOf(day: number): number {
  return (new Date(day * MS_PER_DAY).getUTCDay() + MONDAY_SHIFT) % WEEKDAY_COUNT;
}

/** Uhrzeit der Leitung (`18:30:00`) als Wert des Eingabefelds (`18:30`). */
export function timeInput(time: string): string {
  return time.slice(0, TIME_INPUT_LENGTH);
}

function pad(value: number): string {
  return String(value).padStart(PAD_LENGTH, PAD_CHAR);
}

/** Zeitpunkt der Leitung als Wert eines `datetime-local`-Felds in der Ortszeit des Browsers. */
export function localInput(iso: string): string {
  const moment = new Date(iso);
  if (Number.isNaN(moment.getTime())) {
    return '';
  }
  const date = `${String(moment.getFullYear())}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}`;
  return `${date}T${pad(moment.getHours())}:${pad(moment.getMinutes())}`;
}

/** Wert eines `datetime-local`-Felds als Zeitpunkt mit Zeitzone (UTC); leer, wenn ungültig. */
export function fromLocalInput(value: string): string {
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? '' : moment.toISOString();
}
