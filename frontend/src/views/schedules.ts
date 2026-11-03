import { css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { tasksOf } from '../api/index.ts';
import type { ScheduleWire, Snapshot } from '../api/index.ts';
import { describeTrigger, onChange } from '../components/index.ts';
import type { ChipOption } from '../components/index.ts';
import '../components/index.ts';
import { EVENT_DRAWN_NAME, SERVICE_DRAW, VIEW_TAGS } from '../constants/index.ts';
import { TRIGGER_BUILDERS } from '../state/index.ts';
import type { TriggerWire } from '../state/index.ts';
import { ConfigView } from './config-view.ts';
import type { ConfigTexts } from './config-view.ts';
import { defineOnce } from '../components/define.ts';

interface ScheduleDraft {
  readonly name: string;
  readonly trigger: TriggerWire;
  readonly task_ids: readonly string[];
  readonly enabled: boolean;
  readonly notify: boolean;
  readonly skip_absent: boolean;
  readonly archived: boolean;
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
      enabled: true,
      notify: true,
      skip_absent: true,
      archived: false,
      slug: '',
    };
  }

  protected draftOf(schedule: ScheduleWire): ScheduleDraft {
    return {
      name: schedule.name,
      slug: schedule.slug,
      trigger: schedule.trigger,
      task_ids: schedule.task_ids,
      enabled: schedule.enabled,
      notify: schedule.notify,
      skip_absent: schedule.skip_absent,
      archived: schedule.archived,
    };
  }

  protected payload(draft: ScheduleDraft): object {
    return {
      name: draft.name,
      trigger: draft.trigger,
      task_ids: draft.task_ids,
      enabled: draft.enabled,
      notify: draft.notify,
      skip_absent: draft.skip_absent,
      archived: draft.archived && !draft.enabled,
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
      <tw-chip-select
        .label=${this.text('schedules.tasks')}
        .options=${tasks}
        .selected=${draft.task_ids}
        .error=${this.fieldError('task_ids')}
        @tw-change=${onChange<string[]>((task_ids) => {
          this.patch({ task_ids });
        })}
      ></tw-chip-select>
      ${this.toggle('schedules.enabled', 'enabled', draft.enabled)}
      ${this.toggle('schedules.notify', 'notify', draft.notify)}
      ${this.toggle('schedules.skip_absent', 'skip_absent', draft.skip_absent)}
      ${draft.slug ? this.#example(draft.slug) : nothing}
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
