import type { DecisionExchange, DecisionRecord, DecisionTask } from '../api/index.ts';
import {
  DECISION_KINDS,
  DECISION_OUTCOMES,
  FILTER_ALL,
  REASON_PREFIX,
  WARNING_REASONS,
} from '../constants/index.ts';
import type { DecisionOutcome, Tone } from '../constants/index.ts';
import { formatPercent } from '../i18n/format.ts';
import { hasText, translate } from '../i18n/index.ts';
import type { TextKey, TextParams } from '../i18n/index.ts';

/** Eine Zeile unter einer Aufgabe: Person, Marke und Begründung. */
export interface CandidateLine {
  readonly personId: string;
  readonly name: string;
  readonly tone: Tone;
  readonly pill: string;
  readonly detail: string;
}

type Text = (key: TextKey, params?: TextParams) => string;

/** Ergebnis einer Aufgabe: zugeteilt oder unvergeben. */
export function outcomeOf(task: DecisionTask): DecisionOutcome {
  return task.winner_id === null ? DECISION_OUTCOMES.unassigned : DECISION_OUTCOMES.assigned;
}

/** Die Aufgaben des Eintrags, die zum Ergebnisfilter passen (`all` lässt alle durch). */
export function tasksMatching(record: DecisionRecord, filter: string): readonly DecisionTask[] {
  return filter === FILTER_ALL
    ? record.tasks
    : record.tasks.filter((task) => outcomeOf(task) === filter);
}

/** Ob der Eintrag beim Ergebnisfilter erscheint: Tausch und Austausch immer, Auslosungen mit passender Aufgabe. */
export function showsRecord(record: DecisionRecord, filter: string): boolean {
  return record.kind !== DECISION_KINDS.draw || tasksMatching(record, filter).length > 0;
}

/** Anzahl zugeteilter und unvergebener Aufgaben einer Auslosung. */
export function counts(record: DecisionRecord): Readonly<Record<DecisionOutcome, number>> {
  const assigned = record.tasks.filter((task) => task.winner_id !== null).length;
  return { assigned, unassigned: record.tasks.length - assigned };
}

/** Name des Gewinners aus dem Rad der Aufgabe, falls vorhanden. */
export function winnerName(task: DecisionTask): string | undefined {
  return task.wheel.find((entry) => entry.person_id === task.winner_id)?.person_name;
}

/** Text zu einem Ausschlussgrund; Gründe ohne Übersetzung erscheinen unverändert. */
export function reasonText(reason: string, language: string): string {
  const key = `${REASON_PREFIX}${reason}`;
  return hasText(key) ? translate(key, language) : reason;
}

/** Zeilen einer Aufgabe: Gewinner zuerst, dann das übrige Rad, dann die Ausgeschlossenen. */
export function candidateLines(task: DecisionTask, language: string, text: Text): CandidateLine[] {
  const single = task.wheel.length === 1;
  const wheel = task.wheel.map((entry): CandidateLine => {
    const won = entry.person_id === task.winner_id;
    const chance = formatPercent(entry.chance, language);
    return {
      personId: entry.person_id,
      name: entry.person_name,
      tone: won ? 'success' : 'info',
      pill: text(won ? 'log.pill.winner' : 'log.pill.inWheel'),
      detail:
        won && single
          ? text('log.winnerDirect')
          : text(won ? 'log.winnerChance' : 'log.inWheel', { chance }),
    };
  });
  const excluded = task.excluded.map((entry): CandidateLine => ({
    personId: entry.person_id,
    name: entry.person_name,
    tone: WARNING_REASONS.includes(entry.reason) ? 'warning' : 'neutral',
    pill: text('log.pill.excluded'),
    detail: reasonText(entry.reason, language),
  }));
  const winnersFirst = [...wheel].sort(
    (a, b) => Number(b.tone === 'success') - Number(a.tone === 'success'),
  );
  return [...winnersFirst, ...excluded];
}

/** Satz zu einem Tausch zweier Personen oder zum Austausch einer Aufgabe durch einen Admin. */
export function exchangeText(exchange: DecisionExchange, text: Text): string {
  const params = {
    person: exchange.person_name ?? '',
    task: exchange.task_name,
    otherTask: exchange.other_task_name,
    otherPerson: exchange.other_person_name ?? '',
  };
  return text(exchange.person_name === null ? 'log.exchange' : 'log.swap', params);
}
