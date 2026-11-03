# Aufgaben-Glücksrad für Home Assistant

Verteilt Haushaltsaufgaben fair und mit etwas Spaß: Ein Glücksrad lost aus, wer was übernimmt. Die Chancen
richten sich danach, wer zuletzt wie viel erledigt hat, wer da ist und wer wie belastbar ist.

> **Status:** Entwicklung, Version 0.0.1. Das Projektgerüst steht (Integration lässt sich hinzufügen und
> entfernen, CI ist eingerichtet), Konstanten und Domänenmodell (AP-02), Häufigkeits- und Anwesenheitsregeln (AP-04/05), Persistenz über Repositories (AP-03), Gewichtung und Ziehung (AP-06), Zuteilungen und Tausch (AP-07), Statistik und Historie (AP-13) Runden und Zeitpläne (AP-08), Einstieg, Dienste, Events und Einstellungen (AP-09), Benachrichtigungen (AP-12) Entitäten (AP-11) sowie die WebSocket-API für das Panel (AP-10) und das Frontend-Gerüst des Panels (AP-14: Tabs, Store, Seitenleisten-Eintrag) sind umgesetzt, die Ansichten folgen mit den Arbeitspaketen. Es gibt noch keine Veröffentlichung
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

## Panel (Gerüst)

Nach dem Einrichten erscheint in der Seitenleiste der Eintrag „Aufgaben-Glücksrad“ (`/task-wheel`). Das Panel hat die
Tabs Übersicht, Auslosung, Aufgaben, Personen, Zeitpläne, Historie und Statistik, lädt den Stand per `snapshot` und
bleibt über `subscribe` aktuell. Der Tab **Auslosung** ist fertig: Zeitplan wählen, Runde starten (eine offene Runde
lässt sich fortsetzen), je Aufgabe das Glücksrad drehen (Segmentgröße = Chance, „Wer ist im Rad?“ mit Gründen; wer in der Runde schon eine Aufgabe hat, ist für die weiteren nicht mehr im Rad; überzählige Aufgaben bleiben als „nicht verteilbar“ offen; bleibt für eine Aufgabe nur noch eine Person übrig, wird sie ohne Drehen zugewiesen),
den Rest ohne Animation verlosen und die Runde abschließen. Das Ergebnis bestimmt immer das Backend; das Rad dreht
nur dorthin, bei „reduzierte Bewegung“ im Betriebssystem ohne Animation. Fertig sind außerdem **Übersicht**, **Historie** und **Statistik** (AP-17); Aufgaben, Personen und Zeitpläne zeigen
vorerst nur Zähler und werden mit AP-15 ausgebaut.


- **Übersicht:** nächste Auslosung (mit Blättern durch die Zeitpläne), offene Zuteilungen je Zeitplan mit Filter nach Person,
  Erledigen und Tauschen (nur erlaubte, nicht pausierte Personen, Hinweis auf verbleibende Joker), Punkte im Monat gegen den
  fairen Anteil und die jüngste Aktivität. Jede Zuteilung erscheint unter dem Zeitplan, der sie ausgelost hat. Ist eine Aufgabe in
  mehreren Zeitplänen, kann sie mehrfach ausgelost werden; jede Zuteilung wird einzeln erledigt.
- **Historie:** Runden aufklappbar (Zeitplan, Herkunft, Zuteilungen mit Chance und Status), Filter nach Person, Nachladen in
  Seiten und **CSV-Export** (Semikolon, UTF-8 mit Marke; Felder, die mit `=`, `+`, `-`, `@`, Tabulator oder Zeilenumbruch
  beginnen, werden mit einem Hochkomma entschärft, damit Tabellenprogramme sie nicht als Formel ausführen).
- **Statistik:** Zeitraum (Monat, 3 oder 12 Monate), Kennzahlen, Punkte gegen fairen Anteil, Erledigungsquote je Woche
  (SVG-Liniendiagramm ohne Diagrammbibliothek), Matrix Aufgabe mal Person und Auszeichnungen (Glückspilz, Pechvogel,
  Zuverlässigste Person). Leere Zeiträume zeigen einen Hinweis statt leerer Diagramme.

