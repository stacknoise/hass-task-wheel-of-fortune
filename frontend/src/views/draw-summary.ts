import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import '../components/index.ts';
import { DRAW_PHASE, EMPTY_TEXT } from '../constants/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { isIdle, needsConfirmation } from '../state/index.ts';
import type { DrawSession } from '../state/index.ts';
import type { DrawState, PersonInfo, TaskInfo } from '../state/index.ts';

export interface DrawSummaryContext {
  readonly state: DrawState;
  readonly tasks: ReadonlyMap<string, TaskInfo>;
  readonly persons: ReadonlyMap<string, PersonInfo>;
  readonly text: (key: TextKey) => string;
  /** Raum der Aufgabe als Marke. */
  readonly room: (task: TaskInfo | undefined) => TemplateResult | typeof nothing;
  readonly onHistory: () => void;
  readonly onAgain: () => void;
}

function row(result: DrawState['results'][number], context: DrawSummaryContext): TemplateResult {
  const task = context.tasks.get(result.task_id);
  const winner = context.persons.get(result.winner_id ?? EMPTY_TEXT)?.name;
  return html`
    <li>
      <span>${task?.name ?? result.task_id} ${context.room(task)}</span>
      <strong>${winner ?? context.text('draw.undistributable')}</strong>
    </li>
  `;
}

/** Abschluss der Auslosung: Ergebnis je Aufgabe mit Raum und die beiden Folgeaktionen. */
export function drawSummary(context: DrawSummaryContext): TemplateResult {
  const { state, text } = context;
  return html`
    <tw-confetti></tw-confetti>
    <div class="done" role="status">
      <span class="eyebrow">${text('draw.done.title')}</span>
      <span class="title"
        >${text(state.results.length > 0 ? 'draw.done.all' : 'draw.done.none')}</span
      >
      <ul class="summary">
        ${state.results.map((result) => row(result, context))}
      </ul>
      <div class="actions">
        <button class="button" @click=${context.onHistory}>${text('draw.done.history')}</button>
        <button class="button" @click=${context.onAgain}>${text('draw.done.again')}</button>
      </div>
    </div>
  `;
}

export interface StageNoticeContext {
  readonly state: DrawState;
  readonly tasks: ReadonlyMap<string, TaskInfo>;
  readonly text: (key: TextKey) => string;
  /** Die Sitzung, die der Benutzer mit „Trotzdem auslosen“ bestätigt oder mit „Abbrechen“ neu startet. */
  readonly session: DrawSession | undefined;
}

/** Warnung vor dem Start: diese Aufgaben lassen sich nicht vergeben; der Benutzer entscheidet. */
function unplaceableNotice(context: StageNoticeContext): TemplateResult {
  const { state, tasks, text } = context;
  return html`<section class="stage warning" role="alertdialog" aria-labelledby="unplaceable-title">
    <div class="heading">
      <span class="title" id="unplaceable-title">${text('draw.unplaceable.title')}</span>
      <p class="muted">${text('draw.unplaceable.body')}</p>
      <ul class="summary">
        ${state.unplaceable.map((id) => html`<li>${tasks.get(id)?.name ?? id}</li>`)}
      </ul>
      <p class="muted">${text('draw.unplaceable.ask')}</p>
    </div>
    <div class="actions">
      <button class="button primary" @click=${() => context.session?.confirmUnplaceable()}>
        ${text('draw.unplaceable.confirm')}
      </button>
      <button class="button" @click=${() => void context.session?.restart()}>
        ${text('draw.unplaceable.cancel')}
      </button>
    </div>
  </section>`;
}

/**
 * Bühne ohne Rad: Wahl des Zeitplans, die Vorbereitung ohne Animation oder die Warnung vor nicht
 * vergebbaren Aufgaben (sonst `undefined`).
 */
export function stageNotice(context: StageNoticeContext): TemplateResult | undefined {
  const { state, text } = context;
  if (needsConfirmation(state)) {
    return unplaceableNotice(context);
  }
  if (isIdle(state)) {
    return html`<section class="stage idle">
      <p class="heading">${text('draw.choose')}</p>
    </section>`;
  }
  return state.direct && state.phase === DRAW_PHASE.ready
    ? html`<section class="stage prepare"><p class="heading">${text('draw.prepare')}</p></section>`
    : undefined;
}
