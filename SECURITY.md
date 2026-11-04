# Sicherheitsrichtlinie

## Sicherheitslücke melden

Bitte **kein öffentliches Issue** anlegen. Nutze stattdessen die vertrauliche Meldung über GitHub:
*Security → Report a vulnerability* in diesem Repository
(<https://github.com/stacknoise/hass-task-wheel-of-fortune/security/advisories/new>).

Hilfreich sind: betroffene Version, Home-Assistant-Version, Schritte zur Reproduktion und die erwartete Auswirkung.

Das Projekt wird ehrenamtlich gepflegt. Richtwerte (keine Zusage): Eingangsbestätigung innerhalb von 7 Tagen,
erste Einschätzung innerhalb von 14 Tagen; eine Korrektur erscheint als neues Release, und die Meldung wird danach
(auf Wunsch mit Namensnennung) als Security Advisory veröffentlicht.

## Unterstützte Versionen

Vor dem ersten stabilen Release (`v1.0.0`) wird nur die jeweils neueste `v0.x`-Version mit Korrekturen versorgt.

## Was öffentlich ist

Das gebaute Panel (JavaScript) wird von Home Assistant unter `/task_wheel_static` **ohne Anmeldung** ausgeliefert (so
arbeiten alle benutzerdefinierten Panels). Es enthält keine Daten und keine Geheimnisse, nur den Programmcode, der auch
im Repository liegt. Alle Daten und Aktionen laufen über angemeldete WebSocket-Verbindungen und Dienste von Home
Assistant (Konfigurationsbefehle nur für Administratoren, Einstellung `panel_admin_only` für das Panel).

## Herkunft der Releases

Releases entstehen nur über den Workflow `Release` aus einem Commit auf `main`, dessen CI vollständig grün ist. Dem
Release liegt `SHA256SUMS` für `task_wheel.zip` bei; die Prüfsumme lässt sich mit `sha256sum -c SHA256SUMS` prüfen.
HACS lädt das ZIP direkt aus dem Release.

## Grundsätze

Die Sicherheitsmaßnahmen der Erweiterung sind in [docs/KONZEPT.md](docs/KONZEPT.md), Abschnitt 8, beschrieben.
