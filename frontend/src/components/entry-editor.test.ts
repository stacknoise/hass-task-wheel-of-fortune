import { describe, expect, it } from 'vitest';

import './entry-editor.ts';
import type { TwEntryEditor } from './entry-editor.ts';

describe('Aufgabenliste des Zeitplans', () => {
  it('zeigt die Räume der Aufgaben unter dem Namen', async () => {
    const editor = document.createElement('tw-entry-editor') as TwEntryEditor;
    editor.tasks = [
      {
        id: 't1',
        label: 'Bad putzen',
        rooms: [
          { name: 'Bad', deleted: false },
          { name: 'Küche', deleted: false },
        ],
      },
      { id: 't2', label: 'Müll', rooms: [] },
    ];
    document.body.append(editor);
    await editor.updateComplete;
    const rows = [...(editor.shadowRoot?.querySelectorAll('.row') ?? [])];
    const rooms = (row: Element | undefined): string[] =>
      [...(row?.querySelectorAll('tw-room') ?? [])].map(
        (room) => (room as unknown as { name: string }).name,
      );
    expect(rooms(rows[0])).toEqual(['Bad', 'Küche']);
    expect(rooms(rows[1])).toEqual([]);
    editor.remove();
  });
});
