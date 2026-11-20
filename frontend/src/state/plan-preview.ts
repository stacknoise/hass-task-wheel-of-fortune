import type { ReactiveControllerHost } from 'lit';

import type { ApiClient, PlanPreviewRequest, PlanPreviewWire } from '../api/index.ts';
import { PLAN_PREVIEW_DEBOUNCE_MS } from '../constants/index.ts';
import { AsyncValue } from './async-value.ts';

/**
 * Bewertung der Planung eines Zeitplans im Editor: rechnet das Backend nach der letzten Eingabe
 * (entprellt) und merkt sich die zuletzt angefragte Planung, damit Änderungen an anderen Feldern
 * nichts auslösen. Ein Fehler der Auswertung sperrt nichts; das Speichern prüft das Backend ohnehin.
 */
export class PlanPreviewLoader {
  readonly #result: AsyncValue<PlanPreviewWire>;
  #timer: ReturnType<typeof setTimeout> | undefined;
  #key = '';

  constructor(host: ReactiveControllerHost) {
    this.#result = new AsyncValue<PlanPreviewWire>(host);
  }

  /** Die zuletzt berechnete Bewertung; während einer neuen Rechnung bleibt die alte stehen. */
  get value(): PlanPreviewWire | undefined {
    return this.#result.status === 'error' ? undefined : this.#result.value;
  }

  get loading(): boolean {
    return this.#result.status === 'loading';
  }

  /** Ob die Bewertung etwas sperrt, das das Speichern verhindert. */
  get blocking(): boolean {
    return this.value?.issues.some((issue) => issue.blocking) ?? false;
  }

  /** Fragt die Bewertung für die Planung an (entprellt); dieselbe Planung wie zuvor löst nichts aus. */
  request(client: ApiClient, plan: PlanPreviewRequest): void {
    const key = JSON.stringify(plan);
    if (key === this.#key) {
      return;
    }
    this.#key = key;
    clearTimeout(this.#timer);
    this.#timer = setTimeout(() => {
      this.#timer = undefined;
      void this.#result.run(() => client.planPreview(plan));
    }, PLAN_PREVIEW_DEBOUNCE_MS);
  }

  /** Verwirft die Anfrage und die Bewertung (der Editor wurde geschlossen). */
  reset(): void {
    clearTimeout(this.#timer);
    this.#timer = undefined;
    this.#key = '';
    this.#result.reset();
  }
}
