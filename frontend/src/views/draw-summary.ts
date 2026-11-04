import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import '../components/index.ts';
import { EMPTY_TEXT } from '../constants/index.ts';
import type { TextKey } from '../i18n/index.ts';
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
