import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { FORM_LIMITS, FORM_TAGS, FREQUENCY_KINDS, PERIODS } from '../constants/index.ts';
import type { FrequencyKind, Period } from '../constants/index.ts';
import { FREQUENCY_BUILDERS } from '../state/index.ts';
import type { FrequencyWire } from '../state/index.ts';
import { emitChange, onChange } from './change.ts';
import { formStyles, stackStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import './segmented.ts';
import './select.ts';
import './stepper.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import './timeline.ts';
import { defineOnce } from './define.ts';

type Renderer = (frequency: never) => TemplateResult | typeof nothing;

/** Häufigkeitsregel einer Aufgabe: Art wählen, Werte einstellen, bei festem Intervall mit Zeitstrahl. */
export class TwFrequencyEditor extends LocalizedElement {
  static override properties = { ...LocalizedElement.properties, value: { attribute: false } };

  static override styles = [tokenStyles, baseStyles, formStyles, stackStyles];

  declare value: FrequencyWire;

  /** Eingabemaske je Art; die Tabelle ersetzt eine Verzweigung nach `kind`. */
  readonly #renderers: Readonly<Record<FrequencyKind, Renderer>> = {
    every_round: () => nothing,
    max_per_period: (frequency: Extract<FrequencyWire, { kind: 'max_per_period' }>) => html`
      <div class="pair">
        <tw-stepper
          .label=${this.text('frequency.count')}
          .value=${frequency.count}
          .min=${FORM_LIMITS.periodCount.min}
          .max=${FORM_LIMITS.periodCount.max}
          @tw-change=${onChange<number>((count) => {
            this.#merge({ count });
          })}
        ></tw-stepper>
        <tw-stepper
          .label=${this.text('frequency.every')}
          .value=${frequency.every}
          .min=${FORM_LIMITS.periodEvery.min}
          .max=${FORM_LIMITS.periodEvery.max}
          @tw-change=${onChange<number>((every) => {
            this.#merge({ every });
          })}
        ></tw-stepper>
      </div>
      <tw-segmented
        .label=${this.text('frequency.period')}
        .options=${PERIODS.map((period) => ({ id: period, label: this.text(`period.${period}`) }))}
        .value=${frequency.period}
        @tw-change=${onChange<Period>((period) => {
          this.#merge({ period });
        })}
      ></tw-segmented>
    `,
    interval: (frequency: Extract<FrequencyWire, { kind: 'interval' }>) => html`
      <div class="pair">
        <tw-stepper
          .label=${this.text('frequency.days')}
          .value=${frequency.days}
          .min=${FORM_LIMITS.intervalDays.min}
          .max=${FORM_LIMITS.intervalDays.max}
          @tw-change=${onChange<number>((days) => {
            this.#merge({ days, tolerance: Math.min(frequency.tolerance, days - 1) });
          })}
        ></tw-stepper>
        <tw-stepper
          .label=${this.text('frequency.tolerance')}
          .value=${frequency.tolerance}
          .min=${0}
          .max=${frequency.days - 1}
          @tw-change=${onChange<number>((tolerance) => {
            this.#merge({ tolerance });
          })}
        ></tw-stepper>
      </div>
      <tw-timeline
        .language=${this.language}
        .days=${frequency.days}
        .tolerance=${frequency.tolerance}
      ></tw-timeline>
    `,
  };

  constructor() {
    super();
    this.value = FREQUENCY_BUILDERS.every_round();
  }

  protected override render(): TemplateResult {
    return html`
      <tw-select
        .label=${this.text('tasks.frequency')}
        .options=${FREQUENCY_KINDS.map((kind) => ({ id: kind, label: this.text(`frequency.${kind}`) }))}
        .value=${this.value.kind}
        @tw-change=${onChange<FrequencyKind>((kind) => {
          emitChange(this, FREQUENCY_BUILDERS[kind]());
        })}
      ></tw-select>
      ${this.#renderers[this.value.kind](this.value as never)}
    `;
  }

  #merge(patch: Partial<FrequencyWire>): void {
    emitChange(this, { ...this.value, ...patch });
  }
}

defineOnce(FORM_TAGS.frequencyEditor, TwFrequencyEditor);
