/** Maße und Zeiten der Animation „slot“ (Walze). Längen in Einheiten des SVG-Koordinatensystems. */

export const SLOT_VIEW_WIDTH = 360;
export const SLOT_VIEW_HEIGHT = 260;
export const SLOT_FRAME_RADIUS = 18;
export const SLOT_FRAME_STROKE = 4;
export const SLOT_REEL_X = 14;
export const SLOT_REEL_Y = 14;
export const SLOT_REEL_WIDTH = 332;
export const SLOT_REEL_HEIGHT = 232;
export const SLOT_REEL_RADIUS = 10;
export const SLOT_HALF = 0.5;

/** Höhe eines Umlaufs der Walze (alle Personen einmal); Zeilenhöhe = Chance mal Umlaufhöhe. */
export const SLOT_CYCLE_HEIGHT = 360;
/** Wie oft die Personen auf dem Streifen wiederholt werden. */
export const SLOT_CYCLES = 11;
export const SLOT_START_CYCLE = 1;
export const SLOT_TARGET_CYCLE = 9;
/** Wie weit der Streifen anfangs unter der Gewinnlinie steht (Anteil eines Umlaufs). */
export const SLOT_START_FRACTION = 0.35;
/** Abstand zum Rand des Gewinnersegments, in dem die Walze nie stehen bleibt (Anteil der Zeile). */
export const SLOT_EDGE_MARGIN = 0.08;
/** Zeilen unter dieser Höhe tragen keinen Text. */
export const SLOT_MIN_LABEL_HEIGHT = 22;
export const SLOT_LABEL_GAP = 8;

export const SLOT_RECOIL = 30;
export const SLOT_RECOIL_MS = 250;
export const SLOT_SPIN_MS = 5000;
export const SLOT_BRAKE_EXPONENT = 1.8;

export const SLOT_PAYLINE_WIDTH = 3;
export const SLOT_PAYLINE_ARROW = 12;
export const SLOT_CELL_GAP = 3;
export const SLOT_FADE_HEIGHT = 56;
export const SLOT_CLIP_ID = 'reel-clip';
export const SLOT_WIN_CLASS = 'win';
