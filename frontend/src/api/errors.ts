/** Fehler der WebSocket-API: Home Assistant liefert `{ code, message }`; bei Prüffehlern ist `message` `Feld: Schlüssel`. */

export interface ApiFailure {
  readonly code: string;
  /** Pfad des fehlerhaften Felds (`trigger.weekdays`); leer, wenn kein Feld gemeint ist. */
  readonly field: string;
}

export const UNKNOWN_CODE = 'unknown';
const FIELD_SEPARATOR = ': ';

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === 'object' && value !== null;
}

/** Zerlegt einen abgelehnten Aufruf in Schlüssel und Feld; alles Unbekannte ergibt `unknown`. */
export function parseFailure(error: unknown): ApiFailure {
  if (!isRecord(error) || typeof error['code'] !== 'string') {
    return { code: UNKNOWN_CODE, field: '' };
  }
  const message = typeof error['message'] === 'string' ? error['message'] : '';
  const cut = message.indexOf(FIELD_SEPARATOR);
  return { code: error['code'], field: cut > 0 ? message.slice(0, cut) : '' };
}

/** Gehört der Fehler zu einem der Felder (genau oder als Unterpfad)? */
export function failureFor(
  failure: ApiFailure | undefined,
  ...fields: readonly string[]
): string | undefined {
  const own = failure?.field ?? '';
  const hit = fields.some((field) => own === field || own.startsWith(`${field}.`));
  return hit ? failure?.code : undefined;
}
