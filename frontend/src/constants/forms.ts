/** Konstanten der Formulare (Konfiguration von Personen, Aufgaben, Zeitplänen). Grenzen spiegeln `const/limits.py`. */

export const EVENT_CHANGE = 'tw-change';

export const FORM_TAGS = {
  field: 'tw-field',
  toggle: 'tw-toggle',
  stepper: 'tw-stepper',
  chipSelect: 'tw-chip-select',
  segmented: 'tw-segmented',
  select: 'tw-select',
  weekPreview: 'tw-week-preview',
  absenceEditor: 'tw-absence-editor',
  entryEditor: 'tw-entry-editor',
  planPreview: 'tw-plan-preview',
} as const;

export const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;
export type Weekday = (typeof WEEKDAYS)[number];
export const WEEKDAY_COUNT = WEEKDAYS.length;
export const DATE_LENGTH = 10;

/** Standardfarbe neuer Personen (wie `DEFAULT_PERSON_COLOR` im Backend). */
export const DEFAULT_PERSON_COLOR = '#4f8cff';
/** Spalten der Farbauswahl; die Farben füllen genau zwei Reihen. */
export const PERSON_COLOR_COLUMNS = 8;
/** Nach Farbton sortiert (Rot bis Weinrot), zuletzt Grau. */
export const PERSON_COLORS = [
  '#e03131',
  '#e8590c',
  '#9c6644',
  '#f08c00',
  '#b08900',
  '#74a30b',
  '#2f9e44',
  '#099268',
  '#0c8599',
  '#4f8cff',
  '#4263eb',
  '#7048e8',
  '#ae3ec9',
  '#d6336c',
  '#a61e4d',
  '#5c7080',
] as const;

export const FORM_LIMITS = {
  nameMax: 60,
  notifyMax: 255,
  points: { min: 1, max: 100 },
  intervalEvery: { min: 1, max: 1000 },
  runDays: { min: 1, max: 365 },
  minCount: { min: 1, max: 1000 },
  rhythmCycle: { min: 1, max: 8 },
  recurrenceInterval: { min: 1, max: 52 },
} as const;

export const ABSENCE_KINDS = ['once', 'weekly_days', 'week_rhythm', 'recurring'] as const;
export type AbsenceKind = (typeof ABSENCE_KINDS)[number];

/** Einheiten des Intervalls zwischen zwei Auslosungen (wie `IntervalUnit` im Backend). */
export const INTERVAL_UNITS = ['hour', 'day', 'week'] as const;
export type IntervalUnit = (typeof INTERVAL_UNITS)[number];

/** Wie eine Aufgabe im Zeitplan vorkommt: mindestens n× je Lauf oder in jeder Auslosung. */
export const ENTRY_MODES = ['min_count', 'every_draw'] as const;
export type EntryMode = (typeof ENTRY_MODES)[number];

/** Auslösung eines Zeitplans: von selbst zu jedem Termin oder per Klick. */
export const SCHEDULE_MODES = ['automatic', 'manual'] as const;
export type ScheduleMode = (typeof SCHEDULE_MODES)[number];

/** Länge einer Intervall-Einheit in Stunden (wie `INTERVAL_UNIT_HOURS` im Backend: Tag = 24, Woche = 168). */
const HOURS_PER_DAY = 24;
const HOURS_PER_WEEK = 168;
export const INTERVAL_UNIT_HOURS: Readonly<Record<IntervalUnit, number>> = {
  hour: 1,
  day: HOURS_PER_DAY,
  week: HOURS_PER_WEEK,
};
/** Perioden zählt das Backend ab 0, angezeigt wird ab 1 (Periode #1). */
export const PERIOD_NUMBER_OFFSET = 1;
export const DEFAULT_INTERVAL_EVERY = 7;
export const DEFAULT_RUN_DAYS = 30;
export const DEFAULT_MIN_COUNT = 1;
/** Der erste Termin eines neuen Zeitplans liegt so viele Stunden nach „jetzt“, zur vollen Stunde. */
export const DEFAULT_START_OFFSET_HOURS = 1;
export const MS_PER_HOUR = 3_600_000;

/** Sichtbare Zeilen im Zeitplan-Editor, danach scrollt der Bereich. */
export const ENTRY_ROWS_VISIBLE = 6;
export const TRACK_ROWS_VISIBLE = 4;
/** Wartezeit nach der letzten Eingabe, bevor die Vorschau des Plans neu rechnet. */
export const PLAN_PREVIEW_DEBOUNCE_MS = 300;
/** Blasse Punkte am Ende der Spur zeigen den Anfang des nächsten Laufs: mindestens 2, sonst ein Drittel der Auslosungen. */
export const TRACK_GHOST_MIN = 2;
export const TRACK_GHOST_DIVISOR = 3;

export const LOADS = ['full', 'half', 'paused'] as const;
export type Load = (typeof LOADS)[number];

export const DEFAULT_LOAD: Load = 'full';
/** Mindest-Belastbarkeit einer Aufgabe, aufsteigend; `paused` heißt „egal“. */
export const MIN_LOADS = ['paused', 'half', 'full'] as const satisfies readonly Load[];
export const DEFAULT_MIN_LOAD: Load = 'paused';
export const DEFAULT_TASK_POINTS = 1;
export const DEFAULT_RHYTHM_CYCLE = 2;
export const DEFAULT_RECURRENCE_INTERVAL = 2;
/** Standard-Wochentag einer wiederkehrenden Abwesenheit: Mittwoch. */
export const DEFAULT_RECURRING_ABSENCE_WEEKDAYS: readonly Weekday[] = [2];
export const DEFAULT_RHYTHM_CHANGE_DAY: Weekday = 4;
export const DEFAULT_ABSENT_WEEKDAYS: readonly Weekday[] = [5, 6];

export const NOTIFY_PREFIX = 'notify.';
export const NOTIFY_DOMAIN = 'notify';
/** Dienst, der zu den Entitäten führt und selbst kein Ziel ist. */
export const NOTIFY_SEND_MESSAGE = 'send_message';
export const SERVICE_DRAW = 'task_wheel.draw';
export const EVENT_DRAWN_NAME = 'task_wheel_drawn';
