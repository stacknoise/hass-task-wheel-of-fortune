import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { FORM_TAGS, TIMELINE_SCALE_LABELS, TIMELINE_SCALE_STEPS } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/** Zeitstrahl eines festen Intervalls: gesperrt, Toleranz und frei, in Tagen nach der letzten Zuteilung. */
export class TwTimeline extends LitElement {
  static override properties = {
    days: { type: Number },
    tolerance: { type: Number },
    language: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      .bar {
        display: flex;
        height: 16px;
        border-radius: 8px;
        overflow: hidden;
      }
      .outside {
        background: color-mix(in srgb, var(--tw-color-primary) 30%, transparent);
      }
      .window {
        background: var(--tw-color-primary);
      }
      .track {
        position: relative;
      }
      .tick {
        position: absolute;
        top: 0;
        bottom: 0;
        left: calc(var(--at) * 100%);
        width: 2px;
        translate: -50% 0;
        background: var(--tw-color-text);
      }
      .days {
        position: relative;
        height: 1.3em;
        margin-top: 2px;
        font-size: 0.75em;
        color: var(--tw-color-text-muted);
      }
      .days span {
        position: absolute;
        left: calc(var(--at) * 100%);
        translate: calc(var(--at) * -100%) 0;
        font-variant-numeric: tabular-nums;
      }
      .scale {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        gap: 2px 12px;
        margin-top: 4px;
        font-size: 0.8em;
        color: var(--tw-color-text-muted);
      }
    `,
  ];

  declare days: number;
  declare tolerance: number;
  declare language: string;

  constructor() {
    super();
    this.days = 1;
    this.tolerance = 0;
    this.language = '';
  }

  /** Zeitachse: Anfang, Toleranzfenster und Ende; hinter dem Fenster bleibt ein Stück Skala. */
  #axis(): { earliest: number; latest: number; total: number } {
    const earliest = Math.max(0, this.days - this.tolerance);
    const latest = this.days + this.tolerance;
    return { earliest, latest, total: latest + Math.max(1, this.tolerance) };
  }

  /** Tage an der Skala: gleichmäßige Schritte von 0 an, höchstens `TIMELINE_SCALE_LABELS` Zahlen. */
  #scaleDays(total: number): readonly number[] {
    const step =
      TIMELINE_SCALE_STEPS.find((candidate) => total / candidate <= TIMELINE_SCALE_LABELS) ??
      TIMELINE_SCALE_STEPS.at(-1) ??
      1;
    return Array.from({ length: Math.floor(total / step) + 1 }, (_, index) => index * step);
  }

  protected override render(): TemplateResult {
    const { earliest, latest, total } = this.#axis();
    const at = (day: number): string => `--at:${String(day / total)}`;
    const share = (days: number): string => `flex:${String(days / total)}`;
    return html`
      <span class="label">${translate('frequency.timeline', this.language)}</span>
      <div class="track">
        <div class="bar" role="img" aria-label=${translate('frequency.timeline', this.language)}>
          <span class="outside" style=${share(earliest)}></span>
          <span class="window" style=${share(latest - earliest)}></span>
          <span class="outside" style=${share(total - latest)}></span>
        </div>
        <span class="tick" style=${at(this.days)}></span>
      </div>
      <div class="days" aria-hidden="true">
        ${this.#scaleDays(total).map((day) => html`<span style=${at(day)}>${day}</span>`)}
      </div>
      <div class="scale">
        <span>${translate('timeline.earliest', this.language)}: ${earliest}</span>
        <span>${translate('timeline.target', this.language)}: ${this.days}</span>
        <span>${translate('timeline.latest', this.language)}: ${latest}</span>
      </div>
    `;
  }
}

customElements.define(FORM_TAGS.timeline, TwTimeline);
