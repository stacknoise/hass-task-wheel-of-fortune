# Änderungsprotokoll

Angelehnt an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/) (ohne Kategorien), Versionierung nach [SemVer](https://semver.org/lang/de/).
Die Release-Notizen auf GitHub werden zusätzlich aus den Pull Requests erzeugt (`.github/release.yml`).

## [Unveröffentlicht]

- **Neu:** Entscheidungslog als Tab nach der Statistik, für alle sichtbar: Je Auslosung und Aufgabe steht, wer im Rad war (mit Chance), wer warum nicht (abwesend, nicht erlaubt, Belastbarkeit, schon versorgt …) und wer gezogen wurde; Tausch und Admin-Austausch stehen mit Vermerk darin. Die Aufbewahrung (Standard 7 Tage) stellt man in den Optionen der Integration ein, eine tägliche Bereinigung löscht ältere Einträge.
- **Geändert:** Bei Zeitplänen ohne Animation zeigt das Panel Administratoren vor dem Ziehen eine kurze Vorbereitung mit „Austauschen“ je Aufgabe; erst „Aufgaben direkt verteilen“ lost. Andere Benutzer bekommen wie bisher sofort das Ergebnis
- **Neu:** Der Admin kann in der vorbereiteten Auslosung (Panel) vor dem Start eine Aufgabe der Runde gegen eine andere Aufgabe desselben Zeitplans tauschen. Zur Wahl stehen nur Aufgaben, die nicht in der Runde sind; Aufgaben, die mit den heute anwesenden Personen nicht machbar sind (niemand erlaubt, anwesend und belastbar genug), sind nicht wählbar. Mit dem ersten Dreh ist der Tausch gesperrt. Neue Befehle `draw/replacements` und `draw/replace_task` (nur Administratoren); das ist etwas anderes als der Tausch zwischen Personen
- **Geändert:** Die Statistik „Verlosungen je Aufgabe: Soll und Ist“ wird je Zeitplan berechnet und gruppiert: Es zählen nur die Auslosungen des jeweiligen Zeitplans, eine Aufgabe in mehreren Zeitplänen erscheint in jedem davon. Die Box scrollt, die Zeitpläne lassen sich auf- und zuklappen
- **Geändert:** Aufgaben, die täglich anfallen (Häufigkeit „höchstens n× in 1 Tag“), sind in jeder Auslosung dabei; bei mehr Aufgaben als mitmachenden Personen füllt der Zufall nur die übrigen Plätze. Gibt es mehr tägliche Aufgaben als Personen, wird unter den täglichen zufällig gewählt
- Behoben: Wer am Tag der Auslosung abwesend ist, nimmt nicht mehr an ihr teil. Bisher genügte ein anwesender Tag zwischen Auslosung und Frist, sodass z. B. eine Person, die heute (Mittwoch) fehlt, aber morgen wieder da ist, trotzdem im Rad stand; das galt auch für wiederkehrende Abwesenheiten. Die Zahl der Aufgaben je Runde richtet sich nach den heute anwesenden Personen

## [0.5.0] – 2026-11-04

- **Geändert:** Der Tausch ist ein echter Tausch Aufgabe gegen Aufgabe innerhalb einer Auslosung: Ana (Bad) und Ben (Küche) haben danach Küche und Bad, jede Person behält genau eine Aufgabe (bisher bekam Ben Anas Aufgabe zusätzlich). Das Panel zeigt je Zielperson auch deren Aufgabe („Ben (Küche)“); ohne offene Gegenaufgabe lehnt der Dienst mit `swap_person_has_no_open_assignment` ab. Die Regeln (Aufgabe tauschbar, erlaubt, nicht pausiert, Belastbarkeit, Anwesenheit) gelten für beide Richtungen, beide Zuteilungen werden gemeinsam gespeichert und lösen je ein Event `task_wheel_swapped` aus; jede Person bekommt eine Benachrichtigung
- **Entfernt:** Der Tausch hat nichts mehr mit Jokern zu tun (keine Jokerprüfung `no_jokers_left`, kein Zähler, kein `jokers_left` in Snapshot und Panel); die Einstellung `jokers_per_month` bleibt für später reserviert und ohne Wirkung. Das Feld `person_ids` der Runden im Snapshot entfällt
- Geändert: Eine Auslosung im Panel dürfen nach dem ersten Ergebnis nur noch Administratoren abbrechen oder durch einen Neustart ersetzen; vor dem ersten Ergebnis kann sie jeder schließen
- Geändert: Der Dienst `complete` ohne eindeutiges Ziel meldet einen übersetzten Dienstfehler statt einer Schema-Ausnahme
- Behoben: Ein monatlicher Zeitplan mit mehreren Wochentagen (z. B. Montag und Donnerstag) löst nur noch einmal im Monat aus, am ersten gewählten Wochentag; bisher löste er an jedem gewählten Wochentag der ersten sieben Tage aus
- Behoben: Beim Wechsel des Home-Assistant-Panels oder bei einem Verbindungsabbruch während des Ladens blieben serverseitige Abonnements zurück
- Behoben: Die Auslosung hing in „Dreht“, wenn die Animation abgebrochen wurde (z. B. durch ein Live-Update); „Neu starten“ während einer laufenden Anfrage ist gesperrt und verwirft verspätete Antworten
- Behoben: Eine laufende Auslosung geht beim Wechsel des Tabs nicht mehr verloren
- Behoben: „Weitere laden“ in der Historie springt bei Live-Änderungen und nach dem Löschen einer Runde nicht mehr zurück
- Panel zeigt Ladefehler einer Ansicht und einen Hinweis „Daten womöglich veraltet“ mit „Erneut versuchen“ statt einer leeren Seite
- Tastatur und Screenreader: Dialoge nutzen das native `<dialog>` (Fokusfalle, Escape, Fokusrückgabe), das Aktionsmenü lässt sich mit Pfeiltasten bedienen, Tabellen haben Überschriften mit Bezug, Karten sind als Knöpfe benannt, Strg-/Cmd-Klick auf Tabs öffnet einen neuen Tab
- Sicherheit: Personenfarben werden vor der Verwendung auf `#rrggbb` geprüft; Farben gelangen nicht mehr als Text in Stilangaben
- Leistung: Das Panel zeichnet nicht mehr bei jeder Zustandsänderung von Home Assistant neu; Formatierer, Raum- und Benachrichtigungslisten werden zwischengespeichert; die Übersicht fragt nach einer Aktion nur einmal neu
- Der Anfangsbuchstabe einer Person zerschneidet keine Emoji mehr, Prozentangaben und Daten folgen der Sprache; einheitliche Avatar-Marke
- Download der CSV-Datei funktioniert auch in Safari, Firefox und der Companion-App
- Die Statistik zeigt beim Wechsel des Zeitraums „in Arbeit“ (`aria-busy`), das Glücksrad teilt Abbruch und Reduced-Motion mit den übrigen Animationen
- Intern: Farbwerte nur noch in `constants/` (neue ESLint-Regel), Totcode und 15 ungenutzte Übersetzungsschlüssel entfernt, Test für Parität und Nutzung der Schlüssel
- Intern: Schlüssel-Literal in der Panel-Rundenansicht durch Konstante ersetzt.
- Behoben: ein einmaliger Zeitplan, dessen Termin während eines Ausfalls verstrichen ist, wird beim Start nachgeholt.
- Performance: der tägliche Verpasst-Lauf speichert und rechnet die Statistik je Runde einmal statt je Zuteilung.
- Performance: Speichern des Verlaufs kodiert nur noch geänderte Runden neu; Feldnamen der Datenklassen werden zwischengespeichert.
- Intern: Auslosung rechnet Kapazitäten und Erreichbarkeit nur einmal je Runde (spürbar bei langem Fairness-Fenster und vielen Abwesenheitsregeln); nur von Tests genutzte Funktionen entfernt
- Je Panel-Verbindung gibt es höchstens zwei Live-Abonnements (ein neues ersetzt das älteste)
- Dienste lehnen einen mehrdeutigen Aufgabennamen ab (`ambiguous_reference`) statt still die erste Aufgabe zu nehmen; Fehler eines Benachrichtigungsdienstes werden protokolliert und stören die übrigen Ziele nicht
- „Panel nur für Administratoren“ gilt jetzt auch für die Dienste, den Button „Auslosen“ und das Abhaken in der To-do-Liste; beim Aktivieren werden bestehende Panel-Verbindungen abgemeldet, und die Seitenleiste folgt der Einstellung sofort
- Behoben: Das Panel wird beim erneuten Einrichten nach einem abgebrochenen Setup nicht mehr doppelt registriert
- Beschädigter oder zu neuer Speicher zeigt beim Einrichten eine verständliche Fehlermeldung statt „Fehler beim Einrichten“
- Eine Auslosung im Panel schlägt fehl (und entfällt), wenn die gezogene Person, Aufgabe oder der Zeitplan inzwischen gelöscht wurde, statt unsichtbare Zuteilungen zu erzeugen
- Von Hand oder per Dienst ausgelöste Runden desselben Zeitplans brauchen 30 Sekunden Abstand; ist die Obergrenze gespeicherter Runden erreicht, entfällt die älteste abgeschlossene Runde statt alle weiteren Auslosungen zu blockieren
- Intern: doppelte Konstanten und doppelter Code zusammengeführt (Ressourcennamen, Statusmengen, Zeitspannen, Wochenanfang, offene Zuteilungen im Snapshot)
- Behoben: Ein einmaliger Zeitplan wird nicht mehr archiviert oder gelöscht, wenn seine Auslosung fehlgeschlagen ist
- Behoben: Zeitplan-, Erinnerungs- und Wartungs-Zeitgeber werden auch nach einem unerwarteten Fehler im Rückruf neu gesetzt
- Die Aufbewahrung des Verlaufs beträgt mindestens 373 Tage (Standard 373): Häufigkeitsregeln, Fairness-Fenster und offene Zuteilungen brauchen diesen Verlauf. Zu kurze gespeicherte Werte werden beim Start angehoben; Runden mit offenen Zuteilungen werden nie aufgeräumt
- Behoben: Eine Zuteilung mit längster Frist plus Kulanzzeit wurde bei Sommerzeit-Wechsel nie als verpasst markiert

## [0.4.0] – 2026-11-04

- Abwesenheiten können wiederkehren: neue Art „Wiederkehrend“ mit Wochentagen, Abstand in Wochen (z. B. jeden Mittwoch alle zwei Wochen), Beginn und optionalem Ende. Die Auslosung, die Fristfenster, die Kapazität und die Vorschau werten sie wie die übrigen Abwesenheiten aus; gespeicherte Abwesenheiten bleiben unverändert gültig, eine Migration ist nicht nötig
- Die Statistik (inklusive „Verlosungen je Aufgabe: Soll und Ist“) aktualisiert sich nach jeder Aktion (neue Auslosung, Erledigen, Tauschen, „Bleibt unerledigt“, Löschen) und nicht nur beim Öffnen

## [0.3.1] – 2026-11-04

- „Verlosungen je Aufgabe: Soll und Ist“ zeigt die Räume der Aufgaben
- Behoben: Das Panel (vor allem die lange Statistik) sprang beim Scrollen immer wieder an den Seitenanfang; die Tab-Leiste hat die Seite bei jedem Neuzeichnen zu sich zurückgeholt. Sie verschiebt jetzt nur noch sich selbst und nur beim Tabwechsel

## [0.3.0] – 2026-11-04

- Statistik: eigene Box „Verlosungen je Aufgabe: Soll und Ist“; für Aufgaben mit „höchstens n× in x Zeiträumen“ zeigt sie, wie oft die Aufgabe im laufenden und in den drei vorherigen Fenstern verlost wurde (z. B. 2 / 3 in den letzten 2 Monaten), sodass der Admin die Häufigkeit nachprüfen kann
- Die Auslosungsliste zeigt nur die Aufgaben, die in dieser Runde vergeben werden können: Es gibt höchstens so viele Aufgaben wie mitmachende Personen (je Person eine Aufgabe pro Runde). Bei mehr Aufgaben werden die Aufgaben zufällig gewählt, damit die Runde nicht vorhersehbar ist
- Aufgaben lassen sich mit „höchstens n× in x Tagen/Wochen/Monaten“ einplanen (z. B. 5× in 2 Monaten, 1× in 2 Wochen); das Fenster umfasst die laufende und die vorherigen Kalenderperioden. Bestehende Aufgaben behalten ihr Verhalten (x = 1)
- Personen, Aufgaben und Zeitpläne erscheinen im Panel alphabetisch, ohne Beachtung der Groß-/Kleinschreibung und nach der Sprache von Home Assistant (Umlaute, Zahlen nach ihrem Wert); ebenso die Räume in der Auswahl
- Eine Aufgabe kann mehrere Räume haben (Mehrfachauswahl im Aufgaben-Popup); alle Räume erscheinen in Übersicht, Auslosung, Aufgabenkarte, Historie (auch im CSV, durch Komma getrennt) und Statistik. Bereits gespeicherte einzelne Räume werden beim Start automatisch übernommen (Speicherstand 1.3)

## [0.2.0] – 2026-11-04

- Hinzufügen und Bearbeiten von Personen, Aufgaben und Zeitplänen öffnen in Popups (auf dem Smartphone Vollbild); Zahlenfelder (+/−) stehen paarweise nebeneinander, die Abwesenheiten scrollen ab zwei Einträgen
- Aufgaben haben eine Mindest-Belastbarkeit (egal, halb, voll); wer darunter liegt, kommt für die Aufgabe nicht ins Rad und kann sie auch nicht per Tausch übernehmen
- 16 Personenfarben (nach Farbton sortiert, zwei Reihen à 8) statt 8
- Hat ein Zeitplan keine Animation gewählt, wird die Runde sofort ausgelost und die Aufgabenliste erscheint direkt
- Der Name ist überall englisch: „Task Wheel of Fortune“ in HACS und in der Integrationsliste (Version 0.1.1 wurde nicht veröffentlicht, ihre Änderungen sind hier enthalten)
- Drei neue Auslosungs-Animationen: Rubbellose (selbst rubbeln oder per Münze, beim Gewinnerlos ist die Runde fertig), Eilmeldung (Zeitung mit Gerüchten und Stempel) und Oscar-Verleihung („Und die Aufgabe geht an …“)
- Die neuen Animationen zeigen keine Gewinnchancen; Oscar-Kuvert (der Zettel ragt nicht mehr heraus) und Zentrierung von Eilmeldung und Rubbellosen nachgebessert
- Aufgaben lassen sich einem Home-Assistant-Raum (Bereich) zuweisen; der Raum erscheint auf der Aufgabenkarte, in Übersicht, Auslosung, Historie (auch im CSV) und Statistik
- Titel auf Deutsch und Englisch: Seitenleiste und Panel-Überschrift heißen bei deutscher Systemsprache „Aufgaben-Glücksrad“, sonst „Task Wheel of Fortune“; HACS und Integrationsname bleiben englisch
- Panel für Tablet und Smartphone optimiert, vor allem die Auslosung (Bühne oben, kompaktes Layout, Menü-Knopf, Touch-Größen)
- README erklärt Fairness und fairen Anteil (Belastbarkeit, Anwesenheitstage, Punktefaktoren) mit Beispielen
- README komplett auf Englisch, die HACS-Installationsanleitung steht ganz oben

## [0.1.0] – 2026-11-03

Erste Veröffentlichung über HACS als benutzerdefiniertes Repository.

- Personen, Aufgaben, Zeitpläne und Auslosung mit Animation im Panel
- Fairness-Gewichtung, Tausch mit Joker, „Bleibt unerledigt“, Historie mit CSV-Export und Statistiken
- Home-Assistant-Anbindung: Dienste, Events, Sensoren, To-do-Listen, Buttons, Benachrichtigungen

[Unveröffentlicht]: https://github.com/stacknoise/hass-task-wheel-of-fortune/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/stacknoise/hass-task-wheel-of-fortune/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/stacknoise/hass-task-wheel-of-fortune/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/stacknoise/hass-task-wheel-of-fortune/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/stacknoise/hass-task-wheel-of-fortune/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/stacknoise/hass-task-wheel-of-fortune/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/stacknoise/hass-task-wheel-of-fortune/releases/tag/v0.1.0
