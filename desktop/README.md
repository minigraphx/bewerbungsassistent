# Desktop-App

Modul des [Bewerbungsbegleiters](../README.md) für den Pilot (MIN-342): die lokale Oberfläche (`bewerbungen/app.py`) als installierbare App für Windows und macOS, ohne Python, Terminal oder Repo.

- **Start per Doppelklick:** Server auf `127.0.0.1`, der Browser öffnet sich. Ein zweiter Start öffnet die laufende App. „Beenden“ steht oben rechts; Einrichtung, Meine Angaben und die übrigen Seiten stehen im Menü.
- **Einrichtung** (Seite `/einrichtung`, beim ersten Start automatisch): 1. Datenordner wählen, Vorschlag `Dokumente\Bewerbungsbegleiter` (unter Windows auch, wenn Dokumente in OneDrive liegt); erlaubt sind ein neuer, ein leerer oder ein bestehender Datenordner, nie ein Ordner mit anderen Dateien oder einer der App. 2. Einstiegsdatei (`einstieg.zip` oder `.json`) importieren, falls vorhanden (`onboarding/import_bundle.py`). 3. Einladungscode für die KI. 4. Browser-Erweiterung laden (siehe unten). Ordner und Datei kommen aus dem Auswahldialog des Systems (`dialogs.py`: PowerShell bzw. AppleScript), weil der Browser keine Pfade liefert und die ZIP-Datei grösser sein darf als eine Anfrage. Ein Wechsel des Datenordners gilt sofort, ohne Neustart. Fehlt der Ordner (z.B. USB-Stick), führt jede Seite zur Einrichtung.
- **Meine Angaben** (Seite `/angaben`, `routes_angaben.py`): das Formular für die Grundlagen, gebaut aus denselben Quellen. Ohne Lebenslauf und Suchprofil führen Einrichtung und Übersicht dorthin. Der Zwischenstand liegt in `dokumente/angaben-stand.json`, weil der Port bei jedem Start wechselt und der Speicher des Browsers verloren ginge. PDF- und Word-Dateien kommen beim Hochladen sofort nach `dokumente/<art>/`. „Übernehmen“ nutzt dieselben Prüfungen wie der Import einer Datei; Vorhandenes wird nur auf Wunsch ersetzt, der alte Stand bleibt als Entwurf.
- **App-Ordner:** Einstellungen und Protokoll in `%APPDATA%\Bewerbungsbegleiter`, macOS `~/Library/Application Support/Bewerbungsbegleiter`. Bis ein Datenordner gewählt ist, läuft die App auf `noch-kein-datenordner` darin.
- **Einladung:** Der Link `bewerbungsbegleiter://einladung?code=…` öffnet die App und löst den Code ein; der Zugang kommt in den Schlüsselbund des Systems. Alternativ den Code in der Einrichtung oder auf der Seite einer Bewerbung eintippen.
- **Adresse der KI-Vermittlung:** kommt beim Bauen aus der Repository-Variable `KI_URL` (kein Geheimnis) in `voreinstellungen.json` im Paket.

## Browser-Erweiterung

Die App ist zugleich der **Native-Messaging-Host** für die [Erweiterung](../erweiterung/README.md) (MIN-339). Startet Chrome sie mit `chrome-extension://…` als Argument, öffnet sie keine Oberfläche, sondern reicht die Anfragen der Erweiterung an die laufende App weiter (`native_host.py`). Läuft keine, startet sie sie im Hintergrund. Erlaubt sind nur Suchplan, Sichten, Treffer und Abschluss der Suche.

- **Anmeldung beim Browser** bei jedem Start (`native_messaging.py`): Windows über die Registry (`HKCU\Software\Google\Chrome\NativeMessagingHosts` und Edge) mit der Datei im App-Ordner; macOS und Linux mit einer Datei in den Profilordnern von Chrome, Chrome Beta, Edge, Chromium und Brave. Beim Start aus dem Repo verweist sie auf ein kleines Startskript im App-Ordner.
- **Ordner der Erweiterung:** Die App kopiert die Erweiterung aus dem Paket nach `<App-Ordner>/erweiterung`, wenn sich die Version geändert hat (`extension.py`). Die Einrichtung (Schritt 4) öffnet per Knopf die Erweiterungsseite von Chrome oder Edge und zeigt den Ordner im Finder bzw. Explorer.

## Claude mit dem eigenen Abo

Mit `--mcp` ist die App ein lokaler MCP-Server über stdin und stdout (MIN-377), für Claude Desktop und Claude Code. `mcp_server.py` spricht das Protokoll, `mcp_tools.py` legt fest, was Claude erreicht: Das ist die Grenze. Kein Versand, kein RAV, keine Formulare, keine Schlüssel. Der Zugang ist aus, bis die Person ihn unter „Erweiterte Einstellungen“ einschaltet (`routes_claude.py`, `claude_setup.py`). Anleitung für Nutzer: [`docs/eigenes-abo.md`](../docs/eigenes-abo.md). Eine App darf ein Abo nicht selbst nutzen, darum bleibt die KI auf diesem Weg in Claude.

