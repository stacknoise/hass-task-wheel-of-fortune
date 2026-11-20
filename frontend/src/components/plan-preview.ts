import { css, html, nothing, unsafeCSS } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import {
  FORM_TAGS,
  PERCENT,
  TRACK_GHOST_DIVISOR,
  TRACK_GHOST_MIN,
  TRACK_ROWS_VISIBLE,
} from '../constants/index.ts';
import { hasText, translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import type { PlanIssueWire, PlanPreviewWire, PlanTrackWire } from '../state/index.ts';
import { defineOnce } from './define.ts';
import type { ChipOption } from './chip-select.ts';
import { LocalizedElement } from './localized.ts';
import { roomChips } from './room.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';
import { describeSpan } from './summaries.ts';

/** Höhe einer Zeile der Abstandsspuren in `em`; es zeigen sich `TRACK_ROWS_VISIBLE` Zeilen. */
const TRACK_HEIGHT_EM = 4.4;
const HALF = 0.5;
const UNKNOWN_ISSUE: TextKey = 'error.unknown';

/** Text zu einem Hinweis des Backends; unbekannte Hinweise ergeben den allgemeinen Fehlertext. */
function issueKey(code: string): TextKey {
  const key = `plan.issue.${code}`;
  return hasText(key) ? key : UNKNOWN_ISSUE;
}

/**
 * Live-Auswertung des Plans im Zeitplan-Editor (vom Backend gerechnet): Zahlen je Lauf, die
 * Personen im Rad, die Abstände je Aufgabe und Hinweise. Nur Warnungen erlauben das Speichern.
 */
export class TwPlanPreview extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    preview: { attribute: false },
    tasks: { attribute: false },
    people: { attribute: false },
    runDays: { type: Number },
    loading: { type: Boolean, reflect: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    css`
      :host {
        display: grid;
        gap: var(--tw-space-field);
      }
      .group {
        display: grid;
        gap: var(--tw-space-s);
      }
      .group > .muted {
        display: block;
        line-height: 1.4;
      }
      .kpis {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: var(--tw-space-s);
      }
      .kpi {
        padding: var(--tw-space-s) var(--tw-space-m);
        border: 1px solid var(--tw-color-divider);
        border-radius: 8px;
      }
      .kpi strong {
        display: block;
        font-size: 1.5em;
      }
      .kpi.warn {
        border-color: var(--tw-color-warning);
      }
      .tracks {
        display: grid;
        gap: var(--tw-space-m);
        max-height: ${unsafeCSS(String(TRACK_ROWS_VISIBLE * TRACK_HEIGHT_EM))}em;
        overflow-y: auto;
      }
      .track {
        display: grid;
        gap: var(--tw-space-xs);
      }
      .track-title {
        display: grid;
        min-width: 0;
      }
      .track-head {
        display: flex;
        align-items: baseline;
        margin-bottom: 4px;
        justify-content: space-between;
        gap: var(--tw-space-s);
      }
      .bar {
        position: relative;
        height: 14px;
        border-radius: 7px;
        background: var(--tw-color-fill);
      }
      .dot {
        position: absolute;
        top: 3px;
        width: 8px;
        height: 8px;
        margin-left: -4px;
        border-radius: 50%;
        background: var(--tw-color-primary);
      }
      .dot.ghost {
        opacity: 0.3;
      }
      .persons {
        display: flex;
        flex-wrap: wrap;
        gap: var(--tw-space-s);
      }
      .person {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 2px 10px;
        border: 1px solid var(--tw-color-divider);
        border-radius: 14px;
      }
      .swatch {
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }
      .issue {
        padding: var(--tw-space-s) var(--tw-space-m);
        border: 1px solid var(--tw-color-warning);
        border-radius: 8px;
      }
      .issue.blocking {
        border-color: var(--tw-color-error);
        color: var(--tw-color-error);
      }
      .issue.ok {
        border-color: var(--tw-color-success);
      }
      :host([loading]) .kpis,
      :host([loading]) .tracks {
        opacity: 0.6;
      }
    `,
  ];

  declare preview: PlanPreviewWire | undefined;
  /** Namen der Aufgaben (für Spuren und Hinweise). */
  declare tasks: readonly ChipOption[];
  /** Personen mit Namen und Farbe (für die Liste der Personen im Rad). */
  declare people: readonly ChipOption[];
  declare runDays: number;
  declare loading: boolean;

  constructor() {
    super();
    this.preview = undefined;
    this.tasks = [];
    this.people = [];
    this.runDays = 1;
    this.loading = false;
  }

  protected override render(): TemplateResult | typeof nothing {
    const preview = this.preview;
    if (!preview) {
      return nothing;
    }
    return html`
      <span class="label">${this.text('plan.title')}</span>
      ${this.#kpis(preview)} ${this.#persons(preview)} ${this.#tracks(preview)}
      ${this.#issues(preview.issues)}
    `;
  }

  #kpis(preview: PlanPreviewWire): TemplateResult {
    const text = (key: TextKey, params: Readonly<Record<string, number | string>>): string =>
      translate(key, this.language, params);
    const over = preview.planned > preview.capacity;
    return html`<div class="kpis">
      <div class="kpi">
        <strong>${preview.draws_per_run}</strong>
        ${text('plan.draws', {
          days: this.runDays,
          interval: describeSpan(preview.interval_hours, this.language),
        })}
      </div>
      <div class="kpi ${over ? 'warn' : ''}">
        <strong>${preview.planned}</strong>
        ${text('plan.planned', { capacity: preview.capacity })}
      </div>
      <div class="kpi ${preview.empty_draws > 0 ? 'warn' : ''}">
        <strong>${preview.empty_draws}</strong>
        ${text('plan.empty', {})}
      </div>
    </div>`;
  }

  #persons(preview: PlanPreviewWire): TemplateResult {
    const names = new Map(this.people.map((person) => [person.id, person]));
    const entries = Object.entries(preview.persons);
    return html`<div class="group">
      <span class="label">${this.text('plan.persons')}</span>
      ${
        entries.length === 0
          ? html`<span class="muted">${this.text('plan.persons.none')}</span>`
          : html`<div class="persons">
              ${entries.map(([id, count]) => {
                const person = names.get(id);
                return html`<span class="person">
                  <span class="swatch" style="background: ${person?.color ?? 'transparent'}"></span>
                  ${person?.label ?? id} · ${count}
                </span>`;
              })}
            </div>`
      }
      <span class="hint">${this.text('plan.persons.hint')}</span>
    </div>`;
  }

  #tracks(preview: PlanPreviewWire): TemplateResult | typeof nothing {
    if (preview.tracks.length === 0) {
      return nothing;
    }
    const options = new Map(this.tasks.map((task) => [task.id, task]));
    return html`<div class="group">
      <span class="label">${this.text('plan.tracks')}</span>
      <div class="tracks">
        ${repeat(
          preview.tracks,
          (track) => track.task_id,
          (track) => this.#track(track, preview, options.get(track.task_id)),
        )}
      </div>
      <span class="hint"
        >${translate('plan.tracks.legend', this.language, { draws: preview.draws_per_run })} ·
        ${this.text('plan.tracks.ghost')}</span
      >
    </div>`;
  }

  #track(
    track: PlanTrackWire,
    preview: PlanPreviewWire,
    task: ChipOption | undefined,
  ): TemplateResult {
    const draws = preview.draws_per_run;
    const ghosts = Math.max(TRACK_GHOST_MIN, Math.ceil(draws / TRACK_GHOST_DIVISOR));
    const total = draws + ghosts;
    const left = (position: number): string =>
      `left: ${String(((position + HALF) / total) * PERCENT)}%`;
    return html`<div class="track">
      <div class="track-head">
        <span class="track-title"
          ><span>${task?.label ?? track.task_id}</span
          ><span>${roomChips(task?.rooms ?? [])}</span></span
        ><span class="muted">${this.#gap(track, preview.interval_hours)}</span>
      </div>
      <div class="bar">
        ${track.positions.map((position) => html`<span class="dot" style=${left(position)}></span>`)}
        ${track.positions
          .filter((position) => position < ghosts)
          .map((position) => html`<span class="dot ghost" style=${left(position + draws)}></span>`)}
      </div>
    </div>`;
  }

  #gap(track: PlanTrackWire, intervalHours: number): string {
    if (track.every_draw) {
      return this.text('plan.gap.every');
    }
    const min = describeSpan(track.gap_min * intervalHours, this.language);
    return track.gap_min === track.gap_max
      ? min
      : translate('plan.gap.range', this.language, {
          min,
          max: describeSpan(track.gap_max * intervalHours, this.language),
        });
  }

  #issues(issues: readonly PlanIssueWire[]): TemplateResult {
    if (issues.length === 0) {
      return html`<div class="issue ok" role="status">${this.text('plan.ok')}</div>`;
    }
    const names = new Map(this.tasks.map((task) => [task.id, task.label]));
    return html`${issues.map((issue) => {
      const task = names.get(String(issue.params['task_id'] ?? ''));
      return html`<div class="issue ${issue.blocking ? 'blocking' : ''}" role="alert">
        ${translate(issueKey(issue.code), this.language, { ...issue.params, task: task ?? '' })}
      </div>`;
    })}`;
  }
}

defineOnce(FORM_TAGS.planPreview, TwPlanPreview);
