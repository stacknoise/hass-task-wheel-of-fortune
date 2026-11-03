/**
 * Meldet ein Element an, sofern der Name noch frei ist. Wird das Bundle ein zweites Mal ausgewertet
 * (etwa weil Home Assistant das Modul erneut lädt), bleibt die erste Anmeldung bestehen, statt dass
 * `customElements.define` einen Fehler wirft.
 */
export function defineOnce(tag: string, constructor: CustomElementConstructor): void {
  if (!customElements.get(tag)) {
    customElements.define(tag, constructor);
  }
}
