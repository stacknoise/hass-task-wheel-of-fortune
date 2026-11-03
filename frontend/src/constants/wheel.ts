/** Maße, Zeiten und Schwellen des Glücksrads. Winkel in Grad, im Uhrzeigersinn ab oben. */

export const WHEEL_VIEWBOX = 360;
export const WHEEL_CENTER = 180;
export const WHEEL_RIM_RADIUS = 176;
export const WHEEL_RADIUS = 168;
export const WHEEL_NAME_RADIUS = 112;
export const WHEEL_CHANCE_RADIUS = 86;
export const WHEEL_POINTER_HALF_WIDTH = 16;
export const WHEEL_POINTER_DEPTH = 36;
export const WHEEL_SEGMENT_GAP = 3;

export const FULL_CIRCLE = 360;
export const HALF_CIRCLE = 180;
export const PERCENT = 100;
/** Ab diesem Winkel eines Segments wird der Bogen als „groß“ gezeichnet. */
export const LARGE_ARC_FROM = HALF_CIRCLE;
/** Chance, ab der ein Segment seinen Namen trägt; kleinere bleiben unbeschriftet. */
export const MIN_LABEL_CHANCE = 0.07;
/** Ab dieser Chance ist das Rad ein einziges Segment (Vollkreis). */
export const FULL_CHANCE = 0.999;

export const SPIN_DURATION_MS = 5000;
export const SPIN_SETTLE_MS = 300;
export const SPIN_EXTRA_TURNS = 5;
export const SPIN_EASING = 'cubic-bezier(0.17, 0.67, 0.12, 1)';
/** Wo im Segment das Rad ausläuft (Anteil der Segmentbreite von seinem Anfang). */
export const LANDING_FRACTION = 0.5;

export const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
export const EVENT_WHEEL_STOP = 'tw-wheel-stop';

export const CONFETTI_COUNT = 36;
export const CONFETTI_COLUMN_STEP = 29;
export const CONFETTI_DELAY_STEP_MS = 37;
export const CONFETTI_DELAY_CYCLE = 17;
export const CONFETTI_DURATION_MS = 2600;
export const CONFETTI_DURATION_SPREAD_MS = 40;
export const CONFETTI_DURATION_CYCLE = 11;
export const CONFETTI_PALETTE = ['#f5c542', '#4fa6e8', '#e8564f', '#58c47c', '#b07be8'] as const;

export const FALLBACK_COLOR = '#727272';
export const EMPTY_TEXT = '';
export const PATH_DECIMALS = 2;
