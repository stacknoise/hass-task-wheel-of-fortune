import { html } from 'lit';
import type { TemplateResult } from 'lit';

import { translate } from '../i18n/index.ts';

export interface RoundDeleteOptions {
  readonly language: string;
  /** Zuteilungen der Auslosung insgesamt und davon schon abgeschlossene. */
  readonly total: number;
  readonly closed: number;
  readonly busy: boolean;
  readonly onConfirm: () => void;
}

/** „Auslosung löschen“ mit Rückfrage; die Frage nennt, was mit den Punkten geschieht. */
export function roundDelete(options: RoundDeleteOptions): TemplateResult {
  const { language, total, closed } = options;
  return html`<tw-confirm-delete
    language=${language}
    label=${translate('round.delete', language)}
    question=${translate('round.deleteQuestion', language, { total, closed })}
    ?busy=${options.busy}
    @tw-confirm=${options.onConfirm}
  ></tw-confirm-delete>`;
}
