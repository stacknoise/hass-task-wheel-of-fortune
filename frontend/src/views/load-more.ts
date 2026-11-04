import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import type { AsyncStatus } from '../state/index.ts';

/** Schaltfläche „Weitere laden“ unter einer seitenweise geladenen Liste. */
export function loadMore(
  label: string,
  hasMore: boolean,
  status: AsyncStatus,
  onClick: () => void,
): TemplateResult | typeof nothing {
  return hasMore
    ? html`<button type="button" class="action" ?disabled=${status === 'loading'} @click=${onClick}>
        ${label}
      </button>`
    : nothing;
}

/** Platzhalter einer seitenweise geladenen Liste, solange sie fehlt: Ladefehler oder „Wird geladen“. */
export function listPlaceholder(
  list: { readonly status: AsyncStatus; readonly items: readonly unknown[] | undefined },
  text: (key: 'common.loadError' | 'common.loading') => string,
): TemplateResult | undefined {
  if (list.status === 'error') {
    return html`<p class="error" role="alert">${text('common.loadError')}</p>`;
  }
  return list.items ? undefined : html`<p class="empty">${text('common.loading')}</p>`;
}
