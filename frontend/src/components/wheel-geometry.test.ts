import { describe, expect, it } from 'vitest';

import { layoutWedges, pointAt, spinRotation, wedgePath } from './wheel-geometry.ts';

const seg = (id: string, chance: number) => ({ id, label: id, color: '#000000', chance });

describe('layoutWedges', () => {
  it('teilt den Kreis im Verhältnis der Chancen auf', () => {
    const [a, b] = layoutWedges([seg('a', 3), seg('b', 1)]);
    expect(a).toMatchObject({ start: 0, end: 270, mid: 135, share: 0.75, full: false });
    expect(b).toMatchObject({ start: 270, end: 360, share: 0.25 });
  });

  it('lässt Segmente ohne Chance weg und zeichnet ein einzelnes als Vollkreis', () => {
    const wedges = layoutWedges([seg('a', 1), seg('b', 0)]);
    expect(wedges).toHaveLength(1);
    expect(wedges[0]?.full).toBe(true);
  });

  it('liefert für ein leeres Rad keine Segmente', () => {
    expect(layoutWedges([])).toEqual([]);
  });
});

describe('wedgePath', () => {
  it('zeichnet einen kleinen und einen großen Bogen', () => {
    expect(wedgePath(0, 90)).toContain(' 0 0 1 ');
    expect(wedgePath(0, 270)).toContain(' 0 1 1 ');
  });
});

describe('pointAt', () => {
  it('misst Winkel ab oben im Uhrzeigersinn', () => {
    expect(pointAt(0, 10)).toEqual({ x: 180, y: 170 });
    const right = pointAt(90, 10);
    expect(right.x).toBeCloseTo(190);
    expect(right.y).toBeCloseTo(180);
  });
});

describe('spinRotation', () => {
  it('dreht das Segment unter den Zeiger, immer vorwärts und mit vollen Umdrehungen', () => {
    const target = spinRotation(0, 135);
    expect((target + 135) % 360).toBe(0);
    expect(target).toBeGreaterThan(360);
  });

  it('knüpft an die bisherige Drehung an', () => {
    const first = spinRotation(0, 100);
    const second = spinRotation(first, 250);
    expect(second).toBeGreaterThan(first);
    expect((second + 250) % 360).toBe(0);
  });
});
