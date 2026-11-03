# Desktop-App

Modul des [Bewerbungsassistenten](../README.md) für den Pilot (MIN-342): die lokale Oberfläche (`bewerbungen/app.py`) als installierbare App für Windows und macOS, ohne Python, Terminal oder Repo.

- **Start per Doppelklick:** Server auf `127.0.0.1`, der Browser öffnet sich. Ein zweiter Start öffnet die laufende App. „Beenden“ steht oben rechts.
- **Datenordner:** beim ersten Start `Dokumente\Bewerbungsassistent` (unter Windows auch, wenn Dokumente in OneDrive liegt). Einstellungen und Protokoll liegen im App-Ordner (`%APPDATA%\Bewerbungsassistent`, macOS `~/Library/Application Support/Bewerbungsassistent`).
- **Einladung:** Der Link `bewerbungsassistent://einladung?code=…` öffnet die App und löst den Code ein; der Zugang kommt in den Schlüsselbund des Systems. Alternativ den Code auf der Seite einer Bewerbung eintippen.
- **Adresse der KI-Vermittlung:** kommt beim Bauen aus der Repository-Variable `KI_URL` (kein Geheimnis) in `voreinstellungen.json` im Paket.

## Updates

Die App fragt beim Start und danach höchstens alle 6 Stunden das neueste Release dieses Repos ab und zeigt ein Banner.

- **Windows:** „Jetzt aktualisieren“ lädt den Installer, prüft seine SHA-256-Prüfsumme gegen `SHA256SUMS.txt` des Releases und installiert still über die bestehende Version. Danach startet die neue Version selbst. Datenordner, Einstellungen und Zugang bleiben.
- **macOS:** Link zum Release zum Herunterladen.

**Neue Version ausrollen:**
1. `desktop/version.py` erhöhen und committen.
2. Tag `v<Version>` pushen. Die CI baut, installiert und testet die App und legt einen **Release-Entwurf** mit Installer, Prüfsummen und macOS-Zip an.
3. Den Entwurf prüfen (Installer auf einem Testrechner) und **veröffentlichen**. Erst dann sehen die Apps das Update.

Für das Release zusätzlich mit Code-Signatur (Windows Authenticode, Apple Developer ID); dann entfällt auch die Warnung bei der Erstinstallation (MIN-351).

## Installation im Pilot (Windows)

1. `Bewerbungsassistent-Setup-<Version>.exe` aus dem Release laden und öffnen.
2. Warnung von SmartScreen: „Weitere Informationen“ → „Trotzdem ausführen“ (die App ist im Pilot nicht signiert).
3. Installation ohne Administratorrechte, nach `%LOCALAPPDATA%\Programs\Bewerbungsassistent`; Eintrag im Startmenü.
4. Die App öffnet sich im Browser. Einladungslink anklicken oder Code eintippen.

Deinstallation über Einstellungen → Apps. Der Datenordner in Dokumente bleibt erhalten.

## Bauen

```bash
pip install -r ../requirements.txt -r requirements.txt
cd .. && pyinstaller --noconfirm desktop/bewerbungsassistent.spec
dist/Bewerbungsassistent/Bewerbungsassistent --selbsttest    # baut Lebenslauf und Anschreiben aus den Beispieldaten
```

Den Windows-Installer baut die CI mit Inno Setup (`installer.iss`), siehe `.github/workflows/app.yml`.

## Tests

```bash
python -m pytest -q
```