## Updates

Die App fragt beim Start und danach höchstens alle 6 Stunden das neueste Release dieses Repos ab und zeigt ein Banner.

- **Windows:** „Jetzt aktualisieren“ lädt den Installer, prüft seine SHA-256-Prüfsumme gegen `SHA256SUMS.txt` des Releases und installiert still über die bestehende Version. Danach startet die neue Version selbst. Datenordner, Einstellungen und Zugang bleiben.
- **macOS:** „Jetzt aktualisieren“ lädt das Zip, prüft es gegen `SHA256SUMS-macOS.txt` und entpackt es in den versteckten Ordner `.Bewerbungsbegleiter-update` neben der App (`ditto`, Rechte und Symlinks bleiben). `codesign --verify --deep --strict` prüft das Paket. Nach dem Beenden tauscht ein kleines Skript alte und neue Version und startet die neue. Die alte bleibt liegen, bis die neue ihren Start bestätigt; sonst kommt sie nach 2 Minuten zurück und die App nennt die Version nicht mehr zum automatischen Update. Datenordner und Einstellungen bleiben.
  - **Ort:** Die App muss aus einem beschreibbaren Ordner laufen, am besten „Programme“. Startet macOS sie aus einem Ersatzordner (App Translocation, typisch direkt nach dem Download) oder darf sie den Ordner nicht schreiben, zeigt das Banner „Zuerst in den Ordner Programme verschieben“ und den Link zum Release.
  - **Erstmals von Hand:** Erst die Version mit diesem Weg kann sich selbst aktualisieren.
- **Beim Beenden (MIN-382):** Wartet ein Update und könnte die App es selbst installieren, läuft nach „Beenden“ derselbe Weg im Hintergrund, ohne Klick und ohne dass sich die App wieder öffnet. Windows ruft den Installer mit `/NOSTART` auf. Auf macOS startet das Skript die neue Version mit `--nach-update`: Sie lädt ihre Module, bestätigt den Start und endet; schlägt das fehl, kommt die alte zurück. Klappt das Laden oder Installieren nicht, endet die App trotzdem, und das Update wird wieder angeboten.

**Neue Version ausrollen:**
1. `desktop/version.py` erhöhen und committen.
2. Tag `v<Version>` pushen. Die CI baut, installiert und testet die App und legt einen **Release-Entwurf** mit Installer, macOS-Zip und je einer Prüfsummen-Datei an.
3. Den Entwurf prüfen (Installer auf einem Testrechner) und **veröffentlichen**. Erst dann sehen die Apps das Update.

Für das Release zusätzlich mit Code-Signatur (Windows Authenticode, Apple Developer ID); dann entfällt auch die Warnung bei der Erstinstallation (MIN-351).

Die Anleitung für Teilnehmende steht in [`docs/installation.md`](../docs/installation.md); ändert sich der Ablauf, dort nachführen.

## Installation im Pilot (Windows)

1. `Bewerbungsbegleiter-Setup-<Version>.exe` aus dem Release laden und öffnen.
2. Warnung von SmartScreen: „Weitere Informationen“ → „Trotzdem ausführen“ (die App ist im Pilot nicht signiert).
3. Installation ohne Administratorrechte, nach `%LOCALAPPDATA%\Programs\Bewerbungsbegleiter`; Eintrag im Startmenü.
4. Die App öffnet sich im Browser mit der Einrichtung: Datenordner bestätigen, Einstiegsdatei importieren, falls vorhanden, Einladungscode eingeben (oder den Einladungslink anklicken).

Deinstallation über Einstellungen → Apps. Der Datenordner in Dokumente bleibt erhalten.

## Installation im Pilot (macOS)

1. `Bewerbungsbegleiter-<Version>-macOS.zip` aus dem Release laden und im Finder öffnen.
2. **Die App in den Ordner „Programme“ ziehen.** Sonst startet macOS sie aus einem Ersatzordner, und das Update in der App geht nicht.
3. Beim ersten Start warnt macOS: Systemeinstellungen → Datenschutz & Sicherheit → „Dennoch öffnen“ (die App ist im Pilot nur ad hoc signiert).
4. Die App öffnet sich im Browser mit der Einrichtung, wie unter Windows.

Löschen: die App aus „Programme“ in den Papierkorb legen. Der Datenordner in Dokumente bleibt erhalten.

## Bauen

```bash
pip install -r ../requirements.txt -r requirements.txt
cd .. && pyinstaller --noconfirm desktop/bewerbungsbegleiter.spec
dist/Bewerbungsbegleiter/Bewerbungsbegleiter --selbsttest    # baut Lebenslauf und Anschreiben aus den Beispieldaten
```

Den Windows-Installer baut die CI mit Inno Setup (`installer.iss`), siehe `.github/workflows/app.yml`.

## Tests

```bash
python -m pytest -q
```
