/** Maße, Zeiten und Schwellen der Animation „scratch“ (Rubbellose mit Silberschicht). */

/** Zeichenfläche der Silberschicht in Pixeln (wird per CSS auf die Kartengröße skaliert). */
export const SCRATCH_CANVAS_WIDTH = 320;
export const SCRATCH_CANVAS_HEIGHT = 220;
/** Ab diesem Anteil freigerubbelter Fläche gilt ein Los als aufgedeckt. */
export const SCRATCH_REVEAL_SHARE = 0.5;
/** Jeder n-te Bildpunkt (Alphawert) wird für die Messung der freien Fläche gelesen. */
export const SCRATCH_SAMPLE_STEP = 37;
/** Alphawert, unter dem ein Bildpunkt als frei gilt (von 255). */
export const SCRATCH_CLEAR_ALPHA = 128;
export const SCRATCH_CHANNELS = 4;
export const SCRATCH_ALPHA_OFFSET = 3;
/** Pinselbreite beim Rubbeln von Hand und mit der Münze. */
export const SCRATCH_BRUSH = 34;
export const SCRATCH_COIN_BRUSH = 46;
/** Mindestabstand zwischen zwei Messungen beim Ziehen (ms). */
export const SCRATCH_CHECK_MS = 150;

/** Münze: Zickzack in Reihen über das Los. */
export const SCRATCH_COIN_ROWS = 6;
export const SCRATCH_COIN_MARGIN = 14;
export const SCRATCH_COIN_ROW_STEP = 38;
export const SCRATCH_COIN_TRAIL = 0.15;
export const SCRATCH_COIN_WOBBLE = 6;
export const SCRATCH_COIN_WOBBLE_FREQUENCY = 9;
export const SCRATCH_COIN_START_MS = 250;
export const SCRATCH_COIN_MS = 1100;
export const SCRATCH_HOLD_MS = 300;

/** Silberschicht: Farbverlauf, Kopfstreifen mit dem Namen, Beschriftung. */
export const SCRATCH_FOIL_STOPS = [
  [0, '#d7dbe0'],
  [0.5, '#f4f6f8'],
  [1, '#aab1ba'],
] as const;
export const SCRATCH_FOIL_INK = '#4a525c';
export const SCRATCH_FOIL_HEAD = 54;
export const SCRATCH_FOIL_NAME_Y = 40;
export const SCRATCH_FOIL_HINT_Y = 140;
export const SCRATCH_FOIL_NAME_FONT = '900 34px Roboto, sans-serif';
export const SCRATCH_FOIL_HINT_FONT = '900 38px Roboto, sans-serif';
export const SCRATCH_FOIL_WHITE = '#ffffff';
export const SCRATCH_GOLD = '#f5c542';
/** Zwei: Hälfte der Breite (Mitte) und gerade/ungerade Reihen der Münze. */
export const SCRATCH_PAIR = 2;
