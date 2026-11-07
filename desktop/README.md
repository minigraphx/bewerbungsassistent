# Desktop-App

Modul des [Bewerbungsbegleiters](../README.md) für den Pilot (MIN-342): die lokale Oberfläche (`bewerbungen/app.py`) als installierbare App für Windows, macOS und Linux (AppImage, #73), ohne Python, Terminal oder Repo.

- **Start per Doppelklick:** Server auf `127.0.0.1`, der Browser öffnet sich. Ein zweiter Start öffnet die laufende App. „Übersicht“, „Stellen suchen“ und „Meine Angaben“ stehen oben; „Beenden“, die Einrichtung und die übrigen Seiten stehen im Menü „Mehr“.
- **Einrichtung** (Seite `/einrichtung`, beim ersten Start automatisch): 1. Datenordner wählen, Vorschlag `Dokumente\Bewerbungsbegleiter` (unter Windows auch, wenn Dokumente in OneDrive liegt); erlaubt sind ein neuer, ein leerer oder ein bestehender Datenordner, nie ein Ordner mit anderen Dateien oder einer der App. 2. Einstiegsdatei (`einstieg.zip` oder `.json`) importieren, falls vorhanden (`onboarding/import_bundle.py`). 3. Einladungscode für die KI. 4. Browser-Erweiterung laden (siehe unten). Ordner und Datei kommen aus dem Auswahldialog des Systems (`dialogs.py`: PowerShell, AppleScript, unter Linux zenity oder kdialog), weil der Browser keine Pfade liefert und die ZIP-Datei grösser sein darf als eine Anfrage. Ein Wechsel des Datenordners gilt sofort, ohne Neustart. Fehlt der Ordner (z.B. USB-Stick), führt jede Seite zur Einrichtung.
- **Meine Angaben** (Seite `/angaben`, `routes_angaben.py`): das Formular für die Grundlagen, gebaut aus denselben Quellen. Ohne Lebenslauf und Suchprofil führen Einrichtung und Übersicht dorthin. Der Zwischenstand liegt in `dokumente/angaben-stand.json`, weil der Port bei jedem Start wechselt und der Speicher des Browsers verloren ginge. PDF- und Word-Dateien kommen beim Hochladen sofort nach `dokumente/<art>/`. „Übernehmen“ nutzt dieselben Prüfungen wie der Import einer Datei; Vorhandenes wird nur auf Wunsch ersetzt, der alte Stand bleibt als Entwurf.
- **App-Ordner:** Einstellungen und Protokoll in `%APPDATA%\Bewerbungsbegleiter`, macOS `~/Library/Application Support/Bewerbungsbegleiter`, Linux `~/.config/bewerbungsbegleiter`. Bis ein Datenordner gewählt ist, läuft die App auf `noch-kein-datenordner` darin.
- **Einladung:** Der Link `bewerbungsbegleiter://einladung?code=…` öffnet die App und löst den Code ein; der Zugang kommt in den Schlüsselbund des Systems (Linux: Secret Service; ohne ihn sagt die App, was fehlt, und legt nichts unverschlüsselt ab). Alternativ den Code in der Einrichtung oder auf der Seite einer Bewerbung eintippen.
- **Adresse der KI-Vermittlung:** kommt beim Bauen aus der Repository-Variable `KI_URL` (kein Geheimnis) in `voreinstellungen.json` im Paket.
- **Adresse des Update-Servers:** ebenso aus der Variable `UPDATE_URL`. Ein Tag-Build ohne sie bricht ab, sonst bekäme das Release nie mehr Updates.

## Browser-Erweiterung

Die App ist zugleich der **Native-Messaging-Host** für die [Erweiterung](../erweiterung/README.md) (MIN-339). Startet Chrome sie mit `chrome-extension://…` als Argument, öffnet sie keine Oberfläche, sondern reicht die Anfragen der Erweiterung an die laufende App weiter (`native_host.py`). Läuft keine, startet sie sie im Hintergrund. Erlaubt sind nur Suchplan, Sichten, Treffer und Abschluss der Suche.

- **Anmeldung beim Browser** bei jedem Start (`native_messaging.py`): Windows über die Registry (`HKCU\Software\Google\Chrome\NativeMessagingHosts` und Edge) mit der Datei im App-Ordner; macOS und Linux mit einer Datei in den Profilordnern von Chrome, Chrome Beta, Edge, Chromium und Brave. Beim Start aus dem Repo verweist sie auf ein kleines Startskript im App-Ordner.
- **Ordner der Erweiterung:** Die App kopiert die Erweiterung aus dem Paket nach `<App-Ordner>/erweiterung`, wenn sich die Version geändert hat (`extension.py`). Die Einrichtung (Schritt 4) öffnet per Knopf die Erweiterungsseite von Chrome oder Edge und zeigt den Ordner im Finder bzw. Explorer.

## Claude mit dem eigenen Abo

Mit `--mcp` ist die App ein lokaler MCP-Server über stdin und stdout (MIN-377), für Claude Desktop und Claude Code. `mcp_server.py` spricht das Protokoll, `mcp_tools.py` legt fest, was Claude erreicht: Das ist die Grenze. Kein Versand, kein RAV, keine Formulare, keine Schlüssel. Der Zugang ist aus, bis die Person ihn unter „Erweiterte Einstellungen“ einschaltet (`routes_claude.py`, `claude_setup.py`). Anleitung für Nutzer: [`docs/eigenes-abo.md`](../docs/eigenes-abo.md). Eine App darf ein Abo nicht selbst nutzen, darum bleibt die KI auf diesem Weg in Claude.

## Updates

Die App fragt beim Start und danach höchstens alle 6 Stunden die Datei `latest.json` auf dem Update-Server ab. Der Server sieht dabei die IP-Adresse; das steht im Datenschutztext. Eine neue Version erscheint auf der ersten Seite nach dem Start in einem Dialog mit „Installieren“ und „Später“ (#32). „Später“ gilt bis zum nächsten Start der App; bis dahin steht ein Banner oben auf den Seiten.

**Signatur (MIN-403):** Auf dem Hosting liegen auch andere Websites, darum vertraut die App dem Server nicht. `latest.json` enthält Version und Prüfsummen und ist mit Ed25519 signiert. Die App installiert nichts ohne gültige Signatur gegen den Schlüssel in `update_key.py` und baut die Adressen der Pakete selbst aus der eigenen Update-Adresse. Der private Schlüssel liegt nur als Geheimnis der GitHub-Umgebung `update-ausrollen` und in Andys Passwortmanager, nie auf dem Hosting. Geht er verloren, kann keine installierte App mehr automatisch aktualisieren: Dann braucht es einen neuen Schlüssel und eine Neuinstallation von Hand.

Bewusst offen: Die Ankündigung hat kein Ablaufdatum. Wer den Server kontrolliert, kann eine ältere signierte Ankündigung zeigen und so ein neueres Update zurückhalten. Installieren lässt sich damit nur, was einmal signiert wurde, und nie eine ältere Version als die laufende.

- **Windows:** „Installieren“ (im Banner „Jetzt aktualisieren“) lädt den Installer, prüft seine SHA-256-Prüfsumme aus `latest.json` und installiert still über die bestehende Version. Danach startet die neue Version selbst. Datenordner, Einstellungen und Zugang bleiben.
- **macOS:** „Installieren“ lädt das Zip, prüft es gegen die Prüfsumme aus `latest.json` und entpackt es in den versteckten Ordner `.Bewerbungsbegleiter-update` neben der App (`ditto`, Rechte und Symlinks bleiben). `codesign --verify --deep --strict` prüft das Paket. Nach dem Beenden tauscht ein kleines Skript alte und neue Version und startet die neue. Die alte bleibt liegen, bis die neue ihren Start bestätigt; sonst kommt sie nach 2 Minuten zurück und die App nennt die Version nicht mehr zum automatischen Update. Datenordner und Einstellungen bleiben.
  - **Ort:** Die App muss aus einem beschreibbaren Ordner laufen, am besten „Programme“. Startet macOS sie aus einem Ersatzordner (App Translocation, typisch direkt nach dem Download) oder darf sie den Ordner nicht schreiben, zeigt das Banner „Zuerst in den Ordner Programme verschieben“ und den Link zum Release.
  - **Erstmals von Hand:** Erst die Version mit diesem Weg kann sich selbst aktualisieren.
- **Beim Beenden (MIN-382):** Wartet ein Update und könnte die App es selbst installieren, läuft nach „Beenden“ derselbe Weg im Hintergrund, ohne Klick und ohne dass sich die App wieder öffnet. Windows ruft den Installer mit `/NOSTART` auf. Auf macOS startet das Skript die neue Version mit `--nach-update`: Sie lädt ihre Module, bestätigt den Start und endet; schlägt das fehl, kommt die alte zurück. Klappt das Laden oder Installieren nicht, endet die App trotzdem, und das Update wird wieder angeboten.

**Neue Version ausrollen:**
1. `desktop/version.py` erhöhen und committen.
2. Tag `v<Version>` pushen. Die CI baut, installiert und testet die App und legt einen **Release-Entwurf** mit Installer, macOS-Zip, AppImage und je einer Prüfsummen-Datei an. Das AppImage installiert sich nicht selbst; unter Linux verlinkt die App das AppImage der neuen Version auf dem Update-Server (`latest.json` nennt es mit Prüfsumme, #102).
3. Den Entwurf prüfen (Installer auf einem Testrechner) und **veröffentlichen**. Erst dann sehen die Apps das Update: `update-ausrollen.yml` lädt die Pakete und zuletzt die signierte `latest.json` auf den Server und vergleicht, was er ausliefert. Vorabversionen rollt der Workflow nicht aus.
4. Bricht der Workflow ab, sehen die Apps weiter die alte Ankündigung. Dann den Workflow von Hand mit dem Tag nochmals starten.

Das Release bleibt auch auf GitHub stehen: Installationen bis 0.2.11 fragen dort nach, und die Installationsanleitung verweist darauf. Die Prüfsummen-Dateien des Builds gehören darum weiter ins Release; `release_manifest.py` vergleicht sie mit den Paketen.

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

## Linux (AppImage, #73)

Zugesagt ist das aktuelle Ubuntu LTS; gebaut wird auf Ubuntu 22.04, damit das Paket auch auf neueren Systemen und Mint läuft. Ein AppImage läuft aus einem temporären Einhängepunkt, darum bekommt alles, was die App später startet, die Datei selbst aus `$APPIMAGE` (`linux_desktop.py`): Native Messaging, Claude Desktop und der Einladungslink.

- **Menüeintrag und Einladungslink:** Bei jedem Start schreibt die App `~/.local/share/applications/bewerbungsbegleiter.desktop` mit `MimeType=x-scheme-handler/bewerbungsbegleiter` und meldet sich mit `xdg-mime` dafür an. Wird das AppImage verschoben, gilt beim nächsten Start der neue Pfad.
- **Laufzeit:** Die statische Laufzeit von AppImage braucht FUSE (`fusermount3` aus `fuse3`), nicht mehr `libfuse2`. Ohne FUSE läuft die App mit `--appimage-extract-and-run`, dann aber nicht für die Erweiterung.
- **Browser:** Chrome, Edge, Chromium und Brave als normales Paket. Als Snap oder Flatpak dürfen sie kein Programm ausserhalb starten; Native Messaging geht dort nicht.
- **CI:** `appimage.py` baut das AppDir und ruft appimagetool mit der gepinnten Laufzeit auf (Werkzeuge mit Prüfsumme in `app.yml`). Getestet werden der Selbsttest mit und ohne FUSE, MCP und `linux_smoke.py`: Start in einem leeren Benutzerordner, Menüeintrag und Link, Native Messaging über die AppImage-Datei, Einladungslink an die laufende App.

## Bauen

```bash
pip install -r ../requirements.txt -r requirements.txt
cd .. && pyinstaller --noconfirm desktop/bewerbungsbegleiter.spec
dist/Bewerbungsbegleiter/Bewerbungsbegleiter --selbsttest    # baut Lebenslauf und Anschreiben aus den Beispieldaten
```

Den Windows-Installer baut die CI mit Inno Setup (`installer.iss`), das AppImage mit `appimage.py`, siehe `.github/workflows/app.yml`.

## Tests

```bash
python -m pytest -q
```
