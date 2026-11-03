import { expect, test, type Page } from '@playwright/test';

import { callWS, signIn } from '../support/panel.ts';

const PANEL = '/task-wheel';
const TASK_NAME = 'Müll rausbringen';
const SECOND_TASK_NAME = 'Spülmaschine ausräumen';
// Nur die offenen Zuteilungen; die Aktivitätsliste nennt erledigte Aufgaben weiter
const openRows = (page: Page) => page.locator('.assignments li', { hasText: TASK_NAME });
const READY_MS = 30_000;
// Budget für das Laden des Panels bis zur ersten Ansicht (Messwert: docs/CODE_DOKU.md §3.2)
const PANEL_LOAD_BUDGET_MS = 5000;

// Bei einem Fehler steht der Zustand der Seite im Protokoll (der Artefakt-Download ist nicht immer erreichbar)
test.afterEach(async ({ page }, info) => {
  if (info.status !== info.expectedStatus) {
    console.log(await page.locator('html').ariaSnapshot());
  }
});

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
  // Getauscht wird nur innerhalb einer Auslosung: jede Person braucht eine Zuteilung
  const second = await callWS<Created>(page, {
    type: 'task_wheel/task/create',
    task: {
      name: SECOND_TASK_NAME,
      allowed: [anna.id, ben.id],
      frequency: { kind: 'every_round' },
    },
  });
  await callWS(page, {
    type: 'task_wheel/schedule/create',
    schedule: {
      name: 'Wochenrunde',
      trigger: { kind: 'manual' },
      task_ids: [task.id, second.id],
    },
  });

  // Auslosung: Runde starten, drehen, abschließen
  await page.goto(`${PANEL}/draw`);
  await page.getByRole('button', { name: 'Runde starten' }).click();
  await page.getByRole('button', { name: 'Auslosung starten' }).click();
  await page.getByRole('button', { name: 'Nächste Aufgabe' }).click({ timeout: READY_MS });
  await page.getByRole('button', { name: 'Runde abschließen' }).click({ timeout: READY_MS });
  await expect(page.getByText('Runde abgeschlossen')).toBeVisible();

  // Die Zuteilung steht in der Übersicht; wer sie hat, entscheidet die Ziehung
  await page.goto(`${PANEL}/overview`);
  const row = openRows(page).first();
  await expect(row).toBeVisible({ timeout: READY_MS });
  const owner = (await row.textContent())?.includes('Anna') ? 'Anna' : 'Ben';
  const other = owner === 'Anna' ? 'Ben' : 'Anna';

  // Tausch gegen Joker an die andere Person
  await row.getByRole('button', { name: 'Aktionen' }).click();
  await row.getByRole('menuitem', { name: 'Tauschen' }).click();
  await page
    .getByRole('group', { name: 'Tauschen mit' })
    .getByRole('button', { name: other })
    .click();
  await expect(openRows(page).first()).toContainText(other);

  // Erledigen
  await openRows(page).first().getByRole('button', { name: 'Aktionen' }).click();
  await openRows(page).first().getByRole('menuitem', { name: 'Erledigt', exact: true }).click();
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Erledigt', exact: true })
    .click();
  await expect(openRows(page)).toHaveCount(0, {
    timeout: READY_MS,
  });
});
