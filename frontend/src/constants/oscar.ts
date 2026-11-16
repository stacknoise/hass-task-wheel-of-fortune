/** Zeiten der Animation „oscar“ (Verleihung: Vorhang, Scheinwerfer, Umschlag, Verkündung). */

export const OSCAR_CURTAIN_MS = 450;
/** Verweildauer des Scheinwerfers je Nominiertem, bei vielen Personen kürzer (Gesamtzeit begrenzt). */
export const OSCAR_NOMINEE_TOTAL_MS = 900;
export const OSCAR_NOMINEE_MIN_MS = 160;
export const OSCAR_ENVELOPE_MS = 350;
export const OSCAR_FLAP_MS = 300;
export const OSCAR_CARD_MS = 350;
export const OSCAR_PAUSE_MS = 350;
/** Wie lange die Verkündung mit Konfetti steht, bevor die Animation endet. */
export const OSCAR_HOLD_MS = 450;
/** Abdunkelung der Nominierten, die nicht gewonnen haben (CSS-Deckkraft). */
export const OSCAR_LOSER_OPACITY = 0.25;

/**
 * Namensleiste: Fensterbreite zwischen den geöffneten Vorhängen und Größe der Nominierten (in `cqw` der
 * Bühne). Passen nicht alle hinein, scrollt die Leiste und hält die Hervorgehobenen mittig.
 */
export const OSCAR_WINDOW_INSET_PCT = 12;
export const OSCAR_WINDOW_CQW = 100 - 2 * OSCAR_WINDOW_INSET_PCT;
export const OSCAR_NOMINEE_WIDTH_CQW = 22;
export const OSCAR_NOMINEE_GAP_CQW = 3;
export const OSCAR_NOMINEE_STEP_CQW = OSCAR_NOMINEE_WIDTH_CQW + OSCAR_NOMINEE_GAP_CQW;
/** Dauer, in der die Leiste zur nächsten Person gleitet (kürzer als die Verweildauer). */
export const OSCAR_SCROLL_MS = 140;
/** Hälfte, für die Mitte von Fenster, Leiste und Lücke. */
export const OSCAR_HALF = 0.5;
export const OSCAR_WINDOW_HALF_CQW = OSCAR_WINDOW_CQW * OSCAR_HALF;
export const OSCAR_NOMINEE_HALF_GAP_CQW = OSCAR_NOMINEE_GAP_CQW * OSCAR_HALF;
