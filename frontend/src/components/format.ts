import { PERCENT } from '../constants/index.ts';

/** Eine Zahl als Text für Attribute und Pfade. */
export function numberText(value: number): string {
  return String(value);
}

/** Eine Chance (0 bis 1) als ganze Prozent. */
export function percentText(chance: number): string {
  return `${numberText(Math.round(chance * PERCENT))} %`;
}
