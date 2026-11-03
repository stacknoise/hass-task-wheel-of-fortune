import { DEFAULT_LANGUAGE } from '../constants/index.ts';

const DATE_TIME: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' };
const DATE: Intl.DateTimeFormatOptions = { dateStyle: 'medium' };
const SHORT_DATE: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'numeric' };
const FRACTION_DIGITS = 2;

function locale(language: string): string {
  return language || DEFAULT_LANGUAGE;
}

/** Datum und Uhrzeit aus einem ISO-Text; ein unlesbarer Wert bleibt unverändert. */
export function formatDateTime(iso: string, language: string): string {
  return formatWith(iso, language, DATE_TIME);
}

export function formatDate(iso: string, language: string): string {
  return formatWith(iso, language, DATE);
}

/** Tag und Monat, für Achsenbeschriftungen. */
export function formatShortDate(iso: string, language: string): string {
  return formatWith(iso, language, SHORT_DATE);
}

function formatWith(iso: string, language: string, options: Intl.DateTimeFormatOptions): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : new Intl.DateTimeFormat(locale(language), options).format(date);
}

/** Anteil (0 bis 1) als ganze Prozent mit Zeichen. */
export function formatPercent(ratio: number, language: string): string {
  return new Intl.NumberFormat(locale(language), {
    style: 'percent',
    maximumFractionDigits: 0,
  }).format(ratio);
}

/** Zahl mit höchstens zwei Nachkommastellen. */
export function formatNumber(value: number, language: string): string {
  return new Intl.NumberFormat(locale(language), { maximumFractionDigits: FRACTION_DIGITS }).format(
    value,
  );
}
