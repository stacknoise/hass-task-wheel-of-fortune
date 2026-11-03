/** Maße, Zeiten und Physik der Lostrommel (Einheiten der Zeichenfläche; Zeit in ms, Geschwindigkeit je Sekunde). */

export const DRUM_VIEWBOX = 400;
export const DRUM_CENTER_X = 160;
export const DRUM_CENTER_Y = 160;
export const DRUM_RADIUS = 140;
/** Abstand der Kugeln zur Trommelwand. */
export const DRUM_WALL_INSET = 6;
/** Ablage („Gezogen“) und Ziel der Gewinnerkugel. */
export const DRUM_TRAY_X = 338;
export const DRUM_TRAY_Y = 334;
export const DRUM_TRAY_LEFT = 288;
export const DRUM_TRAY_TOP = 284;
export const DRUM_TRAY_SIZE = 108;
export const DRUM_TRAY_CORNER = 14;
export const DRUM_TRAY_DASH = '6 5';
export const DRUM_CHUTE_FROM = 215;
export const DRUM_CHUTE_WIDTH = 86;
/** Die Öffnung der Trommel liegt zwischen diesen Winkeln (Grad, von der x-Achse nach unten). */
export const DRUM_OPENING_FROM = 60;
export const DRUM_OPENING_TO = 30;
export const DRUM_WALL_WIDTH = 7;
export const DRUM_RIB_COUNT = 6;
export const DRUM_RIB_LENGTH = 124;
export const DRUM_RIB_WIDTH = 4;
export const DRUM_HUB_RADIUS = 9;

/** Je Person so viele Kugeln. */
export const DRUM_BALLS_PER_PERSON = 3;
/** Kugelradius = Faktor * Wurzel(Prozent), also Fläche proportional zur Chance. */
export const DRUM_RADIUS_FACTOR = 4.7;
export const DRUM_SPAWN_INSET = 8;
export const DRUM_WARMUP_STEPS = 400;
export const DRUM_WARMUP_SECONDS = 0.016;
export const DRUM_RUN_STEP_SECONDS = 0.033;

export const DRUM_GRAVITY = 1100;
export const DRUM_DAMPING = 0.997;
/** Elastizität an Wand und zwischen Kugeln (Faktor auf die Normalgeschwindigkeit). */
export const DRUM_BOUNCE = 1.5;
export const DRUM_KICK_RATE = 7;
export const DRUM_KICK_SPEED = 400;
export const DRUM_MIN_DISTANCE = 0.001;
export const DRUM_TAU = Math.PI * 2;
/** Winkelgeschwindigkeit der Trommel (rad/s) zu Beginn und am Ende des Wirbelns. */
export const DRUM_SPIN_FROM = 6.5;
export const DRUM_SPIN_DROP = 3.5;
/** Wie schnell die Trommel in die Ruhelage zurückdreht (je Sekunde). */
export const DRUM_REST_RATE = 3;

/** Dauer der Phasen: Wirbeln, Lenken zur Öffnung, Rollen in die Ablage, Aufpoppen. */
export const DRUM_PHASE_MS = [3400, 1000, 900, 400] as const;
export const DRUM_EXIT_INSET = 2;
export const DRUM_LANDED_DISTANCE = 6;
export const DRUM_SUBSTEPS = 2;
export const DRUM_QUARTER_TURN = Math.PI / 2;
export const DRUM_POP_SCALE = 0.25;

/** Kugelbeschriftung und Glanz im Verhältnis zum Radius. */
export const DRUM_BALL_STROKE = 2.5;
export const DRUM_SHINE_OFFSET = 0.35;
export const DRUM_SHINE_SIZE = 0.28;
export const DRUM_SHINE_OPACITY = 0.35;
export const DRUM_LETTER_SIZE = 0.95;
export const DRUM_LETTER_DROP = 0.34;

/** Legende unter der Trommel: Zeilen je Spalte, Abstand und Platz. */
export const DRUM_LEGEND_TOP = 322;
export const DRUM_LEGEND_ROW = 18;
export const DRUM_LEGEND_ROWS = 4;
export const DRUM_LEGEND_WIDTH = 280;
export const DRUM_LEGEND_DOT = 5;
export const DRUM_LEGEND_TEXT_GAP = 14;
export const DRUM_FALLBACK_LETTER = '?';
