# Reference

Services, events, notifications, entities and the panel in detail. [← Back to the README](../README.md)

## Services and events

```yaml
action: task_wheel.draw
data:
  schedule: weekly-plan
```

| Service | Purpose |
|---|---|
| `task_wheel.draw` | Draw a round of a schedule |
| `task_wheel.complete` | Complete an assignment |
| `task_wheel.swap` | Swap an assignment with a joker |
| `task_wheel.set_absence` | Enter an absence for a person |

Events: `task_wheel_drawn`, `task_wheel_completed`, `task_wheel_swapped`, `task_wheel_missed`, `task_wheel_reminder`. With `animate_on`, `task_wheel.draw` additionally fires `task_wheel_animate` (a hint for a display). The payloads contain only identifiers, names and numbers. "Stays undone" and deleting a draw fire no event.

A schedule and a person can be addressed by identifier or short name, a task by identifier or name. `task_wheel.complete` takes either `assignment_id` or `person` together with `task`.

Settings (jokers, fairness window, retention, points factors, grace period, panel for administrators only) are changed under *Settings → Devices & services → Task Wheel of Fortune → Configure*. Every night at 03:00, missed assignments are marked and rounds older than the retention period (at least 373 days) are deleted; rounds that still hold open assignments are kept.

## Notifications

Each person can have a target: a `notify` entity (via `notify.send_message`) or a legacy service `notify.<name>`, e.g. `notify.mobile_app_anna`. Only existing targets of the `notify` domain are allowed; this is checked when saving and on every send.

| Occasion | Recipient |
|---|---|
| Round drawn (only if the schedule has "Send result as push message" enabled) | all people with a target, one line per person |
| Task swapped | the person who takes over the task |
| Reminder (schedule "manual only", after n, 2n, … days without a draw) | all people with a target |

A target shared by several people (e.g. a family channel) receives each message only once. The texts are in `custom_components/task_wheel/texts/` (de, en; other languages fall back to English). A failed send is logged and blocks neither the draw nor other targets.

## Entities

For every person and every (non-archived) schedule, the integration creates a device "Task Wheel <name>" with these entities. They appear and disappear with the people and schedules; the entity IDs result from the device name and the entity name (shown here with the English UI):

| Entity | Example | Content |
|---|---|---|
| Open tasks per person | `sensor.task_wheel_anna_open` | number of assignments not yet completed |
| Points this month per person | `sensor.task_wheel_anna_points` | points credited in the current month (late/missed factors from the settings) |
| To-do list per person | `todo.task_wheel_anna` | open tasks with deadline; **checking one off completes the assignment** (app, voice assistant), other changes are not possible |
| Next draw per schedule | `sensor.task_wheel_weekly_plan_next_draw` | timestamp; empty when paused or "manual only" |
| Draw button per schedule | `button.task_wheel_weekly_plan_draw` | draws the schedule as in the panel |

The entities do not poll; they update as soon as something changes for them (draw, completion, swap, missed, changed people and schedules).

## Panel

After setup, the entry "Task Wheel of Fortune" (`/task-wheel`) appears in the sidebar. The panel has the
tabs Overview, Draw, Tasks, People, Schedules, History and Statistics, loads the state via `snapshot` and
stays up to date via `subscribe`. The **Draw** tab is finished: choose a schedule, start a round (an open round
can be resumed), play the schedule's animation for each task (wheel of fortune, lottery drum, slot machine, Plinko, spotlight, scratch cards, breaking news or award ceremony; for the first five the size equals the chance, scratch cards, breaking news and the award ceremony show no chances; "Who is in?" lists the reasons; whoever already has a task in the round is no longer on the wheel for the further ones; a round contains only as many due tasks as people can take part, and if there are more, the tasks are chosen at random (the schedule's order is kept); if only one person is left for a task, they are assigned without spinning),
draw the rest without animation and complete the round. The backend always determines the result; the animation only
follows it, and with "reduced motion" in the operating system it is skipped. **Overview**, **History**, **Statistics**, **Tasks**, **People** and **Schedules** are finished as well.

