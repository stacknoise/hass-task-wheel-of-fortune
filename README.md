# Aufgaben-Glücksrad für Home Assistant

Verteilt Haushaltsaufgaben fair und mit etwas Spaß: Ein Glücksrad lost aus, wer was übernimmt. Die Chancen
richten sich danach, wer zuletzt wie viel erledigt hat, wer da ist und wer wie belastbar ist.

> **Status:** Entwicklung, Version 0.0.1. Das Projektgerüst steht (Integration lässt sich hinzufügen und
> entfernen, CI ist eingerichtet), Konstanten und Domänenmodell (AP-02), Häufigkeits- und Anwesenheitsregeln (AP-04/05), Persistenz über Repositories (AP-03), Gewichtung und Ziehung (AP-06), Zuteilungen und Tausch (AP-07), Statistik und Historie (AP-13) Runden und Zeitpläne (AP-08), Einstieg, Dienste, Events und Einstellungen (AP-09) sowie Benachrichtigungen (AP-12) sind umgesetzt, Panel und Entitäten folgen mit den Arbeitspaketen. Es gibt noch keine Veröffentlichung
> über HACS.

## Funktionen (geplant)

- **Personen** als eigene Objekte, unabhängig von HA-Benutzern: Farbe im Rad, volle oder halbe Last oder Pause,
  Abwesenheiten (einmalig, an festen Wochentagen, im Wochenrhythmus wie „jede 2. Woche Fr–Fr“),
  optionale Benachrichtigung
- **Aufgaben** mit erlaubten Personen, Punkten (Aufwand), Frist und Häufigkeit: jede Runde,
  höchstens n× pro Tag/Woche/Monat oder festes Intervall mit Toleranz
- **Zeitpläne**: wiederkehrend, einmalig oder nur manuell
- **Auslosung** automatisch oder im Panel mit Glücksrad-Animation; Segmentgröße = Chance
- **Fairness**: Wer im Verhältnis zu seinem fairen Anteil weniger Punkte hatte, bekommt ein größeres Stück
- **Tauschen mit Joker**, nur mit Personen, die die Aufgabe bekommen dürfen
- **Historie** mit CSV-Export und **Statistiken** (fairer Anteil, Erledigungsquote, Matrix Aufgabe × Person)
- **Home-Assistant-Anbindung**: Dienste, Events, Sensoren, To-do-Listen je Person, Buttons je Zeitplan

## Installation (sobald veröffentlicht)

1. HACS → Integrationen → Menü → *Benutzerdefinierte Repositories* →
   `https://github.com/stacknoise/hass-task-wheel-of-fortune`, Typ *Integration*
2. „Aufgaben-Glücksrad“ installieren und Home Assistant neu starten
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Aufgaben-Glücksrad*
4. In der Seitenleiste erscheint **Glücksrad**; dort Personen, Aufgaben und Zeitpläne anlegen

Voraussetzung: Home Assistant 2025.6 oder neuer (wird mit dem ersten Release festgelegt).

## Dienste und Events

```yaml
action: task_wheel.draw
data:
  schedule: wochenplan
```

| Dienst | Zweck |
|---|---|
| `task_wheel.draw` | Runde eines Zeitplans auslosen |
| `task_wheel.complete` | Zuteilung erledigen |
| `task_wheel.swap` | Zuteilung per Joker tauschen |
| `task_wheel.set_absence` | Abwesenheit einer Person eintragen |

Events: `task_wheel_drawn`, `task_wheel_completed`, `task_wheel_swapped`, `task_wheel_missed`, `task_wheel_reminder`. Mit `animate_on` meldet `task_wheel.draw` zusätzlich `task_wheel_animate` (Hinweis für eine Anzeige). Die Inhalte nennen nur Kennungen, Namen und Zahlen.

Zeitplan und Person lassen sich über Kennung oder Kurzname ansprechen, die Aufgabe über Kennung oder Namen. `task_wheel.complete` nimmt entweder `assignment_id` oder `person` zusammen mit `task`.

Einstellungen (Joker, Fairness-Fenster, Aufbewahrung, Punktefaktoren, Kulanzzeit, Panel nur für Administratoren) ändert man unter *Einstellungen → Geräte & Dienste → Aufgaben-Glücksrad → Konfigurieren*. Jede Nacht um 03:00 werden verpasste Zuteilungen markiert und Runden nach der Aufbewahrungsfrist gelöscht.

## Benachrichtigungen

