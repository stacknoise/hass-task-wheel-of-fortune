import { html } from 'lit';
import type { TemplateResult } from 'lit';

/** Die Fehlermeldung der Auslosung mit dem Fehlercode. */
export function drawFailure(message: string, codeLabel: string, code: unknown): TemplateResult {
  return html`<p class="error" role="alert">${message} (${codeLabel}: ${code})</p>`;
}
