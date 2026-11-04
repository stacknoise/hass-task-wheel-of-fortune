# Änderungsprotokoll

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach [SemVer](https://semver.org/lang/de/).
Die Release-Notizen auf GitHub werden zusätzlich aus den Pull Requests erzeugt (`.github/release.yml`).

## [0.2.0] – 2026-11-04

- Der Name ist überall englisch: „Task Wheel of Fortune“ in HACS und in der Integrationsliste (Version 0.1.1 wurde nicht veröffentlicht, ihre Änderungen sind hier enthalten)
- Drei neue Auslosungs-Animationen: Rubbellose (selbst rubbeln oder per Münze, beim Gewinnerlos ist die Runde fertig), Eilmeldung (Zeitung mit Gerüchten und Stempel) und Oscar-Verleihung („Und die Aufgabe geht an …“)
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