Jede Person kann ein Ziel haben: eine `notify`-Entität (über `notify.send_message`) oder einen Legacy-Dienst `notify.<name>`, z. B. `notify.mobile_app_anna`. Es sind nur vorhandene Ziele der Domäne `notify` erlaubt; geprüft wird beim Speichern und bei jedem Senden.

| Anlass | Empfänger |
|---|---|
| Runde ausgelost (nur wenn der Zeitplan „Ergebnis als Push-Nachricht senden“ aktiv hat) | alle Personen mit Ziel, eine Zeile je Person |
| Aufgabe getauscht | die Person, die die Aufgabe übernimmt |
| Erinnerung (Zeitplan „nur manuell“, nach n, 2n, … Tagen ohne Auslosung) | alle Personen mit Ziel |

Ein Ziel, das mehrere Personen teilen (z. B. ein Familienkanal), bekommt jede Meldung nur einmal. Die Texte stehen in `custom_components/task_wheel/texts/` (de, en; andere Sprachen fallen auf Englisch zurück). Ein fehlgeschlagener Versand wird protokolliert und blockiert weder die Auslosung noch andere Ziele.

## Entitäten (geplant)

| Entität | Beispiel |
|---|---|
| Offene Aufgaben je Person | `sensor.task_wheel_anna_offen` |
| Punkte im Monat je Person | `sensor.task_wheel_anna_punkte` |
| To-do-Liste je Person | `todo.task_wheel_anna` |
| Nächste Auslosung je Zeitplan | `sensor.task_wheel_wochenplan_naechste` |
| Auslosen-Button je Zeitplan | `button.task_wheel_wochenplan_auslosen` |

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/KONZEPT.md](docs/KONZEPT.md) | Technisches Konzept: Architektur, Schichten, Muster, Datenmodell, Algorithmen, Schnittstellen, Sicherheit, Performance, Code-Regeln |
| [docs/ARBEITSPAKETE.md](docs/ARBEITSPAKETE.md) | Arbeitspakete AP-00 bis AP-19 mit Abhängigkeiten, Größen und Definition of Done |
| [docs/CODE_DOKU.md](docs/CODE_DOKU.md) | Code-Dokumentation: Metriken, Schwellwerte, Abhängigkeiten, Änderungsprotokoll |
| [mockups/](mockups/) | Klickbare UI-Mockups ([interaktiv ansehen](https://claude.ai/artifact/NEch6MPsvESdj91pqQFHT7)) |

## Entwicklung

Kurzfassung der Regeln (Details in KONZEPT.md §10):

- Backend: Python 3.13, Home-Assistant-Custom-Integration; Frontend: Lit 3 + TypeScript (strict), Build mit Vite
- Factory + Strategy + Repository: Fabriken erzeugen Regel-Strategien registrierungsbasiert ohne `if/elif`-Ketten, Speicherung nur über Repositories
- Klare Schichten (Konstanten, Einstieg, Schnittstellen, Anwendung, Domäne, Infrastruktur), Importrichtung wird in CI geprüft
- Keine Literale im Code, alles über Konstanten; kein duplizierter Code
- Sicherheit und Performance zuerst: validierte Eingaben, Konfiguration nur für Admins, Ziehung nur im Backend
- **Jede Codeänderung wird in [docs/CODE_DOKU.md](docs/CODE_DOKU.md) protokolliert**; die README wird bei sichtbaren Änderungen nachgezogen

Befehle:

```bash
# Backend (Python 3.13)
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
ruff check . && ruff format --check . && mypy && lint-imports && pytest

# Frontend (Node 22)
cd frontend && npm ci && npm run lint && npm run typecheck && npm test && npm run build && npm run bundle-budget

# Code-Doku erzeugen (docs/code-doku/index.html) und Schwellwerte prüfen
python3 docs/code-doku/generate.py --check
```

### Continuous Integration

Pull Requests und `main` durchlaufen die Jobs `hassfest`, `HACS validation`, `lint`, `typecheck`, `architecture`
(Importrichtung, Duplikate), `test-backend`, `test-frontend`, `build-frontend` (inkl. Bundle-Budget), `audit` und
`docs-check` (Code geändert ⇒ `docs/CODE_DOKU.md` geändert) und `code-doku` (Generator läuft, Schwellwerte aus `docs/CODE_DOKU.md` §1.1 eingehalten). Dependabot hält pip, npm und GitHub Actions aktuell.

Sicherheitslücken bitte vertraulich melden, siehe [SECURITY.md](SECURITY.md).

## Lizenz

[MIT](LICENSE)
