# MSIX-Versuch: Erreicht die Erweiterung die App im Paket?

Stand 12.11.2026. Board-Item #255, erster Schritt von #47 (Windows-App als MSIX im Microsoft Store). Gefragt war, bevor jemand das echte Paket für den Store baut: Erreichen Browser-Erweiterung, Einladungslink und Claude Desktop die App noch, wenn sie als MSIX installiert ist?

## Wie geprüft wurde

Der Workflow `.github/workflows/msix-versuch.yml` läuft nur von Hand oder auf einem Pull Request, der ihn selbst oder `desktop/msix/` ändert, nie auf Tags oder `main`. `app.yml` und der Build des Releases bleiben unverändert.

1. Er baut die App wie `app.yml`: Python 3.12, `desktop/bewerbungsbegleiter.spec`.
2. Er packt sie mit `makeappx` nach `desktop/msix/AppxManifest.xml`, mit einer Platzhalter-Identität: Name `BewerbungsbegleiterVersuch`, Publisher `CN=Bewerbungsbegleiter Versuch`. Als Fähigkeit steht nur `runFullTrust` im Manifest, die jede Desktop-App im Store braucht. Keine eingeschränkte Fähigkeit, die eine Freigabe des Stores bräuchte.
3. Er signiert mit einem Wegwerf-Zertifikat, das der Job selbst erzeugt, nur auf dem Runner vertraut (`Cert:\LocalMachine\TrustedPeople`) und am Ende löscht. Kein Schlüssel und kein Zertifikat liegt im Repo oder in den Secrets.
4. Er legt `%APPDATA%\Claude\claude_desktop_config.json` mit `{"mcpServers": {}}` an, wie nach der Installation von Claude Desktop.
5. Er installiert das Paket mit `Add-AppxPackage` und startet die App über ihren Eintrag im Startmenü (`shell:AppsFolder\<Paketfamilie>!Bewerbungsbegleiter`).
6. `desktop/msix/msix_check.py` prüft danach von aussen, aus einem gewöhnlichen Prozess ohne Paket, wie ein Browser oder Claude Desktop.

**Lauf:** https://github.com/minigraphx/bewerbungsassistent/actions/runs/43288103014 (Commit 71117f3, alle fünf Prüfungen gemeldet, dazu die Auswege). Der erste Lauf ohne Auswege, https://github.com/minigraphx/bewerbungsassistent/actions/runs/43285911021, zeigte dieselben fünf Ergebnisse.

## Ergebnisse

| Prüfung | Ergebnis | Was der Lauf zeigte |
| --- | --- | --- |
| 1. Registry-Schlüssel für Native Messaging (Chrome, Edge) | FAIL | `HKCU\Software\Google\Chrome\NativeMessagingHosts\bewerbungsbegleiter` und der Schlüssel von Edge sind von aussen nicht sichtbar. MSIX leitet die Schreibzugriffe der App auf HKCU in eine private Ablage des Pakets um. |
| 2. Manifest des Hosts lesbar, Pfad zeigt auf ein Programm | FAIL | Ohne Registry-Eintrag kein Pfad. Die Datei `native-messaging-host.json` liegt nur umgeleitet unter `%LOCALAPPDATA%\Packages\<Paketfamilie>\LocalCache\Roaming\Bewerbungsbegleiter\`, ebenso der ganze App-Ordner (Einstellungen, `instanz.json`, Protokoll, Ordner der Erweiterung). |
| 3. Host antwortet auf einen Ping von aussen | FAIL (über das Manifest) | Weil kein Manifest sichtbar ist, gibt es den Weg des Browsers nicht. Direkt aus dem Paketordner gestartet (`C:\Program Files\WindowsApps\…\Bewerbungsbegleiter.exe`) antwortet der Host: `ok=True`, Version 0.2.19, er sieht die laufende App. |
| 4. Einladungslink `bewerbungsbegleiter://` von aussen sichtbar | FAIL (Eintrag der App) | Der Schlüssel, den die App selbst schreibt (`HKCU\Software\Classes\bewerbungsbegleiter\shell\open\command`), ist von aussen nicht sichtbar. |
| 5. Wohin der Eintrag für Claude Desktop geht | PASS | Die App meldet `%APPDATA%\Claude\claude_desktop_config.json`. Diese echte Datei enthält danach den Eintrag `bewerbungsbegleiter`, die umgeleitete Kopie im Paket keinen. Eine bestehende Datei ändert die App also an ihrem Ort. |

