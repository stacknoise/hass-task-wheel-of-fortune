# Lokale Testumgebung

Zum Ausprobieren dient die bereits laufende Home-Assistant-Testinstanz auf SKYNET-GHOST (Windows 11, Docker Desktop),
die auch das Projekt *HASS Test Data Creator* nutzt. Es wird **keine zweite Instanz** gestartet, die Integration
wird in die vorhandene eingebunden.

| Was | Wert |
|---|---|
| Container | `dev-homeassistant-1` (Compose-Projekt `dev`), Image `ghcr.io/home-assistant/home-assistant:stable` |
| Adresse | <http://localhost:18123> (Host-Port 18123 auf Container-Port 8123) |
| Compose-Datei | `D:\Projekte\GitHub\Stacknoise\hass-test-data-creator-main\dev\docker-compose.yml` |
| Config | `dev/config` dieses Worktrees, als `/config` eingebunden |

## Integration einbinden (einmalig)

1. Dieses Repository auf SKYNET-GHOST auschecken, z. B. nach `D:\Projekte\GitHub\Stacknoise\hass-task-wheel-of-fortune`.
2. Panel-Bundle bauen (sonst fehlt `frontend/dist`):
   `cd frontend && npm ci && npm run build`
3. In der Compose-Datei oben unter `volumes` des Dienstes `homeassistant` eine Zeile ergänzen (nur lesen):

   ```yaml
   - D:\Projekte\GitHub\Stacknoise\hass-task-wheel-of-fortune\custom_components\task_wheel:/config/custom_components/task_wheel:ro
   ```

4. Container neu erstellen, die Config bleibt erhalten:
   `docker compose -f dev/docker-compose.yml up -d --force-recreate`
5. In Home Assistant unter *Einstellungen → Geräte & Dienste → Integration hinzufügen* **Aufgaben-Glücksrad** einrichten.

## Aktualisieren und prüfen

```bash
docker compose -f dev/docker-compose.yml restart      # nach Backend-Änderungen
docker logs dev-homeassistant-1 --since 5m            # im Log nach Traceback und ERROR suchen
```

Nach Frontend-Änderungen `npm run build` ausführen, neu starten und das Panel im Browser mit Strg+F5 neu laden.

## Regeln

- `dev/config` der Instanz nie ersetzen, verschieben, löschen, neu anlegen oder überkopieren (die Instanz startet sonst leer).
- Den Container nur aus dem Worktree des Test-Data-Creator-Projekts steuern, dort kein `git pull` im Haupt-Checkout.
- Vor riskanten Änderungen am HA-Speicher die betroffene Datei in `.storage` kopieren.
- Passwörter und Tokens gehören nicht in Notizen oder Commits.
