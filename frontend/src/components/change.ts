import { EVENT_CHANGE } from '../constants/index.ts';

// Der Typparameter legt den Typ des Werts fest, den Sender und Empfänger verabreden.
/* eslint-disable @typescript-eslint/no-unnecessary-type-parameters */
/** Meldet einen neuen Wert; Formularbausteine kennen nur Eigenschaften und dieses Ereignis. */
export function emitChange<T>(host: HTMLElement, detail: T): void {
  host.dispatchEvent(new CustomEvent<T>(EVENT_CHANGE, { detail, bubbles: true, composed: true }));
}

/** Der Wert aus einem `tw-change`-Ereignis. */
export function changeDetail<T>(event: Event): T {
  return (event as CustomEvent<T>).detail;
}

/** Listener für `tw-change`: hält das Ereignis an (der Baustein meldet danach selbst) und reicht den Wert weiter. */
export function onChange<T>(apply: (value: T) => void): (event: Event) => void {
  return (event) => {
    event.stopPropagation();
    apply(changeDetail<T>(event));
  };
}
/* eslint-enable @typescript-eslint/no-unnecessary-type-parameters */
