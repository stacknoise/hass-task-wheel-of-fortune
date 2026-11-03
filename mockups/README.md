# UI-Mockups: Aufgaben-Glücksrad

Klickbare Mockups für das Home-Assistant-Panel der Erweiterung, im HA-Look (Seitenleiste + Panel mit Tabs).
Interaktiv ansehen: https://claude.ai/artifact/NEch6MPsvESdj91pqQFHT7

Die `.dc.html`-Dateien sind die Quellen der Design-Canvas (Design-Component-Format) und dienen als Referenz
für die spätere Umsetzung des Frontends (z. B. als Lit-Webcomponent-Panel).

| Datei | Screen | Inhalt |
|---|---|---|
| `Main.dc.html` | Übersicht | Nächste geplante Auslosung, aktuelle Zuteilungen der Woche (abhakbar), Punkte im Monat, Aktivität |
| `Auslosung.dc.html` | Auslosung | Glücksrad-Animation pro Aufgabe. Segmentgröße = Chance (Fairness-Gewichtung), ausgeschlossene Personen mit Grund (nicht erlaubt, Pause, abwesend), Ergebnis mit Konfetti, „Rest ohne Animation verlosen" |
| `Aufgaben.dc.html` | Aufgaben & Regeln | Erlaubte Personen, Häufigkeit (jede Runde / max. n× pro Zeitraum / festes Intervall ± Toleranz mit Zeitstrahl), Punkte, Frist, Zusatzregeln |
| `Personen.dc.html` | Personen | Eigene Personen-Objekte (keine HA-User), Farbe im Rad, Abwesenheit, Belastbarkeit (volle/halbe Last), Benachrichtigungsdienst |
| `Zeitplan.dc.html` | Zeitpläne | Wochentage + Uhrzeit, enthaltene Aufgaben, Push, Beispiel für Dienst `task_wheel.draw` und Event `task_wheel_drawn` |
| `Historie.dc.html` | Historie | Runden (automatisch/manuell) mit Zuteilungen, Chance, Status (pünktlich, verspätet, getauscht, verpasst), Filter nach Person |
| `Statistik.dc.html` | Statistiken | KPIs, Punkte vs. fairer Anteil, Erledigungsquote pro Woche, Matrix Aufgabe × Person, Glückspilz/Pechvogel |

Alle Namen und Zahlen sind Beispieldaten.
