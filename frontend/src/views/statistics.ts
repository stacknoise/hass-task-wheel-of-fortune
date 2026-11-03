import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { modelsOf } from '../api/index.ts';
import type { PersonObject, StatisticsReport, TaskObject } from '../api/index.ts';
import { baseStyles, tokenStyles, viewStyles } from '../components/index.ts';
import type { ChipItem } from '../components/index.ts';
import '../components/index.ts';
import {
  DEFAULT_RANGE,
  EVENT_CHIP_SELECT,
  STATISTICS_RANGES,
  STATISTICS_WEEKS,
  VIEW_TAGS,
} from '../constants/index.ts';
import type { StatisticsRangeId } from '../constants/index.ts';
import { formatNumber, formatPercent } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey, TextParams } from '../i18n/index.ts';
import { AsyncValue, StoreController, indexById } from '../state/index.ts';
import { pointBars, weeklyChart } from './statistics-charts.ts';
import { barRows, matrixRows } from './statistics-model.ts';

interface Kpi {
  readonly label: string;
  readonly value: string;
  readonly hint: string;
}

/** Statistik: Kennzahlen, Punkte gegen fairen Anteil, Wochenquote, Matrix, Auszeichnungen. */
export class TwStatisticsView extends LitElement {
  static override properties = { language: { type: String }, _range: { state: true } };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    css`
      :host {
        display: grid;
        gap: var(--tw-space-field);
      }
      .card {
        margin: 0;
      }
      .kpis,
      .highlights {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: var(--tw-space-field);
      }
      .kpi-value {
        font-size: 1.9em;
        font-weight: 500;
      }
      .pair {
        display: flex;
        flex-wrap: wrap;
        gap: var(--tw-space-field);
        align-items: stretch;
      }
      .pair > .card {
        flex: 1 1 340px;
      }
      .bar-row {
        display: grid;
        grid-template-columns: 80px minmax(0, 1fr) 48px;
        align-items: center;
        gap: var(--tw-space-s);
        margin-bottom: var(--tw-space-s);
      }
      .bar-row strong {
        text-align: right;
      }
      .track {
        position: relative;
        height: 18px;
        border-radius: 4px;
        background: var(--tw-color-fill);
      }
      .fill {
        height: 100%;
        border-radius: 4px;
        background: var(--tw-color-primary);
      }
      .fair {
        position: absolute;
        top: -4px;
        bottom: -4px;
        width: 2px;
        background: var(--tw-color-text);
      }
      .chart {
        width: 100%;
        height: auto;
      }
      .grid {
        stroke: var(--tw-color-divider);
      }
      .axis {
        fill: var(--tw-color-text-muted);
        font-size: 11px;
      }
      .line {
        fill: none;
        stroke: var(--tw-color-primary);
        stroke-width: 2.5;
        stroke-linejoin: round;
      }
      .dot {
        fill: var(--tw-color-surface);
        stroke: var(--tw-color-primary);
        stroke-width: 2;
      }
      td.cell {
        text-align: center;
        min-width: 48px;
        background: color-mix(
          in srgb,
          var(--tw-color-primary) calc(var(--level) * 18%),
          transparent
        );
      }
      td.cell[data-level='4'],
      td.cell[data-level='5'] {
        color: var(--tw-color-on-primary);
      }
    `,
  ];

  declare language: string;
  declare _range: StatisticsRangeId;

  readonly #store = new StoreController(this);
  readonly #report = new AsyncValue<StatisticsReport>(this);
  #started = false;

  constructor() {
    super();
    this.language = '';
    this._range = DEFAULT_RANGE;
    this.addEventListener(EVENT_CHIP_SELECT, (event) => {
      this._range = (event as CustomEvent<string>).detail as StatisticsRangeId;
      this.#load();
    });
  }

  protected override willUpdate(): void {
    if (this.#store.client && !this.#started) {
      this.#started = true;
      this.#load();
    }
  }

  protected override render(): TemplateResult | typeof nothing {
    const snapshot = this.#store.state?.snapshot;
    if (!snapshot) {
      return nothing;
    }
    const ranges: readonly ChipItem[] = STATISTICS_RANGES.map(({ id }) => ({
      id,
      label: this.#text(`statistics.range.${id}`),
    }));
    return html`
      <div class="card">
        <tw-chips
          .items=${ranges}
          selected=${this._range}
          label=${this.#text('statistics.range')}
        ></tw-chips>
      </div>
      ${this.#body(modelsOf(snapshot, 'persons'), modelsOf(snapshot, 'tasks'))}
    `;
  }

  #text(key: TextKey, params?: TextParams): string {
    return translate(key, this.language, params);
  }

  #body(persons: readonly PersonObject[], tasks: readonly TaskObject[]): TemplateResult {
    const { status, value: report } = this.#report;
    if (status === 'error') {
      return html`<p class="error" role="alert">${this.#text('common.loadError')}</p>`;
    }
    if (!report) {
      return html`<p class="empty">${this.#text('common.loading')}</p>`;
    }
    if (report.kpis.assigned === 0) {
      return html`<p class="empty">${this.#text('statistics.empty')}</p>`;
    }
    const personById = indexById(persons);
    return html`
      <div class="kpis">
        ${repeat(
          this.#kpis(report),
          (kpi) => kpi.label,
          (kpi) =>
            html`<div class="card">
              <div class="muted">${kpi.label}</div>
              <div class="kpi-value">${kpi.value}</div>
              <div class="muted">${kpi.hint}</div>
            </div>`,
        )}
      </div>
      <div class="pair">${this.#pointsCard(report, personById)} ${this.#weeklyCard(report)}</div>
      ${this.#matrixCard(report, tasks, persons)} ${this.#highlights(report, personById)}
    `;
  }

  #kpis(report: StatisticsReport): readonly Kpi[] {
    const { kpis } = report;
    return [
      {
        label: this.#text('statistics.assigned'),
        value: String(kpis.assigned),
        hint: this.#text('statistics.assignedHint', { pending: kpis.pending }),
      },
      {
        label: this.#text('statistics.rate'),
        value:
          kpis.completion_rate === null
            ? this.#text('common.none')
            : formatPercent(kpis.completion_rate, this.language),
        hint: this.#text('statistics.rateHint', { on_time: kpis.on_time, late: kpis.late }),
      },
      {
        label: this.#text('statistics.missed'),
        value: String(kpis.missed),
        hint: this.#text('statistics.missedHint'),
      },
      {
        label: this.#text('statistics.fairness'),
        value: formatNumber(report.fairness_index, this.language),
        hint: this.#text('statistics.fairnessHint'),
      },
    ];
  }

  #pointsCard(
    report: StatisticsReport,
    personById: ReadonlyMap<string, PersonObject>,
  ): TemplateResult {
    const known = report.standings.filter((entry) => personById.has(entry.person_id));
    return html`<section class="card">
      <h2>${this.#text('statistics.points')}</h2>
      <p class="muted">${this.#text('statistics.pointsHint')}</p>
      ${pointBars(barRows(known), personById, this.#text('common.unknownPerson'))}
    </section>`;
  }

  #weeklyCard(report: StatisticsReport): TemplateResult {
    const last = report.weeks.at(-1)?.rate;
    const label = this.#text('statistics.weeklyLabel', {
      weeks: STATISTICS_WEEKS,
      last:
        last === null || last === undefined
          ? this.#text('common.none')
          : formatPercent(last, this.language),
    });
    return html`<section class="card">
      <h2>${this.#text('statistics.weekly')}</h2>
      ${weeklyChart(report.weeks, this.language, label)}
    </section>`;
  }

  #matrixCard(
    report: StatisticsReport,
    tasks: readonly TaskObject[],
    persons: readonly PersonObject[],
  ): TemplateResult {
    return html`<section class="card">
      <h2>${this.#text('statistics.matrix')}</h2>
      <p class="muted">${this.#text('statistics.matrixHint')}</p>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>${this.#text('statistics.task')}</th>
              ${persons.map((person) => html`<th>${person.name}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${repeat(
              matrixRows(report.matrix, tasks, persons),
              (row) => row.taskId,
              (row) =>
                html`<tr>
                  <td>${row.name ?? this.#text('common.unknownTask')}</td>
                  ${row.cells.map(
                    (cell) =>
                      html`<td class="cell" data-level=${cell.level} style="--level: ${cell.level}">
                        ${cell.count ?? this.#text('common.none')}
                      </td>`,
                  )}
                </tr>`,
            )}
          </tbody>
        </table>
      </div>
    </section>`;
  }

  #highlights(
    report: StatisticsReport,
    personById: ReadonlyMap<string, PersonObject>,
  ): TemplateResult {
    const { lucky, unlucky, reliable } = report.highlights;
    const name = (id: string | null | undefined): string =>
      (id ? personById.get(id)?.name : undefined) ?? this.#text('common.none');
    const standing = (id: string | null) => report.standings.find((s) => s.person_id === id);
    const standingHint = (key: TextKey, id: string | null): string => {
      const entry = standing(id);
      return entry
        ? this.#text(key, {
            points: entry.points,
            difference: formatNumber(Math.abs(entry.difference), this.language),
          })
        : this.#text('statistics.noneYet');
    };
    return html`<div class="highlights">
      <div class="card">
        <div class="muted">${this.#text('statistics.lucky')}</div>
        <strong>${name(lucky)}</strong>
        <div class="muted">${standingHint('statistics.luckyHint', lucky)}</div>
      </div>
      <div class="card">
        <div class="muted">${this.#text('statistics.unlucky')}</div>
        <strong>${name(unlucky)}</strong>
        <div class="muted">${standingHint('statistics.unluckyHint', unlucky)}</div>
      </div>
      <div class="card">
        <div class="muted">${this.#text('statistics.reliable')}</div>
        <strong>${name(reliable?.person_id)}</strong>
        <div class="muted">
          ${
            reliable
              ? this.#text('statistics.reliableHint', {
                  rate: formatPercent(reliable.on_time_rate, this.language),
                  count: reliable.closed,
                })
              : this.#text('statistics.noneYet')
          }
        </div>
      </div>
    </div>`;
  }

  #load(): void {
    const client = this.#store.client;
    const months = STATISTICS_RANGES.find(({ id }) => id === this._range)?.months;
    if (client && months !== undefined) {
      void this.#report.run(() => client.statistics(months, STATISTICS_WEEKS));
    }
  }
}

customElements.define(VIEW_TAGS.statistics, TwStatisticsView);
