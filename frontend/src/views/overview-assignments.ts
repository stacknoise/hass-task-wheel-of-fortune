import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import type { AssignmentObject, PersonObject, TaskObject } from '../api/index.ts';

import { STATUS } from '../constants/index.ts';
import { formatDateTime, formatPercent } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey, TextParams } from '../i18n/index.ts';
import { canSwap, swapTargets } from './overview-model.ts';
import type { AssignmentGroup } from './overview-model.ts';

export interface AssignmentHandlers {
  readonly complete: (assignmentId: string) => void;
  readonly toggleSwap: (assignmentId: string) => void;
  readonly swap: (assignmentId: string, personId: string) => void;
}

export interface AssignmentsContext {
  readonly language: string;
  readonly groups: readonly AssignmentGroup[];
  readonly persons: readonly PersonObject[];
  readonly personById: ReadonlyMap<string, PersonObject>;
  readonly taskById: ReadonlyMap<string, TaskObject>;
  /** Kennung der Zuteilung, deren Tauschauswahl offen ist. */
  readonly swapOpen: string;
  readonly busy: boolean;
  readonly handlers: AssignmentHandlers;
}

type Translate = (key: TextKey, params?: TextParams) => string;

function swapHint(
  task: TaskObject | undefined,
  person: PersonObject | undefined,
  text: Translate,
): string {
  if (!task?.swap_allowed) {
    return text('overview.swapDisabled');
  }
  return (person?.jokers_left ?? 0) > 0
    ? text('overview.jokers', { count: person?.jokers_left ?? 0 })
    : text('overview.noJokers');
}

function swapChoice(
  assignment: AssignmentObject,
  context: AssignmentsContext,
  text: Translate,
): TemplateResult {
  const task = context.taskById.get(assignment.task_id);
  const targets = swapTargets(assignment, task, context.persons);
  return html`
    <div class="row swap" role="group" aria-label=${text('overview.swapWith')}>
      <span class="muted">${text('overview.swapWith')}</span>
      ${
        targets.length === 0
          ? html`<span class="muted">${text('overview.noTargets')}</span>`
          : repeat(
              targets,
              (target) => target.id,
              (target) => html`
                <button
                  type="button"
                  class="action"
                  ?disabled=${context.busy}
                  @click=${() => {
                    context.handlers.swap(assignment.id, target.id);
                  }}
                >
                  <tw-avatar name=${target.name} color=${target.color}></tw-avatar> ${target.name}
                </button>
              `,
            )
      }
      <button
        type="button"
        class="action"
        @click=${() => {
          context.handlers.toggleSwap(assignment.id);
        }}
      >
        ${text('overview.cancel')}
      </button>
    </div>
  `;
}

function rowButtons(
  assignment: AssignmentObject,
  context: AssignmentsContext,
  text: Translate,
): TemplateResult {
  const person = context.personById.get(assignment.person_id);
  const task = context.taskById.get(assignment.task_id);
  return html`
    <button
      type="button"
      class="action"
      title=${swapHint(task, person, text)}
      ?disabled=${context.busy || !canSwap(task, person)}
      aria-expanded=${context.swapOpen === assignment.id ? 'true' : 'false'}
      @click=${() => {
        context.handlers.toggleSwap(assignment.id);
      }}
    >
      ${text('overview.swap')}
    </button>
    <button
      type="button"
      class="action primary"
      ?disabled=${context.busy}
      @click=${() => {
        context.handlers.complete(assignment.id);
      }}
    >
      ${text('overview.complete')}
    </button>
  `;
}

function rowMeta(
  assignment: AssignmentObject,
  context: AssignmentsContext,
  text: Translate,
): string {
  return [
    text('overview.due', { date: formatDateTime(assignment.due_at, context.language) }),
    text('overview.chance', { chance: formatPercent(assignment.chance, context.language) }),
    text('overview.points', { points: assignment.points }),
  ].join(' · ');
}

function assignmentRow(
  assignment: AssignmentObject,
  context: AssignmentsContext,
  text: Translate,
): TemplateResult {
  const person = context.personById.get(assignment.person_id);
  const task = context.taskById.get(assignment.task_id);
  const personName = person?.name ?? text('common.unknownPerson');
  return html`
    <li>
      <div class="row">
        <tw-avatar
          name=${person?.name ?? ''}
          color=${person?.color ?? ''}
          title=${personName}
        ></tw-avatar>
        <div class="grow">
          <div>${task?.name ?? text('common.unknownTask')}</div>
          <div class="muted">${personName} · ${rowMeta(assignment, context, text)}</div>
        </div>
        ${
          assignment.status === STATUS.swapped
            ? html`<tw-badge>${text('status.swapped')}</tw-badge>`
            : nothing
        }
        ${rowButtons(assignment, context, text)}
      </div>
      ${context.swapOpen === assignment.id ? swapChoice(assignment, context, text) : nothing}
    </li>
  `;
}

/** Die Zuteilungen, gruppiert nach Zeitplan. */
export function assignmentGroups(context: AssignmentsContext): TemplateResult {
  const text: Translate = (key, params) => translate(key, context.language, params);
  return html`${repeat(
    context.groups,
    (group) => group.schedule?.id ?? '',
    (group) => html`
      <section aria-label=${group.schedule?.name ?? text('overview.noSchedule')}>
        <h3>
          ${group.schedule?.name ?? text('overview.noSchedule')}
          <span class="muted"
            >${text('overview.openCount', { count: group.assignments.length })}</span
          >
        </h3>
        <ul>
          ${repeat(
            group.assignments,
            (assignment) => assignment.id,
            (assignment) => assignmentRow(assignment, context, text),
          )}
        </ul>
      </section>
    `,
  )}`;
}
