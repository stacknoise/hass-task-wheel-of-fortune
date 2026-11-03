import { html, svg } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import type { PersonObject, WeekRate } from '../api/index.ts';
import { CHART, PAIR } from '../constants/index.ts';
import { formatPercent, formatShortDate } from '../i18n/format.ts';
import { chartPoints, chartSegments } from './statistics-model.ts';
import type { BarRow } from './statistics-model.ts';

const GRID_OFFSET = 4;

/** Balken der Punkte je Person mit Strich für den fairen Anteil. */
export function pointBars(
  rows: readonly BarRow[],
  personById: ReadonlyMap<string, PersonObject>,
  unknown: string,
): TemplateResult {
  return html`${repeat(
    rows,
    (row) => row.personId,
    (row) => {
      const person = personById.get(row.personId);
      return html`<div class="bar-row">
        <span>${person?.name ?? unknown}</span>
        <div class="track">
          <div
            class="fill"
            style="width: ${row.pointsPercent}%; background: ${person?.color ?? ''}"
          ></div>
          <div class="fair" style="left: ${row.fairPercent}%"></div>
        </div>
        <strong>${row.points}</strong>
      </div>`;
    },
  )}`;
}

/** Liniendiagramm der Erledigungsquote je Woche (SVG, ohne Diagrammbibliothek). */
export function weeklyChart(
  weeks: readonly WeekRate[],
  language: string,
  label: string,
): TemplateResult {
  const points = chartPoints(weeks);
  return html`<svg
    viewBox="0 0 ${CHART.width} ${CHART.height}"
    role="img"
    aria-label=${label}
    class="chart"
  >
    ${CHART.ticks.map((tick) => {
      const y = CHART.bottom - tick * (CHART.bottom - CHART.top);
      return svg`<line class="grid" x1=${CHART.left} x2=${CHART.right} y1=${y} y2=${y}></line>
        <text class="axis" x=${CHART.left - GRID_OFFSET * PAIR} y=${y + GRID_OFFSET} text-anchor="end">${formatPercent(tick, language)}</text>`;
    })}
    ${chartSegments(points).map(
      (segment) =>
        svg`<polyline class="line" points=${segment.map((p) => `${String(p.x)},${String(p.y ?? 0)}`).join(' ')}></polyline>`,
    )}
    ${points.map(
      (point) => svg`
        ${
          point.y === undefined
            ? ''
            : svg`<circle class="dot" cx=${point.x} cy=${point.y} r="4"></circle>`
        }
        <text class="axis" x=${point.x} y=${CHART.labelY} text-anchor="middle">${formatShortDate(point.weekStart, language)}</text>`,
    )}
  </svg>`;
}
