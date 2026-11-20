import { html } from 'lit';
import type { TemplateResult } from 'lit';

import { PERIOD_NUMBER_OFFSET } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';

export interface RoundDeleteOptions {
  readonly language: string;
  /** Zuteilungen der Auslosung insgesamt und davon schon erledigte (dann ist Löschen gesperrt). */
  readonly total: number;
  readonly done: number;
  /** Nummer der Periode (0 = erste), die die Auslosung abdeckt. */
  readonly period: number;
  /** Es gibt eine neuere Auslosung desselben Zeitplans (dann ist Löschen gesperrt: keine Lücken). */
  readonly newerDraw: boolean;
  /** Der Zeitplan lost von selbst aus: die Rückfrage weist darauf hin, dass nichts nachgeholt wird. */
  readonly automatic: boolean;
  readonly busy: boolean;
  readonly onConfirm: () => void;
}

/** Warum sich die Auslosung nicht löschen lässt; leer, wenn es geht. */
function blockedReason(options: RoundDeleteOptions): string {
  const { language, done } = options;
  if (done > 0) {
    return translate('round.deleteBlocked', language, { done });
  }
  return options.newerDraw ? translate('round.deleteNewer', language) : '';
}

/**
 * „Auslosung löschen“ mit Rückfrage; gesperrt, sobald eine Aufgabe erledigt ist oder eine neuere
 * Auslosung des Zeitplans existiert. Bei automatischen Zeitplänen sagt die Rückfrage, dass die
 * Periode nicht von selbst nachgeholt wird.
 */
export function roundDelete(options: RoundDeleteOptions): TemplateResult {
  const { language, total } = options;
  const question: TextKey = options.automatic
    ? 'round.deleteQuestionAutomatic'
    : 'round.deleteQuestion';
  return html`<tw-confirm-action
    language=${language}
    label=${translate('round.delete', language)}
    question=${translate(question, language, {
      total,
      period: options.period + PERIOD_NUMBER_OFFSET,
    })}
    blocked=${blockedReason(options)}
    ?busy=${options.busy}
    @tw-confirm=${options.onConfirm}
  ></tw-confirm-action>`;
}
