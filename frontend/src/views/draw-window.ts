import { html } from 'lit';
import type { TemplateResult } from 'lit';

import type { DrawWindowRequest } from '../api/index.ts';
import { EMPTY_TEXT } from '../constants/index.ts';
import type { ScheduleInfo } from '../state/index.ts';

export interface DrawWindowDialogOptions {
  readonly language: string;
  readonly schedule: ScheduleInfo | undefined;
  readonly now: string;
  readonly onConfirm: (request: DrawWindowRequest) => void;
  readonly onCancel: () => void;
}

/** Fragt Gilt-ab und Frist ab (Pflicht); bestätigt der Nutzer, beginnt der Aufrufer die Runde. */
export function drawWindowDialog(options: DrawWindowDialogOptions): TemplateResult {
  const { schedule } = options;
  return html`<tw-draw-start-dialog
    language=${options.language}
    scheduleName=${schedule?.name ?? EMPTY_TEXT}
    nextRun=${schedule?.nextRun ?? EMPTY_TEXT}
    now=${options.now}
    @tw-confirm=${(event: Event) => {
      event.stopPropagation();
      options.onConfirm((event as CustomEvent<DrawWindowRequest>).detail);
    }}
    @tw-cancel=${options.onCancel}
  ></tw-draw-start-dialog>`;
}

/** Die Fehlermeldung der Auslosung mit dem Fehlercode. */
export function drawFailure(message: string, codeLabel: string, code: unknown): TemplateResult {
  return html`<p class="error" role="alert">${message} (${codeLabel}: ${code})</p>`;
}
