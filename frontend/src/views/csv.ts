import {
  CSV_BOM,
  CSV_FORMULA_ESCAPE,
  CSV_FORMULA_PREFIXES,
  CSV_NEWLINE,
  CSV_QUOTE,
  CSV_SEPARATOR,
} from '../constants/index.ts';

/**
 * Ein Feld für eine CSV-Datei. Beginnt der Text mit einem Zeichen, mit dem Tabellenprogramme eine
 * Formel einleiten, wird ihm ein Hochkomma vorangestellt; danach wird immer in Anführungszeichen gesetzt.
 */
export function csvCell(value: string): string {
  const safe = CSV_FORMULA_PREFIXES.some((prefix) => value.startsWith(prefix))
    ? `${CSV_FORMULA_ESCAPE}${value}`
    : value;
  return `${CSV_QUOTE}${safe.replaceAll(CSV_QUOTE, CSV_QUOTE + CSV_QUOTE)}${CSV_QUOTE}`;
}

/** Die Datei als Text (mit Byte-Order-Mark, damit Excel UTF-8 erkennt). */
export function buildCsv(rows: readonly (readonly string[])[]): string {
  return CSV_BOM + rows.map((row) => row.map(csvCell).join(CSV_SEPARATOR)).join(CSV_NEWLINE);
}
