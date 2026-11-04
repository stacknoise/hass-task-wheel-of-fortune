import { afterEach, describe, expect, it, vi } from 'vitest';

import { REVOKE_DELAY_MS } from '../constants/index.ts';
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
    vi.useFakeTimers();
    downloadText('daten.csv', 'a;b', 'text/csv');
    expect(create).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(document.querySelector('a[download]')).toBeNull();
    expect(revoke).not.toHaveBeenCalled();
    vi.advanceTimersByTime(REVOKE_DELAY_MS);
    expect(revoke).toHaveBeenCalledWith('blob:test');
    vi.useRealTimers();
  });
});
