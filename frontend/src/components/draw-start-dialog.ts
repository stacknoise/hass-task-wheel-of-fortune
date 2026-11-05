import { css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import {
  DEADLINE_DURATION_MIN,
  DEFAULT_DEADLINE_DURATION,
  EVENT_CANCEL,
  EVENT_CONFIRM,
  FORM_TAGS,
  MANUAL_STARTS,
} from '../constants/index.ts';
import type { ManualStart } from '../constants/index.ts';
import { formatDateTime } from '../i18n/format.ts';
import type { TextKey } from '../i18n/index.ts';
import { fromLocalInput } from '../state/index.ts';
import type { DrawWindowRequest } from '../state/index.ts';
import { onChange } from './change.ts';
import { defineOnce } from './define.ts';
import './dialog.ts';
import './duration-input.ts';
import type { Duration } from './duration-input.ts';
import './field.ts';
import { formStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import './select.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';
import './toggle.ts';

/**
 * Frage vor einer manuellen Auslosung: ab wann gelten die Aufgaben und bis wann müssen sie erledigt
 * sein (beides Pflicht). Hat der Zeitplan einen nächsten regulären Lauf, muss die Person bestätigen,
 * dass die Auslosung ihn vorzieht (er entfällt). Meldet `tw-confirm` mit einer `DrawWindowRequest`.
 */
export class TwDrawStartDialog extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    scheduleName: { type: String },
    nextRun: { type: String },
    now: { type: String },
    _start: { state: true },
    _custom: { state: true },
    _duration: { state: true },
    _ack: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    formStyles,
    css`
      section {
        display: grid;
        gap: var(--tw-space-field);
      }
      .warn {
        padding: var(--tw-space-s) var(--tw-space-m);
        border: 1px solid var(--tw-color-error);
        border-radius: 8px;
        display: grid;
        gap: var(--tw-space-s);
      }
      .buttons {
        display: flex;
        flex-wrap: wrap;
        gap: var(--tw-space-s);
      }
      .primary,
      .secondary {
        min-height: 40px;
        padding: 0 18px;
        border-radius: 20px;
        border: 1px solid var(--tw-color-divider);
        background: var(--tw-color-surface);
        cursor: pointer;
      }
      .primary {
        background: var(--tw-color-primary);
        border-color: var(--tw-color-primary);
        color: var(--tw-color-on-primary);
      }
      button:disabled {
        opacity: 0.5;
        cursor: default;
      }
    `,
  ];

  declare scheduleName: string;
  /** Der nächste reguläre Lauf (ISO) oder leer, wenn es keinen gibt. */
  declare nextRun: string;
  /** Der aktuelle Zeitpunkt (ISO) laut Home Assistant; „sofort“ beginnt dann. */
  declare now: string;
  declare _start: ManualStart;
  declare _custom: string;
  declare _duration: Duration;
  declare _ack: boolean;

  constructor() {
    super();
    this.scheduleName = '';
    this.nextRun = '';
    this.now = '';
    this._start = 'now';
    this._custom = '';
    this._duration = { amount: DEFAULT_DEADLINE_DURATION, unit: 'day' };
    this._ack = false;
  }

  protected override render(): TemplateResult {
    return html`
      <tw-dialog
        language=${this.language}
        label=${this.text('draw.window.title')}
        @tw-cancel=${() => {
          this.#emit(EVENT_CANCEL);
        }}
      >
        <section>
          <p class="muted">${this.scheduleName}</p>
          <tw-select
            .label=${this.text('draw.window.start')}
            .options=${MANUAL_STARTS.map((start) => ({
              id: start,
              label: this.text(`draw.window.start.${start}` as TextKey),
            }))}
            .value=${this._start}
            @tw-change=${onChange<ManualStart>((start) => {
              this._start = start;
            })}
          ></tw-select>
          ${
            this._start === 'custom'
              ? html`<tw-field
                  type="datetime-local"
                  .label=${this.text('draw.window.custom')}
                  .value=${this._custom}
                  @tw-change=${onChange<string>((value) => {
                    this._custom = value;
                  })}
                ></tw-field>`
              : nothing
          }
          <tw-duration-input
            .language=${this.language}
            .label=${this.text('draw.window.duration')}
            .amount=${this._duration.amount}
            .unit=${this._duration.unit}
            .min=${DEADLINE_DURATION_MIN}
            @tw-change=${onChange<Duration>((duration) => {
              this._duration = duration;
            })}
          ></tw-duration-input>
          ${this.nextRun ? this.#warning() : nothing}
        </section>
        ${this.#buttons()}
      </tw-dialog>
    `;
  }

  #buttons(): TemplateResult {
    return html`
      <div class="buttons" slot="actions">
        <button
          type="button"
          class="primary"
          ?disabled=${!this.#valid()}
          @click=${() => {
            this.#confirm();
          }}
        >
          ${this.text('draw.window.confirm')}
        </button>
        <button
          type="button"
          class="secondary"
          @click=${() => {
            this.#emit(EVENT_CANCEL);
          }}
        >
          ${this.text('form.cancel')}
        </button>
      </div>
    `;
  }

  #warning(): TemplateResult {
    return html`<div class="warn" role="alert">
      <strong>${this.text('draw.window.replaces')}</strong>
      <span>${this.#replacesText()}</span>
      <tw-toggle
        .label=${this.text('draw.window.ack')}
        .checked=${this._ack}
        @tw-change=${onChange<boolean>((ack) => {
          this._ack = ack;
        })}
      ></tw-toggle>
    </div>`;
  }

  #replacesText(): string {
    return `${this.text('draw.window.replaces.run')} ${formatDateTime(this.nextRun, this.language)}. ${this.text('draw.window.replaces.rest')}`;
  }

  #startsAt(): string {
    const starts: Readonly<Record<ManualStart, () => string>> = {
      now: () => this.now,
      custom: () => fromLocalInput(this._custom),
    };
    return starts[this._start]();
  }

  #valid(): boolean {
    return this.#startsAt() !== '' && (!this.nextRun || this._ack);
  }

  #confirm(): void {
    if (this.#valid()) {
      const request: DrawWindowRequest = {
        starts_at: this.#startsAt(),
        duration: this._duration.amount,
        duration_unit: this._duration.unit,
        replace_next: Boolean(this.nextRun),
      };
      this.dispatchEvent(
        new CustomEvent<DrawWindowRequest>(EVENT_CONFIRM, {
          detail: request,
          bubbles: true,
          composed: true,
        }),
      );
    }
  }

  #emit(name: string): void {
    this.dispatchEvent(new CustomEvent(name, { bubbles: true, composed: true }));
  }
}

defineOnce(FORM_TAGS.drawStartDialog, TwDrawStartDialog);
