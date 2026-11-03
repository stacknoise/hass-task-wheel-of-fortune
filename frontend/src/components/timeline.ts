import { LitElement, css, html } from 'lit';
import { nothing } from 'lit';
import type { TemplateResult } from 'lit';

import {
  FORM_TAGS,
  TIMELINE_GRID_MAX,
  TIMELINE_HALF,
  TIMELINE_SCALE_LABELS,
  TIMELINE_SCALE_STEPS,
} from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

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
        height: 16px;
        border-radius: 8px;
        overflow: hidden;
        --dim: color-mix(in srgb, var(--tw-color-primary) 25%, transparent);
        --mid: color-mix(in srgb, var(--tw-color-primary) 55%, transparent);
        background: linear-gradient(
          to right,
          var(--dim) calc(var(--from) * 100%),
          var(--mid) calc(var(--from) * 100%),
          var(--tw-color-primary) calc(var(--at) * 100%),
          var(--mid)
        );
      }
      .grid {
        display: block;
        height: 100%;
        background: linear-gradient(
          to right,
          color-mix(in srgb, var(--tw-color-surface) 55%, transparent) 1px,
          transparent 1px
        );
        background-size: calc(100% / var(--n)) 100%;
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

  /** Zeitachse in Tagen: erster und letzter Tag des Fensters; die Skala reicht von Tag 1 bis `latest`. */
  #axis(): { earliest: number; latest: number } {
    return {
      earliest: Math.max(1, this.days - this.tolerance),
      latest: this.days + this.tolerance,
    };
  }

  protected override render(): TemplateResult {
    const { earliest, latest } = this.#axis();
    const centre = (day: number): number => (day - TIMELINE_HALF) / latest;
    const at = (day: number): string => `--at:${String(centre(day))}`;
    const barStyle = `--from:${String((earliest - 1) / latest)};--at:${String(centre(this.days))};--n:${String(latest)}`;
    return html`
      <span class="label">${translate('frequency.timeline', this.language)}</span>
      <div class="track">
        <div
          class="bar"
          role="img"
          aria-label=${translate('frequency.timeline', this.language)}
          style=${barStyle}
        >
          ${latest <= TIMELINE_GRID_MAX ? html`<span class="grid"></span>` : nothing}
        </div>
        <span class="tick" style=${at(this.days)}></span>
      </div>
      <div class="days" aria-hidden="true">
        ${scaleDays(latest).map((day) => html`<span style=${at(day)}>${day}</span>`)}
      </div>
      <div class="scale">
        <span>${translate('timeline.earliest', this.language)}: ${earliest}</span>
        <span>${translate('timeline.target', this.language)}: ${this.days}</span>
        <span>${translate('timeline.latest', this.language)}: ${latest}</span>
      </div>
    `;
  }
}

/** Tage an der Skala: Tag 1, gleichmäßige Schritte und der letzte Tag, höchstens `TIMELINE_SCALE_LABELS`. */
export function scaleDays(total: number): readonly number[] {
  const step =
    TIMELINE_SCALE_STEPS.find((candidate) => total / candidate <= TIMELINE_SCALE_LABELS) ??
    TIMELINE_SCALE_STEPS.at(-1) ??
    1;
  const inner = Array.from({ length: Math.floor(total / step) }, (_, index) => (index + 1) * step);
  const spaced = inner.filter(
    (day) => day - 1 >= step * TIMELINE_HALF && total - day >= step * TIMELINE_HALF,
  );
  return [...new Set([1, ...spaced, total])];
}

defineOnce(FORM_TAGS.timeline, TwTimeline);
