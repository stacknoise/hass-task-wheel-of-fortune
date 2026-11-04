import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import {
  DEADLINE_DURATION_MIN,
  DEADLINE_OFFSET_MIN,
  DEADLINE_STARTS,
  FORM_TAGS,
  WEEKDAYS,
} from '../constants/index.ts';
import type { DeadlineStart } from '../constants/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { timeInput } from '../state/index.ts';
import type { DeadlineWire } from '../state/index.ts';
import { emitChange, onChange } from './change.ts';
import './duration-input.ts';
import type { Duration } from './duration-input.ts';
import './field.ts';
import { formStyles, stackStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import { WEEKDAY_TEXT } from './options.ts';
import './select.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';
import { defineOnce } from './define.ts';

/** Ob die Art des Beginns eine Uhrzeit braucht (Folgetag, Wochentag). */
const NEEDS_TIME: ReadonlySet<DeadlineStart> = new Set(['next_day', 'weekday']);

/**
 * Frist eines Zeitplans: ab wann die Zeit für die Aufgaben läuft (sofort, nach einem Versatz,
 * am Folgetag oder am nächsten Wochentag zu einer Uhrzeit) und wie lange sie dauert. Wer in
 * diesem Zeitraum nie anwesend ist, bekommt keine Aufgabe des Zeitplans.
 */
export class TwDeadlineEditor extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    value: { attribute: false },
  };

  static override styles = [tokenStyles, baseStyles, viewStyles, formStyles, stackStyles];

  declare value: DeadlineWire;

  protected override render(): TemplateResult {
    const deadline = this.value;
    return html`
      <span class="label">${this.text('deadline.title')}</span>
      <tw-select
        .label=${this.text('deadline.start')}
        .options=${DEADLINE_STARTS.map((start) => ({
          id: start,
          label: this.text(`deadline.start.${start}` as TextKey),
        }))}
        .value=${deadline.start}
        @tw-change=${onChange<DeadlineStart>((start) => {
          this.#merge({ start });
        })}
      ></tw-select>
      ${this.#offset(deadline)} ${this.#weekday(deadline)} ${this.#time(deadline)}
      <tw-duration-input
        .language=${this.language}
        .label=${this.text('deadline.duration')}
        .amount=${deadline.duration}
        .unit=${deadline.duration_unit}
        .min=${DEADLINE_DURATION_MIN}
        @tw-change=${onChange<Duration>(({ amount, unit }) => {
          this.#merge({ duration: amount, duration_unit: unit });
        })}
      ></tw-duration-input>
      <span class="muted">${this.text('deadline.hint')}</span>
    `;
  }

  #offset(deadline: DeadlineWire): TemplateResult | typeof nothing {
    return deadline.start === 'offset'
      ? html`<tw-duration-input
          .language=${this.language}
          .label=${this.text('deadline.offset')}
          .amount=${deadline.offset}
          .unit=${deadline.offset_unit}
          .min=${DEADLINE_OFFSET_MIN}
          @tw-change=${onChange<Duration>(({ amount, unit }) => {
            this.#merge({ offset: amount, offset_unit: unit });
          })}
        ></tw-duration-input>`
      : nothing;
  }

  #weekday(deadline: DeadlineWire): TemplateResult | typeof nothing {
    return deadline.start === 'weekday'
      ? html`<tw-select
          .label=${this.text('deadline.weekday')}
          .options=${WEEKDAYS.map((day) => ({
            id: String(day),
            label: this.text(WEEKDAY_TEXT[day]),
          }))}
          .value=${String(deadline.weekday)}
          @tw-change=${onChange<string>((day) => {
            this.#merge({ weekday: Number(day) });
          })}
        ></tw-select>`
      : nothing;
  }

  #time(deadline: DeadlineWire): TemplateResult | typeof nothing {
    return NEEDS_TIME.has(deadline.start)
      ? html`<tw-field
          type="time"
          .label=${this.text('deadline.time')}
          .value=${timeInput(deadline.time)}
          @tw-change=${onChange<string>((time) => {
            this.#merge({ time });
          })}
        ></tw-field>`
      : nothing;
  }

  #merge(patch: Partial<DeadlineWire>): void {
    emitChange<DeadlineWire>(this, { ...this.value, ...patch });
  }
}

defineOnce(FORM_TAGS.deadlineEditor, TwDeadlineEditor);
