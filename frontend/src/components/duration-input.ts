import { html } from 'lit';
import type { TemplateResult } from 'lit';

import { DEADLINE_AMOUNT_MAX, DEADLINE_UNITS, FORM_TAGS } from '../constants/index.ts';
import type { DeadlineUnit } from '../constants/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { emitChange, onChange } from './change.ts';
import { formStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import './select.ts';
import './stepper.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

/** Meldung von `tw-duration-input`: Anzahl und Einheit. */
export interface Duration {
  readonly amount: number;
  readonly unit: DeadlineUnit;
}

/** Eine Zeitspanne aus Anzahl und Einheit (Stunden, Tage, Wochen, Monate), Anzahl und Einheit nebeneinander. */
export class TwDurationInput extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    label: { type: String },
    amount: { type: Number },
    unit: { type: String },
    min: { type: Number },
  };

  static override styles = [tokenStyles, baseStyles, formStyles];

  declare label: string;
  declare amount: number;
  declare unit: DeadlineUnit;
  declare min: number;

  constructor() {
    super();
    this.label = '';
    this.amount = 1;
    this.unit = 'day';
    this.min = 1;
  }

  protected override render(): TemplateResult {
    return html`
      <div class="pair">
        <tw-stepper
          .label=${this.label}
          .value=${this.amount}
          .min=${this.min}
          .max=${DEADLINE_AMOUNT_MAX[this.unit]}
          @tw-change=${onChange<number>((amount) => {
            emitChange<Duration>(this, { amount, unit: this.unit });
          })}
        ></tw-stepper>
        <tw-select
          .label=${this.text('deadline.unit')}
          .options=${DEADLINE_UNITS.map((unit) => ({
            id: unit,
            label: this.text(`deadline.unit.${unit}` as TextKey),
          }))}
          .value=${this.unit}
          @tw-change=${onChange<DeadlineUnit>((unit) => {
            emitChange<Duration>(this, {
              amount: Math.min(Math.max(this.amount, this.min), DEADLINE_AMOUNT_MAX[unit]),
              unit,
            });
          })}
        ></tw-select>
      </div>
    `;
  }
}

defineOnce(FORM_TAGS.durationInput, TwDurationInput);
