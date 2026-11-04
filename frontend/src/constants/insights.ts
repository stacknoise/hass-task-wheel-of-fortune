/** Konstanten der Ansichten Übersicht, Historie und Statistik (AP-17). Keine Logik. */

import { WS_PREFIX } from './api.ts';

export const WS_HISTORY_LIST = `${WS_PREFIX}history/list`;
export const WS_STATISTICS_GET = `${WS_PREFIX}statistics/get`;
export const WS_ASSIGNMENT_COMPLETE = `${WS_PREFIX}assignment/complete`;
export const WS_ASSIGNMENT_SWAP = `${WS_PREFIX}assignment/swap`;
export const WS_ASSIGNMENT_SKIP = `${WS_PREFIX}assignment/skip`;

export const FIELD_PERSON_ID = 'person_id';
export const FIELD_OFFSET = 'offset';
export const FIELD_LIMIT = 'limit';
export const FIELD_MONTHS = 'months';
export const FIELD_WEEKS = 'weeks';
export const FIELD_ASSIGNMENT_ID = 'assignment_id';
export const FIELD_TO_PERSON_ID = 'to_person_id';

export const STATUS = {
  open: 'open',
  onTime: 'on_time',
  late: 'late',
  swapped: 'swapped',
  missed: 'missed',
  skipped: 'skipped',
} as const;
export type AssignmentStatus = (typeof STATUS)[keyof typeof STATUS];

/** Status, in denen eine Zuteilung noch zu erledigen ist. */
export const PENDING_STATUSES: readonly AssignmentStatus[] = [STATUS.open, STATUS.swapped];
/** Status, in denen sie erledigt wurde. */
export const DONE_STATUSES: readonly AssignmentStatus[] = [STATUS.onTime, STATUS.late];

export type Tone = 'success' | 'warning' | 'error' | 'info' | 'neutral';
export const STATUS_TONES: Readonly<Record<AssignmentStatus, Tone>> = {
  open: 'info',
  on_time: 'success',
  late: 'warning',
  swapped: 'neutral',
  missed: 'error',
  skipped: 'warning',
};

export const FILTER_ALL = 'all';
export const LOAD_PAUSED = 'paused';
export const HALF = 0.5;
export const PAIR = 2;

export const HISTORY_PAGE_SIZE = 20;
/** Größte Seite, die das Backend liefert. */
export const HISTORY_PAGE_SIZE_MAX = 200;
export const ACTIVITY_COUNT = 5;
export const OVERVIEW_MONTHS = 1;
export const OVERVIEW_WEEKS = 1;

/** Attribut, mit dem eine Ansicht meldet, dass sie gerade neu lädt. */
export const ATTRIBUTE_BUSY = 'aria-busy';
/** Deckkraft veralteter Zahlen, während neue geladen werden. */
export const BUSY_OPACITY = 0.6;

/** Höchsthöhe der Scrollbox für Soll und Ist (je Zeitplan aufklappbar), in Zeilenhöhen (em). */
export const GOALS_SCROLL_MAX_HEIGHT = '28em';

export const STATISTICS_WEEKS = 8;
export const STATISTICS_RANGES = [
  { id: 'month', months: 1 },
  { id: 'quarter', months: 3 },
  { id: 'year', months: 12 },
] as const;
export type StatisticsRangeId = (typeof STATISTICS_RANGES)[number]['id'];
export const DEFAULT_RANGE: StatisticsRangeId = 'month';

/** Wartezeit, bis die Adresse einer heruntergeladenen Datei freigegeben wird. */
export const REVOKE_DELAY_MS = 1000;
export const EXPORT_PAGE_SIZE = 200;
export const EXPORT_MAX_PAGES = 50;
export const CSV_SEPARATOR = ';';
/** Trenner mehrerer Räume innerhalb einer CSV-Zelle. */
export const ROOM_SEPARATOR = ', ';
export const CSV_QUOTE = '"';
export const CSV_NEWLINE = '\r\n';
export const CSV_FORMULA_PREFIXES: readonly string[] = ['=', '+', '-', '@', '\t', '\r'];
export const CSV_FORMULA_ESCAPE = "'";
export const CSV_BOM = '\uFEFF';
export const CSV_FILE_NAME = 'task-wheel-history.csv';
export const CSV_MIME = 'text/csv;charset=utf-8';

/** Maße des Liniendiagramms (viewBox) der Erledigungsquote je Woche. */
export const CHART = {
  width: 400,
  height: 180,
  left: 40,
  right: 392,
  top: 16,
  bottom: 140,
  labelY: 162,
  ticks: [0, HALF, 1],
} as const;

/** Anzahl Farbstufen der Matrix (Aufgabe mal Person). */
export const HEAT_LEVELS = 5;

export const EVENT_CHIP_SELECT = 'tw-chip-select';