Texte gibt es auf Deutsch und Englisch (Sprache aus Home Assistant). Das Bundle ist nicht eingecheckt: vor dem
Ausprobieren `cd frontend && npm ci && npm run build`. Fehlt es, bleibt die Integration nutzbar und schreibt eine
Warnung ins Protokoll.

### Personen, Aufgaben und Zeitpläne im Panel (AP-15)

Die Tabs *Personen*, *Aufgaben* und *Zeitpläne* legen Objekte an, ändern und löschen sie (nur Administratoren). Links stehen
die Karten, rechts das Formular; Fehler des Backends erscheinen am betroffenen Feld und als Hinweis über den Knöpfen.

- **Personen:** Farbe im Rad, Belastbarkeit (voll, halb, pausiert), Anwesenheit (einmalig, Wochentage, Wochenrhythmus) mit
  Vorschau der nächsten vier Wochen und optional eine Benachrichtigungs-Entität (`notify.…`, wird beim Speichern geprüft).
- **Aufgaben:** erlaubte Personen, Häufigkeit (jede Runde, höchstens n× je Zeitraum, festes Intervall mit Zeitstrahl),
  Punkte, Frist und die Zusatzregeln „keine Wiederholung“, „Abwesenheit beachten“, „Tausch erlaubt“.
- **Zeitpläne:** wiederkehrend, einmalig oder nur manuell, Aufgabenwahl, Optionen und ein Beispiel für `task_wheel.draw`
  und das Ereignis `task_wheel_drawn`.

## Panel-API (WebSocket)

Das Panel spricht mit dem Backend über WebSocket-Befehle mit dem Präfix `task_wheel/`: `snapshot`, `subscribe`
(erst der Gesamtstand, danach nur Änderungen je Objekt), `history/list`, `statistics/get`,
`assignment/complete`, `assignment/swap`, `draw/begin|spin|spin_rest|commit|cancel` für jeden angemeldeten
Benutzer sowie `person/*`, `task/*`, `schedule/*` und `settings/update` nur für Administratoren. Alle Eingaben
werden gegen strenge Schemas geprüft (keine unbekannten Felder, begrenzte Längen). Ist in den Einstellungen
„Panel nur für Administratoren“ gesetzt, sind auch die Lesebefehle Administratoren vorbehalten. Details:
[docs/KONZEPT.md](docs/KONZEPT.md) §6.4.

## Entitäten

Für jede Person und jeden (nicht archivierten) Zeitplan legt die Integration ein Gerät „Task Wheel <Name>“ mit diesen Entitäten an. Sie entstehen und verschwinden mit den Personen und Zeitplänen; die Entity-IDs ergeben sich aus dem Gerätenamen und dem Entitätsnamen (hier mit deutscher Oberfläche):

| Entität | Beispiel | Inhalt |
|---|---|---|
| Offene Aufgaben je Person | `sensor.task_wheel_anna_offen` | Anzahl der noch nicht abgeschlossenen Zuteilungen |
| Punkte im Monat je Person | `sensor.task_wheel_anna_punkte` | gutgeschriebene Punkte im laufenden Monat (Faktoren für verspätet/verpasst aus den Einstellungen) |
| To-do-Liste je Person | `todo.task_wheel_anna` | offene Aufgaben mit Frist; **Abhaken erledigt die Zuteilung** (App, Sprachassistent), andere Änderungen sind nicht möglich |
| Nächste Auslosung je Zeitplan | `sensor.task_wheel_wochenplan_naechste_auslosung` | Zeitstempel; leer bei pausiert oder „nur manuell“ |
| Auslosen-Button je Zeitplan | `button.task_wheel_wochenplan_auslosen` | löst den Zeitplan wie im Panel aus |

Die Entitäten fragen nichts ab, sondern aktualisieren sich, sobald sich etwas für sie ändert (Auslosung, Erledigen, Tausch, Verpasst, geänderte Personen und Zeitpläne).

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
