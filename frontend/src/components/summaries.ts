import type { FrequencyKind, TriggerKind } from '../constants/index.ts';
import { fill, translate } from '../i18n/index.ts';
import type { FrequencyWire, TriggerWire } from '../state/index.ts';
import { timeInput } from '../state/index.ts';
import { toIds, weekdayOptions } from './options.ts';

type FrequencySummaries = {
  readonly [K in FrequencyKind]: (
    frequency: Extract<FrequencyWire, { kind: K }>,
    language: string,
  ) => string;
};
type TriggerSummaries = {
  readonly [K in TriggerKind]: (
    trigger: Extract<TriggerWire, { kind: K }>,
    language: string,
  ) => string;
};

const FREQUENCY_SUMMARIES: FrequencySummaries = {
  every_round: (_, language) => translate('frequency.summary_every_round', language),
  max_per_period: (frequency, language) =>
    fill(translate('frequency.summary_max', language), {
      count: frequency.count,
      period: translate(`period.${frequency.period}`, language),
    }),
  interval: (frequency, language) =>
    fill(translate('frequency.summary_interval', language), {
      days: frequency.days,
      tolerance: frequency.tolerance,
    }),
};

const TRIGGER_SUMMARIES: TriggerSummaries = {
  recurring: (trigger, language) => {
    const names = new Map(weekdayOptions(language).map((option) => [option.id, option.label]));
    return fill(translate('summary.recurring', language), {
      days: toIds(trigger.weekdays)
        .map((id) => names.get(id) ?? id)
        .join(' '),
      time: timeInput(trigger.time),
    });
  },
  once: (trigger, language) =>
    fill(translate('summary.once', language), {
      at: new Date(trigger.at).toLocaleString(language),
    }),
  manual: (_, language) => translate('summary.manual', language),
};

/** Kurztext einer Häufigkeitsregel für Karten (`alle 7 Tage ± 1`). */
export function describeFrequency(frequency: FrequencyWire, language: string): string {
  return (FREQUENCY_SUMMARIES[frequency.kind] as (f: FrequencyWire, l: string) => string)(
    frequency,
    language,
  );
}

/** Kurztext eines Auslösers für Karten (`Mo Do um 18:30`). */
export function describeTrigger(trigger: TriggerWire, language: string): string {
  return (TRIGGER_SUMMARIES[trigger.kind] as (t: TriggerWire, l: string) => string)(
    trigger,
    language,
  );
}
