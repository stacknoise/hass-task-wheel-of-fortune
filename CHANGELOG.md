# Änderungsprotokoll

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach [SemVer](https://semver.org/lang/de/).
Die Release-Notizen auf GitHub werden zusätzlich aus den Pull Requests erzeugt (`.github/release.yml`).

## [Unveröffentlicht]

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
