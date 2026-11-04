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
  timeline: 'tw-timeline',
  absenceEditor: 'tw-absence-editor',
  frequencyEditor: 'tw-frequency-editor',
  triggerEditor: 'tw-trigger-editor',
} as const;

export const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6] as const;
export type Weekday = (typeof WEEKDAYS)[number];
export const WEEKDAY_COUNT = WEEKDAYS.length;
export const MS_PER_DAY = 86_400_000;
export const TIME_INPUT_LENGTH = 5;
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
  dueDays: { min: 1, max: 365 },
  periodCount: { min: 1, max: 50 },
  intervalDays: { min: 1, max: 365 },
  rhythmCycle: { min: 1, max: 8 },
  everyNWeeks: { min: 1, max: 52 },
  remindDays: { min: 1, max: 365 },
} as const;

export const ABSENCE_KINDS = ['once', 'weekly_days', 'week_rhythm'] as const;
export type AbsenceKind = (typeof ABSENCE_KINDS)[number];

export const FREQUENCY_KINDS = ['every_round', 'max_per_period', 'interval'] as const;
export type FrequencyKind = (typeof FREQUENCY_KINDS)[number];

export const PERIODS = ['day', 'week', 'month'] as const;
export type Period = (typeof PERIODS)[number];

export const TRIGGER_KINDS = ['recurring', 'once', 'manual'] as const;
export type TriggerKind = (typeof TRIGGER_KINDS)[number];

export const AFTER_ONCE = ['keep_manual', 'archive', 'delete'] as const;
export type AfterOnce = (typeof AFTER_ONCE)[number];

export const LOADS = ['full', 'half', 'paused'] as const;
export type Load = (typeof LOADS)[number];

export const DEFAULT_LOAD: Load = 'full';
/** Mindest-Belastbarkeit einer Aufgabe, aufsteigend; `paused` heißt „egal“. */
export const MIN_LOADS = ['paused', 'half', 'full'] as const satisfies readonly Load[];
export const DEFAULT_MIN_LOAD: Load = 'paused';
export const DEFAULT_TIME = '18:00';
export const DEFAULT_TASK_POINTS = 1;
export const DEFAULT_TASK_DUE_DAYS = 7;
export const DEFAULT_INTERVAL_DAYS = 7;
export const DEFAULT_PERIOD_COUNT = 1;
export const DEFAULT_RHYTHM_CYCLE = 2;
export const DEFAULT_RHYTHM_CHANGE_DAY: Weekday = 4;
export const DEFAULT_ABSENT_WEEKDAYS: readonly Weekday[] = [5, 6];
export const DEFAULT_RECURRING_WEEKDAYS: readonly Weekday[] = [0];
export const DEFAULT_REMIND_DAYS = 7;
export const DEFAULT_EVERY_N_WEEKS = 1;

/** Zeitstrahl: höchstens so viele Tageszahlen an der Skala, in diesen Schrittweiten. */
export const TIMELINE_SCALE_LABELS = 8;
/** Bis zu dieser Zahl von Tagen trennen feine Linien die einzelnen Tage am Balken. */
export const TIMELINE_GRID_MAX = 60;
/** Ein Tag nimmt eine Zelle ein; Marken und Zahlen stehen in ihrer Mitte bzw. mit halbem Schrittabstand. */
export const TIMELINE_HALF = 0.5;
export const TIMELINE_SCALE_STEPS = [1, 2, 5, 10, 20, 50, 100, 200, 500] as const;
export const NOTIFY_PREFIX = 'notify.';
export const NOTIFY_DOMAIN = 'notify';
/** Dienst, der zu den Entitäten führt und selbst kein Ziel ist. */
export const NOTIFY_SEND_MESSAGE = 'send_message';
export const ATTR_FRIENDLY_NAME = 'friendly_name';
export const SERVICE_DRAW = 'task_wheel.draw';
export const EVENT_DRAWN_NAME = 'task_wheel_drawn';
