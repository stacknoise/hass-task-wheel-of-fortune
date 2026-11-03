import {
  FULL_CHANCE,
  FULL_CIRCLE,
  HALF_CIRCLE,
  LANDING_FRACTION,
  LARGE_ARC_FROM,
  PATH_DECIMALS,
  SPIN_EXTRA_TURNS,
  WHEEL_CENTER,
  WHEEL_RADIUS,
} from '../constants/index.ts';
import { numberText } from './format.ts';

/** Ein Segment des Rads; die Größe ist die Chance (muss nicht auf 1 summieren). */
export interface WheelSegment {
  readonly id: string;
  readonly label: string;
  readonly color: string;
  readonly chance: number;
}

/** Ein Segment mit seiner Lage im Rad (Winkel in Grad ab oben, im Uhrzeigersinn). */
export interface Wedge extends WheelSegment {
  readonly start: number;
  readonly end: number;
  readonly mid: number;
  /** Anteil an der Summe aller Chancen (0 bis 1). */
  readonly share: number;
  /** Ein einzelnes Segment füllt das ganze Rad und wird als Kreis gezeichnet. */
  readonly full: boolean;
}

export interface Point {
  readonly x: number;
  readonly y: number;
}

/** Ein Punkt auf dem Kreis um die Mitte des Rads. */
export function pointAt(angle: number, radius: number): Point {
  const radians = (angle * Math.PI) / HALF_CIRCLE;
  return {
    x: WHEEL_CENTER + radius * Math.sin(radians),
    y: WHEEL_CENTER - radius * Math.cos(radians),
  };
}

/** Teilt das Rad nach den Chancen auf; Segmente ohne Chance entfallen. */
export function layoutWedges(segments: readonly WheelSegment[]): readonly Wedge[] {
  const drawable = segments.filter((segment) => segment.chance > 0);
  const total = drawable.reduce((sum, segment) => sum + segment.chance, 0);
  let start = 0;
  return drawable.map((segment) => {
    const share = segment.chance / total;
    const end = start + share * FULL_CIRCLE;
    const wedge = { ...segment, start, end, mid: start + (end - start) * LANDING_FRACTION, share };
    start = end;
    return { ...wedge, full: share >= FULL_CHANCE };
  });
}

function coordinates(point: Point): string {
  return `${point.x.toFixed(PATH_DECIMALS)} ${point.y.toFixed(PATH_DECIMALS)}`;
}

/** Pfad eines Tortenstücks von `start` bis `end`. */
export function wedgePath(start: number, end: number): string {
  const large = end - start >= LARGE_ARC_FROM ? '1' : '0';
  const centre = numberText(WHEEL_CENTER);
  const radius = numberText(WHEEL_RADIUS);
  return [
    `M${centre} ${centre}`,
    `L${coordinates(pointAt(start, WHEEL_RADIUS))}`,
    `A${radius} ${radius} 0 ${large} 1 ${coordinates(pointAt(end, WHEEL_RADIUS))}`,
    'Z',
  ].join(' ');
}

function modulo(value: number): number {
  return ((value % FULL_CIRCLE) + FULL_CIRCLE) % FULL_CIRCLE;
}

/** Die neue Drehung des Rads, bei der die Mitte des Segments `mid` oben unter dem Zeiger steht. */
export function spinRotation(current: number, mid: number): number {
  const delta = modulo(modulo(-mid) - modulo(current));
  return current + SPIN_EXTRA_TURNS * FULL_CIRCLE + delta;
}
