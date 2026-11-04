/** Phasen einer manuellen Auslosung (Zustandsautomat der `DrawSession`). */
export const DRAW_PHASE = {
  choose: 'choose',
  busy: 'busy',
  ready: 'ready',
  spinning: 'spinning',
  revealed: 'revealed',
  done: 'done',
  error: 'error',
} as const;

export type DrawPhase = (typeof DRAW_PHASE)[keyof typeof DRAW_PHASE];

/** Fehlercode, wenn die Antwort des Backends keinen nennt. */
export const DRAW_UNKNOWN_ERROR = 'unknown';
