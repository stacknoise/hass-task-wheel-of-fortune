import { INTERVAL_UNIT_HOURS } from '../constants/index.ts';
import type { IntervalUnit } from '../constants/index.ts';
import { formatNumber } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { IntervalWire } from '../state/index.ts';

const SINGULAR = 1;
/** Ab zwei Tagen zählt eine Dauer in Tagen, auch mit Bruchteil. */
const MULTI_DAY_COUNT = 2;
const MULTI_DAY_HOURS = INTERVAL_UNIT_HOURS.day * MULTI_DAY_COUNT;

/** Anzahl mit Einheit in der richtigen Zahl (`1 Stunde`, `4 Tage`). */
function describeAmount(count: number, unit: IntervalUnit, language: string): string {
  const form = count === SINGULAR ? 'one' : 'other';
  return translate(`span.${unit}.${form}`, language, { count: formatNumber(count, language) });
}

/** Kurztext eines Intervalls für Karten (`alle 7 Tage`, `jeden Tag`). */
export function describeInterval(interval: IntervalWire, language: string): string {
  return interval.every === SINGULAR
    ? translate(`interval.single.${interval.unit}`, language)
    : translate('interval.every', language, {
        span: describeAmount(interval.every, interval.unit, language),
      });
}

/** Eine Dauer in Stunden als Text in der größten Einheit, in der sie ohne Rest aufgeht (sonst Tage mit Nachkomma). */
export function describeSpan(hours: number, language: string): string {
  if (hours % INTERVAL_UNIT_HOURS.week === 0) {
    return describeAmount(hours / INTERVAL_UNIT_HOURS.week, 'week', language);
  }
  if (hours % INTERVAL_UNIT_HOURS.day === 0 || hours >= MULTI_DAY_HOURS) {
    return describeAmount(hours / INTERVAL_UNIT_HOURS.day, 'day', language);
  }
  return describeAmount(hours, 'hour', language);
}
