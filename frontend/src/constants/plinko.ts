/** Maße und Zeiten der Animation „plinko“ (Stiftefeld). Längen in Einheiten des SVG-Koordinatensystems. */

export const PLINKO_VIEW_WIDTH = 400;
export const PLINKO_VIEW_HEIGHT = 460;
export const PLINKO_HALF = 0.5;
/** Das Stiftmuster wiederholt sich alle zwei Reihen (versetzt). */
export const PLINKO_ROW_PERIOD = 2;
/** Faktor, der die Parabel s(1-s) auf Höhe 1 normiert. */
export const PLINKO_ARC_SHAPE = 4;

export const PLINKO_BOARD_LEFT = 10;
export const PLINKO_BOARD_RIGHT = 390;
export const PLINKO_PEG_SPACING = 38;
export const PLINKO_ROWS = 10;
export const PLINKO_ROW_SPACING = 30;
export const PLINKO_FIRST_ROW_Y = 50;
export const PLINKO_PEG_RADIUS = 4.5;
/** Rundungsspielraum beim Zählen der Stifte je Reihe. */
export const PLINKO_EDGE_TOLERANCE = 0.1;

export const PLINKO_BIN_TOP = 350;
export const PLINKO_BIN_HEIGHT = 90;
/** Abstand des Landepunkts zu den Fachwänden, höchstens ein Viertel der Fachbreite. */
export const PLINKO_BIN_MARGIN = 12;
export const PLINKO_BIN_MARGIN_SHARE = 0.25;
export const PLINKO_LANDING_OFFSET = 20;
export const PLINKO_SEPARATOR_WIDTH = 4;
export const PLINKO_SEPARATOR_RISE = 6;
export const PLINKO_NAME_Y = 28;
/** Ab dieser Fachbreite stehen Prozent, ab der größeren auch der Name im Fach. */
export const PLINKO_MIN_NAME_WIDTH = 56;

export const PLINKO_BALL_RADIUS = 9;
export const PLINKO_BALL_STROKE = 2.5;
export const PLINKO_BALL_START_Y = 18;
export const PLINKO_PATH_START_Y = 14;
export const PLINKO_START_JITTER = 6;
/** Wie hoch über dem Stift die Kugel beim Treffer steht. */
export const PLINKO_HIT_OFFSET = 14;
export const PLINKO_PEG_ARC = 10;
export const PLINKO_END_ARC = 28;

export const PLINKO_FIRST_MS = 550;
export const PLINKO_LAST_MS = 750;
export const PLINKO_STEP_MIN_MS = 300;
export const PLINKO_STEP_MAX_MS = 360;
export const PLINKO_GLOW_MS = 300;
export const PLINKO_BOUNCE_MS = 500;
export const PLINKO_BOUNCE_HEIGHT = 16;
export const PLINKO_BOUNCE_COUNT = 3;
export const PLINKO_WIN_CLASS = 'win';