## Auswege ohne Freigabe des Stores

Im selben Lauf versucht, nur über das Paketmanifest, ohne Änderung am Code der App:

- **Einladungslink über `windows.protocol` (funktioniert).** Mit der Erweiterung `uap3:Protocol Name="bewerbungsbegleiter"` trägt Windows das Schema selbst ein: `HKCU\Software\Classes\bewerbungsbegleiter` mit `URL Protocol` und dem Standardwert `URL:bewerbungsbegleiter`, von aussen sichtbar. Das Öffnen von `bewerbungsbegleiter://einladung?code=VERSUCH-0000` von aussen kam bei der laufenden App an. Ihr Protokoll meldet `Einladung nicht eingelöst: Für diese App ist keine KI-Vermittlung eingerichtet.`, wie erwartet für einen Build ohne Adresse der Vermittlung. Prüfung 4 bleibt FAIL, weil sie nach dem Eintrag der App sucht. Der Weg über das Manifest ersetzt ihn.
- **Host über einen App-Alias (funktioniert).** Mit `uap3:AppExecutionAlias` (`bewerbungsbegleiter.exe`) liegt `%LOCALAPPDATA%\Microsoft\WindowsApps\bewerbungsbegleiter.exe` für alle Prozesse bereit. Von aussen gestartet antwortet der Host auf den Ping (`PASS alias`, `ok=True`) und sieht die laufende App. Der Pfad bleibt über Updates gleich, anders als der versionierte Ordner unter `WindowsApps`.
- **Registry-Schlüssel für Native Messaging: kein Ausweg ohne Freigabe.** Chrome und Edge finden einen Host unter Windows nur über die Registry. Den Schlüssel nach aussen zu schreiben ginge nur ohne Virtualisierung (`desktop6:RegistryWriteVirtualization` und `desktop6:FileSystemWriteVirtualization` auf `disabled`). Das verlangt die eingeschränkte Fähigkeit `unvirtualizedResources`, die der Store einzeln freigeben muss. Das wurde hier bewusst nicht versucht.

## Folgen für #47

1. **Die Erweiterung erreicht die App aus dem Store-Paket nicht, solange sie Native Messaging braucht.** Der Host selbst läuft, und dank des App-Alias gibt es einen festen Pfad dafür. Es fehlt allein der Registry-Eintrag, der Chrome und Edge zu ihm führt. Drei Wege bleiben offen, ein Entscheid für Andy:
   - `unvirtualizedResources` beim Store beantragen und begründen;
   - einen kleinen Schritt ausserhalb des Pakets, der den Eintrag einmal schreibt, zum Beispiel die App fragt und öffnet dafür ein Programm ohne Paket. Ob das erlaubt ist, müsste die Prüfung des Stores zeigen;
   - die Erweiterung spricht ohne Native Messaging mit der App, über den lokalen Server, den die App ohnehin betreibt. Das ist eine Änderung an Erweiterung und App.
2. **Der Einladungslink braucht im Paket `windows.protocol` im Manifest** statt des eigenen Eintrags der App. Die App muss ihn im Paket nicht mehr schreiben.
3. **Das Paket bekommt einen App-Alias** `bewerbungsbegleiter.exe`. Ein künftiges Manifest des Hosts zeigt auf diesen Pfad, nicht auf den Ordner unter `WindowsApps`.
4. **Claude Desktop:** Die Datei wurde am echten Ort geändert, weil sie schon bestand. Ungeprüft bleibt zweierlei:
   - wohin der Eintrag geht, wenn der Ordner `Claude` noch fehlt; vermutlich nur in die Kopie im Paket;
   - ob Claude Desktop, falls selbst als MSIX installiert, seine Einstellungen am selben Ort liest.
5. **Daten der App:** Einstellungen, Protokoll und Ordner der Erweiterung liegen im Paket unter `LocalCache`. Wer von der heutigen Installation (Inno Setup) wechselt, findet sie dort nicht wieder, ohne eine Übernahme wie `desktop/rename_migration.py`. Das betrifft auch den entpackten Ordner der Erweiterung für den Pilot.

## Echte Identität

Das echte Paket für den Store liest später die Identität aus den Variablen des Repos: `MSIX_IDENTITY_NAME`, `MSIX_PUBLISHER` und `MSIX_PUBLISHER_DISPLAY_NAME`. Der Versuch bleibt bei der Platzhalter-Identität, weil ein selbst signiertes Zertifikat genau auf den Publisher lauten muss. Den echten Publisher signiert erst der Store.
