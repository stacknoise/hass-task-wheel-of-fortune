/**
 * Erzeugt ein registriertes Custom Element und prüft seinen Typ zur Laufzeit. Das ersetzt den
 * Cast `createElement(...) as Klasse`, den typescript-eslint (`no-unsafe-class-instance-assignment`)
 * ablehnt, und schlägt bei einem nicht registrierten Tag mit einer klaren Meldung fehl.
 */
export function createElementOf<T extends HTMLElement>(tag: string, type: abstract new () => T): T {
  const element = document.createElement(tag);
  if (!(element instanceof type)) {
    throw new TypeError(`<${tag}> ist kein ${type.name}`);
  }
  return element;
}
