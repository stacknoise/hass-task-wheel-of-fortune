import { expect, test, type Page } from '@playwright/test';

import { callWS, signIn } from '../support/panel.ts';

const PANEL = '/task-wheel';
const TASK_NAME = 'Müll rausbringen';
// Nur die offenen Zuteilungen; die Aktivitätsliste nennt erledigte Aufgaben weiter
const openRows = (page: Page) => page.locator('.assignments .row', { hasText: TASK_NAME });
const READY_MS = 30_000;
// Budget für das Laden des Panels bis zur ersten Ansicht (Messwert: docs/CODE_DOKU.md §3.2)
const PANEL_LOAD_BUDGET_MS = 5000;

interface Created {
  readonly id: string;
}

test('Auslosung, Erledigen und Tausch im Panel', async ({ page, baseURL }) => {
  await signIn(page, String(baseURL));
  const started = Date.now();
  await page.goto(`${PANEL}/overview`);
  await page.locator('tw-overview-view').waitFor({ timeout: READY_MS });
  const loadMs = Date.now() - started;
  console.log(`Panel geladen in ${String(loadMs)} ms`);
  expect(loadMs).toBeLessThan(PANEL_LOAD_BUDGET_MS);

  // Bestand über die API anlegen (die Ansichten dafür testet vitest)
  const anna = await callWS<Created>(page, {
    type: 'task_wheel/person/create',
    person: { name: 'Anna', color: '#4f8cff', load: 'full' },
  });
  const ben = await callWS<Created>(page, {
    type: 'task_wheel/person/create',
    person: { name: 'Ben', color: '#e8590c', load: 'full' },
  });
  const task = await callWS<Created>(page, {
    type: 'task_wheel/task/create',
    task: {
      name: 'Müll rausbringen',
      allowed: [anna.id, ben.id],
      frequency: { kind: 'every_round' },
    },
  });
  await callWS(page, {
    type: 'task_wheel/schedule/create',
    schedule: {
      name: 'Wochenrunde',
      trigger: { kind: 'manual' },
      task_ids: [task.id],
    },
  });

  // Auslosung: Runde starten, drehen, abschließen
  await page.goto(`${PANEL}/draw`);
  await page.getByRole('button', { name: 'Runde starten' }).click();
  await page.getByRole('button', { name: 'Rad drehen' }).click();
  await page.getByRole('button', { name: 'Runde abschließen' }).click({ timeout: READY_MS });
  await expect(page.getByText('Runde abgeschlossen')).toBeVisible();

  // Die Zuteilung steht in der Übersicht; wer sie hat, entscheidet die Ziehung
  await page.goto(`${PANEL}/overview`);
  const row = openRows(page).first();
  await expect(row).toBeVisible({ timeout: READY_MS });
  const owner = (await row.textContent())?.includes('Anna') ? 'Anna' : 'Ben';
  const other = owner === 'Anna' ? 'Ben' : 'Anna';

  // Tausch gegen Joker an die andere Person
  await row.getByRole('button', { name: 'Tauschen' }).click();
  await page
    .getByRole('group', { name: 'Tauschen mit' })
    .getByRole('button', { name: other })
    .click();
  await expect(openRows(page).first()).toContainText(other);

  // Erledigen
  await page
    .locator('.row', { hasText: 'Müll rausbringen' })
    .first()
    .getByRole('button', { name: 'Erledigt' })
    .click();
  await expect(openRows(page)).toHaveCount(0, {
    timeout: READY_MS,
  });
});
