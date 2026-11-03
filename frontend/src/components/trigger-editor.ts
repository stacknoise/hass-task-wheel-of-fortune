import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import {
  AFTER_ONCE,
  DEFAULT_REMIND_DAYS,
  FORM_LIMITS,
  FORM_TAGS,
  TRIGGER_KINDS,
} from '../constants/index.ts';
import type { AfterOnce, TriggerKind } from '../constants/index.ts';
import { TRIGGER_BUILDERS, fromLocalInput, localInput, timeInput } from '../state/index.ts';
import type { TriggerWire } from '../state/index.ts';
import { emitChange, onChange } from './change.ts';
import './chip-select.ts';
import './field.ts';
import { formStyles, stackStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import { toIds, toNumbers, weekdayOptions } from './options.ts';
import './select.ts';
import './stepper.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import './toggle.ts';
import { defineOnce } from './define.ts';

type Renderer = (trigger: never) => TemplateResult | typeof nothing;

/** Auslöser eines Zeitplans: wiederkehrend, einmalig oder nur manuell. */
export class TwTriggerEditor extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    value: { attribute: false },
    now: { type: String },
  };

  static override styles = [tokenStyles, baseStyles, formStyles, stackStyles];

  declare value: TriggerWire;
  declare now: string;

  /** Eingabemaske je Art; die Tabelle ersetzt eine Verzweigung nach `kind`. */
  readonly #renderers: Readonly<Record<TriggerKind, Renderer>> = {
    recurring: (trigger: Extract<TriggerWire, { kind: 'recurring' }>) => html`
      <tw-chip-select
        .label=${this.text('trigger.weekdays')}
        .options=${weekdayOptions(this.language)}
        compact
        .selected=${toIds(trigger.weekdays)}
        @tw-change=${onChange<string[]>((ids) => {
          this.#merge({ weekdays: toNumbers(ids) });
        })}
      ></tw-chip-select>
      <tw-field
        type="time"
        .label=${this.text('trigger.time')}
        .value=${timeInput(trigger.time)}
        @tw-change=${onChange<string>((time) => {
          this.#merge({ time });
        })}
      ></tw-field>
      <tw-stepper
        .label=${this.text('trigger.every_n_weeks')}
        .value=${trigger.every_n_weeks}
        .min=${FORM_LIMITS.everyNWeeks.min}
        .max=${FORM_LIMITS.everyNWeeks.max}
        @tw-change=${onChange<number>((weeks) => {
          this.#merge({ every_n_weeks: weeks, monthly: trigger.monthly && weeks === 1 });
        })}
      ></tw-stepper>
      <tw-toggle
        .label=${this.text('trigger.monthly')}
        .checked=${trigger.monthly}
        @tw-change=${onChange<boolean>((monthly) => {
          this.#merge({ monthly, every_n_weeks: monthly ? 1 : trigger.every_n_weeks });
        })}
      ></tw-toggle>
      ${
        trigger.every_n_weeks > 1
          ? html`<tw-field
              type="date"
              .label=${this.text('trigger.anchor')}
              .value=${trigger.anchor ?? ''}
              @tw-change=${onChange<string>((anchor) => {
                this.#merge({ anchor: anchor || null });
              })}
            ></tw-field>`
          : nothing
      }
    `,
    once: (trigger: Extract<TriggerWire, { kind: 'once' }>) => html`
      <tw-field
        type="datetime-local"
        .label=${this.text('trigger.at')}
        .value=${localInput(trigger.at)}
        @tw-change=${onChange<string>((value) => {
          this.#merge({ at: fromLocalInput(value) });
        })}
      ></tw-field>
      <tw-select
        .label=${this.text('trigger.after')}
        .options=${AFTER_ONCE.map((after) => ({ id: after, label: this.text(`after.${after}`) }))}
        .value=${trigger.after}
        @tw-change=${onChange<AfterOnce>((after) => {
          this.#merge({ after });
        })}
      ></tw-select>
    `,
    manual: (trigger: Extract<TriggerWire, { kind: 'manual' }>) => html`
      <tw-toggle
        .label=${this.text('trigger.remind')}
        .checked=${trigger.remind_after_days !== null}
        @tw-change=${onChange<boolean>((on) => {
          this.#merge({ remind_after_days: on ? DEFAULT_REMIND_DAYS : null });
        })}
      ></tw-toggle>
      ${
        trigger.remind_after_days === null
          ? nothing
          : html`<tw-stepper
              .label=${this.text('trigger.remind')}
              .value=${trigger.remind_after_days}
              .min=${FORM_LIMITS.remindDays.min}
              .max=${FORM_LIMITS.remindDays.max}
              @tw-change=${onChange<number>((days) => {
                this.#merge({ remind_after_days: days });
              })}
            ></tw-stepper>`
      }
    `,
  };

  constructor() {
    super();
    this.value = TRIGGER_BUILDERS.manual('');
    this.now = '';
  }

  protected override render(): TemplateResult {
    return html`
      <tw-select
        .label=${this.text('trigger.kind')}
        .options=${TRIGGER_KINDS.map((kind) => ({ id: kind, label: this.text(`trigger.${kind}`) }))}
        .value=${this.value.kind}
        @tw-change=${onChange<TriggerKind>((kind) => {
          emitChange(this, TRIGGER_BUILDERS[kind](this.now));
        })}
      ></tw-select>
      ${this.#renderers[this.value.kind](this.value as never)}
    `;
  }

  #merge(patch: Readonly<Record<string, unknown>>): void {
    emitChange(this, { ...this.value, ...patch });
  }
}

defineOnce(FORM_TAGS.triggerEditor, TwTriggerEditor);
