import { html } from 'lit';
import type { TemplateResult } from 'lit';

import { translate } from '../i18n/index.ts';

export interface RoundDeleteOptions {
  readonly language: string;
  /** Zuteilungen der Auslosung insgesamt und davon schon erledigte (dann ist Löschen gesperrt). */
  readonly total: number;
  readonly done: number;
  readonly busy: boolean;
  readonly onConfirm: () => void;
}

/** „Auslosung löschen“ mit Rückfrage; gesperrt, sobald eine Aufgabe erledigt ist. */
export function roundDelete(options: RoundDeleteOptions): TemplateResult {
  const { language, total, done } = options;
  return html`<tw-confirm-delete
    language=${language}
    label=${translate('round.delete', language)}
    question=${translate('round.deleteQuestion', language, { total })}
    blocked=${done > 0 ? translate('round.deleteBlocked', language, { done }) : ''}
    ?busy=${options.busy}
    @tw-confirm=${options.onConfirm}
  ></tw-confirm-delete>`;
}