- **Overview:** next draw (with paging through the schedules), open assignments per schedule with a filter by person,
  an action menu per assignment with Complete and "Stays undone" (both with a confirmation popup) and Swap (only allowed, non-paused people of the same draw, with a note on the remaining jokers), points this month against the
  fair share, and the latest activity. The open assignments are grouped by **draw** (most recent first, with
  schedule and time); a draw without open assignments disappears from the list. A whole draw can be
  **deleted** after confirmation as long as none of its tasks is completed; it then also disappears from history and statistics.
  If a task is in several schedules, it can be drawn several times; each assignment is completed individually.
- **History:** expandable rounds (schedule, origin, assignments with chance and status, deleting a round after confirmation), filter by person, loading in
  pages and **CSV export** (semicolon, UTF-8 with BOM; fields that begin with `=`, `+`, `-`, `@`, a tab or a line break
  are defused with an apostrophe so that spreadsheet programs do not execute them as a formula).
- **Statistics:** period (month, 3 or 12 months), indicators, points against fair share, completion rate per week
  (SVG line chart without a charting library), task × person matrix and awards (lucky one, unlucky one,
  most reliable person). Empty periods show a note instead of empty charts.

**Tablet and smartphone:** the panel adapts to its own width. On a tablet in portrait mode and on a smartphone, the stage (wheel, result, "Next task") sits at the top of the draw and the round list below it; on a smartphone everything is single-column and compact, controls have touch size (44 px), and in narrow mode the Home Assistant menu button for the sidebar appears.

Texts are available in German and English (language from Home Assistant). The bundle is not checked in: before
trying it out, run `cd frontend && npm ci && npm run build`. If it is missing, the integration stays usable and writes a
warning to the log.

### People, tasks and schedules in the panel

The *People*, *Tasks* and *Schedules* tabs create, change and delete objects (administrators only). People and tasks cannot be deleted while they are still in use: a person not while a task allows them or they have open assignments; a task not while a schedule contains it or it is still assigned and open. The cards are laid out
in a grid; adding and editing open a popup (full screen on a smartphone, close with Escape or ✕), and deleting asks for confirmation in another popup. Backend errors appear at the affected field and as a note in the popup.

- **People:** color on the wheel, load capacity (full, half, paused), presence (one-off, weekdays, weekly rhythm, recurring) with a
  preview of the next four weeks, and optionally a notification entity (`notify.…`, with a search across the entities and services of Home Assistant, checked when saving).
- **Tasks:** allowed people, frequency (every round, at most n× per period, fixed interval with a timeline),
  points, deadline, minimum load capacity (any, at least half or full load only; whoever is below it does not get onto the wheel for the task and cannot take it over by swapping) and the extra rules "no repetition", "respect absence", "swap allowed". A task can optionally be assigned to a **room** (a Home Assistant area); the room is shown on the task card, in the overview, the draw, the history (also as a column in the CSV export) and the statistics. If an area is deleted in Home Assistant, the task keeps the assignment and shows "Unknown room" until you pick another one.
- **Schedules:** recurring, one-off or manual only, task selection, options and an example for `task_wheel.draw`
  and the event `task_wheel_drawn`.

## Panel API (WebSocket)

The panel talks to the backend through WebSocket commands with the prefix `task_wheel/`: `snapshot`, `subscribe`
(first the full state, then only changes per object), `history/list`, `statistics/get`, `availability/preview` (presence preview),
`assignment/complete`, `assignment/swap`, `assignment/skip`, `draw/begin|preview|spin|spin_rest|commit|cancel` for every signed-in
user, and `round/delete`, `person/*`, `task/*`, `schedule/*` and `settings/update` for administrators only. All inputs
are validated against strict schemas (no unknown fields, limited lengths). If "Panel for administrators only" is set in the settings,
the read commands are also reserved for administrators. Details:
[docs/KONZEPT.md](KONZEPT.md) §6.4 (in German).
