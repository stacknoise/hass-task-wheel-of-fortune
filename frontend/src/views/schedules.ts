import { css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { tasksOf } from '../api/index.ts';
import type { ScheduleWire, Snapshot } from '../api/index.ts';
import { describeDeadline, describeTrigger, onChange } from '../components/index.ts';
import type { ChipOption } from '../components/index.ts';
import type { AnimationKind } from '../constants/index.ts';
import type { TextKey } from '../i18n/index.ts';
import '../components/index.ts';
import {
  ANIMATION_KINDS,
  DEFAULT_ANIMATIONS,
  EVENT_DRAWN_NAME,
  SERVICE_DRAW,
  VIEW_TAGS,
} from '../constants/index.ts';
import { DEADLINE_DEFAULT, TRIGGER_BUILDERS, animationsOf } from '../state/index.ts';
import type { DeadlineWire, TriggerWire } from '../state/index.ts';
import { ConfigView } from './config-view.ts';
import type { ConfigTexts } from './config-view.ts';
import { defineOnce } from '../components/define.ts';

interface ScheduleDraft {
  readonly name: string;
  readonly trigger: TriggerWire;
  readonly task_ids: readonly string[];
  readonly deadline: DeadlineWire;
  readonly enabled: boolean;
  readonly notify: boolean;
  readonly skip_absent: boolean;
  readonly archived: boolean;
  readonly animations: readonly AnimationKind[];
  readonly slug: string;
}

const TEXTS: ConfigTexts = {
  add: 'schedules.add',
  create: 'schedules.new',
  edit: 'schedules.edit',
};

/** Zeitpläne: Auslöser, Aufgabenwahl, Optionen und ein Beispiel für Automationen. */
export class SchedulesView extends ConfigView<ScheduleWire, ScheduleDraft> {
  static override styles = [
    ...ConfigView.styles,
    css`
      pre {
        margin: 0;
        padding: var(--tw-space-s);
        overflow-x: auto;
        border-radius: 8px;
        background: var(--tw-color-background);
        font-size: 0.85em;
      }
    `,
  ];

  protected readonly resource = 'schedule';
  protected readonly collection = 'schedules';
  protected readonly texts = TEXTS;

  protected blank(snapshot: Snapshot): ScheduleDraft {
    return {
      name: '',
      trigger: TRIGGER_BUILDERS.manual(snapshot.now),
      task_ids: [],
      deadline: DEADLINE_DEFAULT,
      enabled: true,
      notify: true,
      skip_absent: true,
      archived: false,
      animations: DEFAULT_ANIMATIONS,
      slug: '',
    };
  }

  protected draftOf(schedule: ScheduleWire): ScheduleDraft {
    return {
      name: schedule.name,
      slug: schedule.slug,
      trigger: schedule.trigger,
      task_ids: schedule.task_ids,
      deadline: schedule.deadline,
      enabled: schedule.enabled,
      notify: schedule.notify,
      skip_absent: schedule.skip_absent,
      archived: schedule.archived,
      animations: animationsOf(schedule.animations),
    };
  }

  protected payload(draft: ScheduleDraft): object {
    return {
      name: draft.name,
      trigger: draft.trigger,
      task_ids: draft.task_ids,
      deadline: draft.deadline,
      enabled: draft.enabled,
      notify: draft.notify,
      skip_absent: draft.skip_absent,
      archived: draft.archived && !draft.enabled,
      animations: draft.animations,
    };
  }

  protected card(schedule: ScheduleWire): TemplateResult {
    const state = schedule.archived
      ? this.text('schedules.archived')
      : schedule.enabled
        ? ''
        : this.text('schedules.disabled');
    return html`
      <strong>${schedule.name}</strong>
      <div class="muted">${describeTrigger(schedule.trigger, this.language)}</div>
      <div class="muted">${describeDeadline(schedule.deadline, this.language)}</div>
      <div class="muted">${schedule.task_ids.length} ${this.text('tab.tasks')} ${state}</div>
    `;
  }

  protected form(draft: ScheduleDraft, snapshot: Snapshot): TemplateResult {
    const tasks: readonly ChipOption[] = tasksOf(snapshot).map((task) => ({
      id: task.id,
      label: task.name,
    }));
    return html`
      ${this.nameField(draft.name, (name) => {
        this.patch({ name });
      })}
      <tw-trigger-editor
        .language=${this.language}
        .now=${snapshot.now}
        .value=${draft.trigger}
        @tw-change=${onChange<TriggerWire>((trigger) => {
          this.patch({ trigger });
        })}
      ></tw-trigger-editor>
      ${this.fieldError('trigger') ? html`<div class="banner">${this.fieldError('trigger')}</div>` : nothing}
      ${
        draft.trigger.kind === 'manual'
          ? html`<span class="muted">${this.text('deadline.manual_hint')}</span>`
          : html`<tw-deadline-editor
              .language=${this.language}
              .value=${draft.deadline}
              @tw-change=${onChange<DeadlineWire>((deadline) => {
                this.patch({ deadline });
              })}
            ></tw-deadline-editor>`
      }
      <tw-chip-select
        .label=${this.text('schedules.tasks')}
        .options=${tasks}
        .selected=${draft.task_ids}
        .error=${this.fieldError('task_ids')}
        @tw-change=${onChange<string[]>((task_ids) => {
          this.patch({ task_ids });
        })}
      ></tw-chip-select>
      <div>
        ${this.toggle('schedules.enabled', 'enabled', draft.enabled)}
        ${this.toggle('schedules.notify', 'notify', draft.notify)}
        ${this.toggle('schedules.skip_absent', 'skip_absent', draft.skip_absent)}
      </div>
      ${this.#animations(draft.animations)} ${draft.slug ? this.#example(draft.slug) : nothing}
    `;
  }

  /** Mehrfachauswahl der Animationen; bei mehreren wird bei jeder Auslosung zufällig eine genommen. */
  #animations(selected: readonly AnimationKind[]): TemplateResult {
    const options: readonly ChipOption[] = ANIMATION_KINDS.map((kind) => ({
      id: kind,
      label: this.text(`animation.${kind}` as TextKey),
    }));
    return html`
      <tw-chip-select
        .label=${this.text('schedules.animations')}
        .options=${options}
        .selected=${selected}
        .error=${this.fieldError('animations')}
        @tw-change=${onChange<AnimationKind[]>((animations) => {
          this.patch({ animations });
        })}
      ></tw-chip-select>
      <span class="muted">${this.text('schedules.animations.hint')}</span>
    `;
  }

  #example(slug: string): TemplateResult {
    return html`
      <div>
        <span class="label">${this.text('schedules.example')}</span>
        <pre>
action: ${SERVICE_DRAW}
data:
  schedule: ${slug}</pre>
        <pre>
trigger: event
event_type: ${EVENT_DRAWN_NAME}</pre>
      </div>
    `;
  }
}

defineOnce(VIEW_TAGS.schedules, SchedulesView);
