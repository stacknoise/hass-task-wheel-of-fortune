/** Maße und Zeiten der Animation „spotlight“ (Scheinwerfer über einer Treemap aus Kacheln). */

/** Seitenverhältnis der Fläche; die Treemap wird in diesen Einheiten berechnet. */
export const SPOTLIGHT_WIDTH = 4;
export const SPOTLIGHT_HEIGHT = 3;

/** Anzahl der Sprünge des Scheinwerfers, der letzte landet auf dem Gewinner. */
export const SPOTLIGHT_STEPS = 26;
/** Verweildauer auf einer Kachel: am Anfang kurz, am Ende lang (kubisch). */
export const SPOTLIGHT_MIN_DELAY_MS = 70;
export const SPOTLIGHT_DELAY_SPAN_MS = 520;
export const SPOTLIGHT_DELAY_POWER = 3;
/** Wie lange der Scheinwerfer nach der Landung noch steht, bevor die Animation endet. */
export const SPOTLIGHT_HOLD_MS = 900;

export const SPOTLIGHT_FALLBACK_COLOR = 'var(--tw-color-neutral)';
/** Ziel der Teilung der Treemap: die Hälfte der Chance je Seite. */
export const SPOTLIGHT_SPLIT_AT = 0.5;
