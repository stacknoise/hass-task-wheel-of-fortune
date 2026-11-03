import { afterEach, describe, expect, it, vi } from 'vitest';

import { downloadText } from './download.ts';

describe('downloadText', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('bietet den Text als Datei an und gibt die Adresse wieder frei', () => {
    const create = vi.fn(() => 'blob:test');
    const revoke = vi.fn();
    Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    downloadText('daten.csv', 'a;b', 'text/csv');
    expect(create).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revoke).toHaveBeenCalledWith('blob:test');
  });
});
