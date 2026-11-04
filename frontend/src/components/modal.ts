import { css, unsafeCSS } from 'lit';

import { COLOR_SCRIM, EVENT_CANCEL } from '../constants/index.ts';
import { LocalizedElement } from './localized.ts';

/** Gemeinsame Gestalt der modalen Fenster: das `<dialog>` selbst, sein Hintergrund und der Standardrand. */
export const modalStyles = css`
  dialog {
    padding: 0;
    border: 1px solid var(--tw-color-divider);
    border-radius: var(--tw-radius);
    background: var(--tw-color-surface);
    color: var(--tw-color-text);
  }
  dialog::backdrop {
    background: ${unsafeCSS(COLOR_SCRIM)};
  }
`;

/**
 * Basis der modalen Fenster. Das native `<dialog>` übernimmt, was von Hand schwer ist: Fokus ins
 * Fenster, Fokusfalle, inerter Hintergrund, Escape und die Rückgabe des Fokus beim Schließen.
 * Escape meldet `tw-cancel`; das Schließen übernimmt der Aufrufer, indem er das Element entfernt.
 */
export abstract class ModalElement extends LocalizedElement {
  protected override firstUpdated(): void {
    this.renderRoot.querySelector('dialog')?.showModal();
  }

  override disconnectedCallback(): void {
    this.renderRoot.querySelector('dialog')?.close();
    super.disconnectedCallback();
  }

  /** Escape: das Fenster bleibt, bis der Aufrufer es entfernt. */
  protected readonly onCancel = (event: Event): void => {
    event.preventDefault();
    this.dispatchEvent(new CustomEvent(EVENT_CANCEL, { bubbles: true, composed: true }));
  };
}
