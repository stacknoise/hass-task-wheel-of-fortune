<div align="center">

# 🎡 Task Wheel of Fortune

**Who takes out the trash this week? Let the wheel decide.**

Fair household chores for Home Assistant, drawn with a bit of drama.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/stacknoise/hass-task-wheel-of-fortune)](https://github.com/stacknoise/hass-task-wheel-of-fortune/releases)
[![License: MIT](https://img.shields.io/github/license/stacknoise/hass-task-wheel-of-fortune)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.6%2B-41BDF5.svg)](https://www.home-assistant.io)

[![Open your Home Assistant instance and open the repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stacknoise&repository=hass-task-wheel-of-fortune&category=integration)

<img src="https://raw.githubusercontent.com/stacknoise/hass-task-wheel-of-fortune/main/docs/screenshots/draw-wheel.png" alt="Drawing a chore with the wheel of fortune" width="780">

</div>

## Chores without the arguments

Nobody likes dividing up the housework. Task Wheel of Fortune does it for you: it draws who takes which
chore, keeps score of who has done how much, and makes sure the load stays fair over time. Whoever has done
less recently gets a bigger slice of the wheel. Whoever is away is simply not on it.

And because chores are more fun with a little suspense, every draw comes with an animation.

## Why you will like it

- 🎰 **Eight ways to draw.** Wheel of fortune, lottery drum, slot machine, Plinko, spotlight, scratch cards, breaking news or an award ceremony ("And the chore goes to …"). Pick one per schedule, or let it surprise you every time.
- ⚖️ **Fair by design.** Chances follow each person's fair share, based on points, presence and capacity. A person on half load, on holiday or on a weekly rota is taken into account automatically. [How fairness works →](docs/FAIRNESS.md)
- 🗓️ **Schedules.** Draw every Monday, once, or by hand. Each round hands every person at most one chore.
- 🏠 **Rooms and rules.** Assign chores to your Home Assistant areas. Say who may do what, how often, how much effort it is (points) and how much load a person needs to take it.
- 🔄 **Swapping and "stays undone".** Swap chores with someone else from the same draw (a real swap: each takes the other's chore), or openly skip one. Everything is counted.
- 📊 **History and statistics.** Every draw, completion rate, task × person matrix, lucky and unlucky ones, plus CSV export.
- 📱 **Looks good everywhere.** The panel is made for desktop, tablet and phone, in English and German.
- 🔔 **Fits into Home Assistant.** Services, events, sensors, a to-do list per person and a draw button per schedule. Use it in automations, dashboards and notifications.

## Screenshots

<table>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/stacknoise/hass-task-wheel-of-fortune/main/docs/screenshots/overview.png" alt="Overview"><br><sub><b>Overview:</b> open chores, points this month, next draw</sub></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/stacknoise/hass-task-wheel-of-fortune/main/docs/screenshots/draw-slot.png" alt="Slot machine"><br><sub><b>Draw:</b> the slot machine, one of eight animations</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/stacknoise/hass-task-wheel-of-fortune/main/docs/screenshots/schedules.png" alt="Schedules"><br><sub><b>Schedules:</b> recurring, once or manual</sub></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/stacknoise/hass-task-wheel-of-fortune/main/docs/screenshots/statistics.png" alt="Statistics"><br><sub><b>Statistics:</b> fair share, completion rate, task × person</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/stacknoise/hass-task-wheel-of-fortune/main/docs/screenshots/history.png" alt="History"><br><sub><b>History:</b> every draw, with CSV export</sub></td>
    <td width="50%"></td>
  </tr>
</table>

## Installation

Task Wheel of Fortune is not (yet) in the default HACS store, so you add it as a **custom repository**.
You need [HACS](https://hacs.xyz) and Home Assistant 2025.6 or newer.

[![Open your Home Assistant instance and open the repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stacknoise&repository=hass-task-wheel-of-fortune&category=integration)

Or by hand:

1. In HACS open the menu (⋮) → *Custom repositories*, add `https://github.com/stacknoise/hass-task-wheel-of-fortune` as type *Integration*.
2. Search for **Task Wheel of Fortune** in HACS, click *Download* and restart Home Assistant.
3. Go to *Settings → Devices & services → Add integration* and pick **Task Wheel of Fortune**.

The panel now appears in the sidebar ("Aufgaben-Glücksrad" if Home Assistant is set to German).

<details>
<summary>Without HACS</summary>

Extract the folder `custom_components/task_wheel` from `task_wheel.zip` of the latest
[release](https://github.com/stacknoise/hass-task-wheel-of-fortune/releases) to `config/custom_components/task_wheel`
and restart Home Assistant.

</details>

## Quick start

1. **People:** add everyone who takes part. Choose a color for the wheel and a load capacity (full, half or paused), and enter absences if there are any.
2. **Tasks:** add your chores with the people who may do them, points for the effort and how often they come up (every round, "at most 2× per month", a fixed interval, …).
3. **Schedule:** create a schedule, for example "every Saturday at 10:00", choose its tasks and animations, and set the **deadline**: how long the tasks stay valid and from when (right away, after an offset, the next day or on a weekday at a time). Only people who are present at some point in that period can get a task.
4. **Draw:** open the *Draw* tab, press start, say from when the tasks apply and how long people have, and watch. (For a scheduled plan you confirm that this draw replaces its next regular run.) Or let the schedule draw by itself and tell everyone with a push message.
5. **Done?** Tick chores off in the *Overview* (or in the to-do list of the person). The statistics keep score and the next draw becomes fairer.

## Use it in Home Assistant

```yaml
# Draw a round from an automation
action: task_wheel.draw
data:
  schedule: weekly-plan
```

Besides the draw service there are `task_wheel.complete`, `task_wheel.swap` and `task_wheel.set_absence`, events for
draws, completions and reminders, sensors and a to-do list per person, and a draw button per schedule.
Everything is listed in the [reference](docs/REFERENCE.md).

## More

| | |
|---|---|
| [How fairness works](docs/FAIRNESS.md) | Fair share, chances and examples |
| [Reference](docs/REFERENCE.md) | Services, events, notifications, entities, panel, WebSocket API |
| [Development](docs/DEVELOPMENT.md) | Build, test, release, continuous integration |
| [Changelog](CHANGELOG.md) | What changed in which version |
| [Concept and code documentation](docs/KONZEPT.md) | Architecture and code metrics (in German) |

Found a bug or have an idea? Open an [issue](https://github.com/stacknoise/hass-task-wheel-of-fortune/issues).
Please report security problems confidentially, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
