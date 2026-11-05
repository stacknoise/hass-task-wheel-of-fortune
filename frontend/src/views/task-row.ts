import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { EMPTY_TEXT } from '../constants/index.ts';
import type { DrawState, PersonInfo, TaskInfo } from '../state/index.ts';
import { winnerChip } from './winner-chip.ts';

export interface TaskRowContext {
  readonly state: DrawState;
  readonly task: TaskInfo | undefined;
  /** Die Person, der die Aufgabe schon zugeteilt wurde; sonst steht der Status in der Zeile. */
  readonly winner: PersonInfo | undefined;
  readonly current: boolean;
  readonly status: string;
  readonly points: string;
  readonly rooms: TemplateResult | typeof nothing;
  /** Rechts in der Zeile: der Knopf „Austauschen“ (nur vor dem Start). */
  readonly action: TemplateResult | typeof nothing;
}

/** Eine Zeile der Aufgabenliste: Name, Status oder Punkte und Räume links, rechts die Person. */
export function taskRow(context: TaskRowContext): TemplateResult {
  const { winner } = context;
  return html`
    <li class="task ${context.current ? 'current' : ''}">
      <span class="info">
        <span class="name">${context.task?.name ?? EMPTY_TEXT}</span>
        <span class="line">
          ${winner ? nothing : html`<span class="status">${context.status}</span>`}
          <span class="muted points">${context.points}</span>
        </span>
        <span class="rooms">${context.rooms}</span>
      </span>
      ${winner ? winnerChip(winner) : context.action}
    </li>
  `;
}
