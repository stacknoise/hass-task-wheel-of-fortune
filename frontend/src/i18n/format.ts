import { DEFAULT_LANGUAGE } from '../constants/index.ts';

const DATE_TIME: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' };
const DATE: Intl.DateTimeFormatOptions = { dateStyle: 'medium' };
const SHORT_DATE: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'numeric' };
const PERCENT: Intl.NumberFormatOptions = { style: 'percent', maximumFractionDigits: 0 };
const FRACTION_DIGITS = 2;
const NUMBER: Intl.NumberFormatOptions = { maximumFractionDigits: FRACTION_DIGITS };

function locale(language: string): string {
  return language || DEFAULT_LANGUAGE;
}

/**
 * Liefert zu einer Sprache den Formatierer, der pro Sprache nur einmal gebaut wird (das Erzeugen
 * von `Intl`-Formatierern ist teuer, die Historie und der CSV-Export rufen sie je Zeile auf).
 */
function perLanguage<T>(create: (locale: string) => T): (language: string) => T {
  const formatters = new Map<string, T>();
  return (language) => {
    const key = locale(language);
    let formatter = formatters.get(key);
    if (formatter === undefined) {
      formatter = create(key);
      formatters.set(key, formatter);
    }
    return formatter;
  };
}

const dateTimeFormat = perLanguage((tag) => new Intl.DateTimeFormat(tag, DATE_TIME));
const dateFormat = perLanguage((tag) => new Intl.DateTimeFormat(tag, DATE));
const shortDateFormat = perLanguage((tag) => new Intl.DateTimeFormat(tag, SHORT_DATE));
const percentFormat = perLanguage((tag) => new Intl.NumberFormat(tag, PERCENT));
const numberFormat = perLanguage((tag) => new Intl.NumberFormat(tag, NUMBER));

/** Datum und Uhrzeit aus einem ISO-Text; ein unlesbarer Wert bleibt unverändert. */
export function formatDateTime(iso: string, language: string): string {
  return formatWith(iso, dateTimeFormat(language));
}

export function formatDate(iso: string, language: string): string {
  return formatWith(iso, dateFormat(language));
}

/** Tag und Monat, für Achsenbeschriftungen. */
export function formatShortDate(iso: string, language: string): string {
  return formatWith(iso, shortDateFormat(language));
}

function formatWith(iso: string, format: Intl.DateTimeFormat): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : format.format(date);
}

/** Anteil (0 bis 1) als ganze Prozent mit Zeichen. */
export function formatPercent(ratio: number, language: string): string {
  return percentFormat(language).format(ratio);
}

/** Zahl mit höchstens zwei Nachkommastellen. */
export function formatNumber(value: number, language: string): string {
  return numberFormat(language).format(value);
}
