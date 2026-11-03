import { LitElement } from 'lit';

import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { emitChange } from './change.ts';

/** Basis der Bausteine mit Texten: Sprache als Eigenschaft, `text()` zum Übersetzen. */
export abstract class LocalizedElement extends LitElement {
  static override properties = { language: { type: String } };

  declare language: string;

  constructor() {
    super();
    this.language = '';
  }

  protected text(key: TextKey): string {
    return translate(key, this.language);
  }

  /** Ersetzt den Eintrag an `index` durch den um `patch` ergänzten und meldet die neue Liste. */
  protected replaceAt<T extends object>(
    list: readonly T[],
    index: number,
    patch: Partial<T>,
  ): void {
    emitChange(
      this,
      list.map((entry, position) => (position === index ? { ...entry, ...patch } : entry)),
    );
  }
}
