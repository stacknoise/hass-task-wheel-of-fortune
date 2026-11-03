import { readFileSync } from "node:fs";
import { test, type Page } from "@playwright/test";

import { AUTH_FILE, type Tokens } from "../support/ha.ts";
import { callWS, signIn } from "../support/panel.ts";

const PANEL = "/task-wheel";
const OUT_DIR = process.env["SHOT_DIR"] ?? "../docs/screenshots";
const READY_MS = 30_000;
const SETTLE_MS = 600;
const SPIN_MS = 1500;

interface Created {
  readonly id: string;
}

const PEOPLE = [
  { name: "Anna", color: "#4f8cff" },
  { name: "Ben", color: "#e8590c" },
  { name: "Clara", color: "#2f9e44" },
  { name: "David", color: "#ae3ec9" },
  { name: "Emma", color: "#f59f00" },
];

const TASKS: readonly [string, number, number][] = [
  ["Take out the trash", 2, 1],
  ["Empty the dishwasher", 1, 1],
  ["Vacuum the living room", 3, 7],
  ["Clean the bathroom", 4, 7],
  ["Water the plants", 1, 3],
];

async function shot(page: Page, name: string): Promise<void> {
  await page.waitForTimeout(SETTLE_MS);
  await page.screenshot({ path: `${OUT_DIR}/${name}.png` });
}

async function service(
  base: string,
  name: string,
  data: Record<string, unknown>,
): Promise<void> {
  const tokens = JSON.parse(readFileSync(AUTH_FILE, "utf8")) as Tokens;
  const response = await fetch(`${base}/api/services/task_wheel/${name}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${tokens.access_token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(
      `${name}: ${String(response.status)} ${await response.text()}`,
    );
  }
}

test("README screenshots", async ({ page, baseURL }) => {
  const base = String(baseURL);
  await signIn(page, base);
  await page.goto(`${PANEL}/overview`);
  await page.locator("tw-overview-view").waitFor({ timeout: READY_MS });

  const people: Created[] = [];
  for (const person of PEOPLE) {
    people.push(
      await callWS<Created>(page, {
        type: "task_wheel/person/create",
        person: { ...person, load: "full" },
      }),
    );
  }
  const taskIds: string[] = [];
  for (const [name, points, dueDays] of TASKS) {
    const task = await callWS<Created>(page, {
      type: "task_wheel/task/create",
      task: {
        name,
        points,
        due_days: dueDays,
        allowed: [],
        frequency: { kind: "every_round" },
      },
    });
    taskIds.push(task.id);
  }
  const weekly = await callWS<Created>(page, {
    type: "task_wheel/schedule/create",
    schedule: {
      name: "Weekly chores",
      trigger: {
        kind: "recurring",
        weekdays: [5],
        time: "18:00",
        every_n_weeks: 1,
        monthly: false,
        anchor: null,
      },
      task_ids: taskIds,
      animations: ["wheel", "drum", "slot", "plinko", "spotlight"],
    },
  });

  for (const [name, animation, tasks] of [
    ["Weekend jobs", "wheel", taskIds.slice(0, 3)],
    ["Kitchen duty", "slot", taskIds.slice(1, 3)],
  ] as const) {
    await callWS(page, {
      type: "task_wheel/schedule/create",
      schedule: {
        name,
        trigger: { kind: "manual", remind_after_days: null },
        task_ids: tasks,
        animations: [animation],
      },
    });
  }

  // Verlauf: zwei abgeschlossene Auslosungen, die dritte bleibt offen
  const done = new Set<string>();
  for (let round = 0; round < 3; round += 1) {
    await service(base, "draw", { schedule: weekly.id });
    const snapshot = await callWS<{
      assignments: { id: string; round_id: string }[];
    }>(page, {
      type: "task_wheel/snapshot",
    });
    const fresh = snapshot.assignments.filter(
      (item) => !done.has(item.round_id),
    );
    const roundId = fresh[0]?.round_id;
    if (roundId === undefined) {
      continue;
    }
    done.add(roundId);
    if (round < 2) {
      for (const item of fresh.filter((entry) => entry.round_id === roundId)) {
        await service(base, "complete", { assignment_id: item.id });
      }
    }
  }

  await page.goto(`${PANEL}/overview`);
  await page.locator("tw-overview-view").waitFor({ timeout: READY_MS });
  await shot(page, "overview");

  // Auslosung: Runde starten und die Animation laufen lassen
  for (const [schedule, file] of [
    ["Weekend jobs", "draw-wheel"],
    ["Kitchen duty", "draw-slot"],
  ] as const) {
    await page.goto(`${PANEL}/draw`);
    await page.locator("tw-draw-view").waitFor({ timeout: READY_MS });
    await page.getByRole("combobox").selectOption({ label: schedule });
    await page.getByRole("button", { name: "Start round" }).click();
    await page.getByRole("button", { name: "Start the draw" }).click();
    await page.waitForTimeout(SPIN_MS);
    await shot(page, file);
    await page
      .getByRole("button", { name: "Restart round" })
      .click({ timeout: READY_MS })
      .catch(() => undefined);
  }

  await page.goto(`${PANEL}/tasks`);
  await page.locator("tw-tasks-view").waitFor({ timeout: READY_MS });
  await page.getByText("Clean the bathroom").first().click();
  await shot(page, "tasks");

  await page.goto(`${PANEL}/schedules`);
  await page.locator("tw-schedules-view").waitFor({ timeout: READY_MS });
  await page.getByText("Weekly chores").first().click();
  await shot(page, "schedules");

  await page.goto(`${PANEL}/history`);
  await page.locator("tw-history-view").waitFor({ timeout: READY_MS });
  await page
    .locator("summary, [aria-expanded]")
    .first()
    .click()
    .catch(() => undefined);
  await shot(page, "history");

  await page.goto(`${PANEL}/statistics`);
  await page.locator("tw-statistics-view").waitFor({ timeout: READY_MS });
  await shot(page, "statistics");
});
