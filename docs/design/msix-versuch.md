# MSIX-Versuch: Erreicht die Erweiterung die App im Paket?

Stand 12.11.2026. Board-Items #255 und #256 (zweiter Versuch, unten), erster Schritt von #47 (Windows-App als MSIX im Microsoft Store). Gefragt war, bevor jemand das echte Paket für den Store baut: Erreichen Browser-Erweiterung, Einladungslink und Claude Desktop die App noch, wenn sie als MSIX installiert ist?

## Wie geprüft wurde

Der Workflow `.github/workflows/msix-versuch.yml` läuft nur von Hand (`workflow_dispatch`), nie auf Tags, Pushes oder Pull Requests. `app.yml` und der Build des Releases bleiben unverändert.

1. Er baut die App wie `app.yml`: Python 3.12, `desktop/bewerbungsbegleiter.spec`.
2. Er packt sie mit `makeappx` nach `desktop/msix/AppxManifest.xml`, mit einer Platzhalter-Identität: Name `BewerbungsbegleiterVersuch`, Publisher `CN=Bewerbungsbegleiter Versuch`. Als Fähigkeit steht nur `runFullTrust` im Manifest, die jede Desktop-App im Store braucht. Keine eingeschränkte Fähigkeit, die eine Freigabe des Stores bräuchte.
3. Er signiert mit einem Wegwerf-Zertifikat, das der Job selbst erzeugt, nur auf dem Runner vertraut (`Cert:\LocalMachine\TrustedPeople`) und am Ende löscht. Kein Schlüssel und kein Zertifikat liegt im Repo oder in den Secrets.
4. Er legt `%APPDATA%\Claude\claude_desktop_config.json` mit `{"mcpServers": {}}` an, wie nach der Installation von Claude Desktop.
5. Er installiert das Paket mit `Add-AppxPackage` und startet die App über ihren Eintrag im Startmenü (`shell:AppsFolder\<Paketfamilie>!Bewerbungsbegleiter`).
6. `desktop/msix/msix_check.py` prüft danach von aussen, aus einem gewöhnlichen Prozess ohne Paket, wie ein Browser oder Claude Desktop.

**Lauf:** https://github.com/minigraphx/bewerbungsassistent/actions/runs/43288103014 (Commit 71117f3, alle fünf Prüfungen gemeldet, dazu die Auswege). Der erste Lauf ohne Auswege, https://github.com/minigraphx/bewerbungsassistent/actions/runs/43285911021, zeigte dieselben fünf Ergebnisse. Beide Läufe kamen über einen vorübergehenden Auslöser auf einem Entwurf eines Pull Requests zustande, weil GitHub einen neuen Workflow erst von Hand starten lässt, wenn er auf `main` liegt. Nach dem Merge startet man ihn unter Actions von `main` aus.

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

## Zweiter Versuch: ohne Virtualisierung der Registry (#256)

Stand 12.11.2026, von Andy freigegeben. Gefragt war, ob Weg 1 aus «Folgen für #47» technisch trägt: die eingeschränkte Fähigkeit `unvirtualizedResources` beim Store beantragen. Ein Paket, das man selbst installiert (Sideloading), darf eingeschränkte Fähigkeiten ohne Freigabe nutzen. Darum lässt sich das auf dem Runner prüfen, bevor jemand einreicht.

Der Workflow hat dafür die Eingabe `variante`, weiterhin nur über `workflow_dispatch`. `desktop/msix/manifest.py` füllt das Manifest je nach Variante:

- `standard`: wie oben, für #255.
- `registry`: `unvirtualizedResources` und `<desktop6:RegistryWriteVirtualization>disabled`, Mindestversion Windows 10 2004.
- `registry-und-dateien`: dazu `<desktop6:FileSystemWriteVirtualization>disabled`.

Identität und Wegwerf-Zertifikat bleiben wie in #255. Am Code der App ändert sich nichts. Die Prüfung 3 ist jetzt geteilt: «host» startet den Host direkt aus dem Paketordner, die neue sechste Prüfung «host-manifest» startet ihn wie Chrome über den Pfad im Manifest, auf das der Registry-Schlüssel zeigt. Danach deinstalliert der Workflow das Paket mit `Remove-AppxPackage` und fragt die Schlüssel erneut ab.

**Läufe** (Commit 18d72b2, Branch `ci/256-msix-unvirtualisiert`):

- `registry`: https://github.com/minigraphx/bewerbungsassistent/actions/runs/43293959372
- `registry-und-dateien`: https://github.com/minigraphx/bewerbungsassistent/actions/runs/43293964233

| Prüfung | `registry` | `registry-und-dateien` |
| --- | --- | --- |
| 1. registry | PASS: Chrome und Edge zeigen auf `%APPDATA%\Bewerbungsbegleiter\native-messaging-host.json` | PASS, gleich |
| 2. manifest | FAIL: Die Datei gibt es dort nicht, sie liegt weiter umgeleitet unter `LocalCache` | PASS: lesbar, `path` zeigt auf `C:\Program Files\WindowsApps\BewerbungsbegleiterVersuch_0.2.19.0_x64__…\Bewerbungsbegleiter.exe`, das existiert |
| 3. host (direkt aus dem Paketordner) | PASS: `ok=True`, Version 0.2.19, sieht die laufende App | PASS, gleich |
| 4. link | PASS: `shell\open\command` der App sichtbar, das Programm existiert | PASS, gleich |
| 5. claude | PASS: Eintrag in der echten `%APPDATA%\Claude\claude_desktop_config.json`; App-Ordner noch unter `LocalCache` | PASS: Eintrag in der echten Datei; App-Ordner jetzt `%APPDATA%\Bewerbungsbegleiter` |
| 6. host-manifest (wie Chrome) | FAIL: kein Pfad, weil das Manifest fehlt | PASS: `ok=True`, Version 0.2.19, sieht die laufende App |
| Deinstallieren | FAIL: Die Schlüssel für Chrome und Edge bleiben; der Link verschwindet | FAIL: gleich |

Der App-Alias antwortete in beiden Varianten (`PASS alias`), der Einladungslink kam bei der laufenden App an wie in #255.

### Folgen für #47

1. **Weg 1 trägt technisch, aber nur mit beiden Schaltern.** Erst wenn auch die Virtualisierung der Dateien aus ist, findet Chrome über Schlüssel und Manifest den Host, und der Host antwortet. Mit der Registry allein zeigt der Schlüssel auf eine Datei, die es ausserhalb des Pakets nicht gibt. Eine Änderung der App, die das Manifest an einen Ort ausserhalb von AppData schreibt, wäre die Alternative. Sie ist nicht geprüft.
2. **Deinstallieren lässt die Schlüssel für Chrome und Edge zurück.** Windows entfernt nur, was es aus dem Paketmanifest selbst eingetragen hat (der Link verschwindet), nicht, was die App geschrieben hat. Die verwaisten Schlüssel zeigen danach auf eine Datei, die nach dem Deinstallieren je nach Variante fehlt oder auf ein gelöschtes Programm zeigt. Chrome meldet dann nur, dass der Host nicht gefunden wird. Das Paket für den Store sollte das in der Begründung offenlegen; aufräumen könnte die App nur, solange sie noch installiert ist (etwa beim Abmelden der Erweiterung).
3. **Der Pfad im Manifest enthält die Version.** Die App schreibt `C:\Program Files\WindowsApps\…_0.2.19.0_…\Bewerbungsbegleiter.exe`. Nach einem Update aus dem Store gibt es diesen Ordner nicht mehr, bis die App einmal startet und das Manifest neu schreibt. Besser zeigt das Manifest im Paket auf den App-Alias `%LOCALAPPDATA%\Microsoft\WindowsApps\bewerbungsbegleiter.exe`, der in beiden Läufen antwortete. Das ist eine kleine Änderung an `desktop/native_messaging.py` für das echte Paket, nicht Teil dieses Versuchs.
4. **Mit beiden Schaltern liegt der App-Ordner wieder unter `%APPDATA%\Bewerbungsbegleiter`,** wie bei der Installation mit Inno Setup. Die Übernahme beim Wechsel (Punkt 5 oben) entfällt dann.

### Entwurf der Begründung für den Store

Partner Center verlangt für eingeschränkte Fähigkeiten eine Begründung. Entwurf, auf Englisch wie die Einreichung:

> Bewerbungsbegleiter is a local job application assistant. Its companion browser extension for Chrome and Edge talks to the app through native messaging. Both browsers find a native messaging host only through a registry key under HKCU\Software\Google\Chrome\NativeMessagingHosts (and the Edge equivalent) that points to a host manifest JSON file. With registry and file system write virtualization in place, the key and the manifest the app writes stay inside the package and the browsers never see them, so the extension cannot reach the app. We therefore declare unvirtualizedResources and disable RegistryWriteVirtualization and FileSystemWriteVirtualization. The app writes only these host keys (Chrome, Edge, Chromium, Brave), the key of its own URL scheme under HKCU\\Software\\Classes\\bewerbungsbegleiter (also declared in the package manifest), its own folder under %APPDATA%\Bewerbungsbegleiter and, when the user asks for it, its entry in the Claude Desktop configuration file. It writes nothing outside the current user's profile and no machine-wide settings. The keys are not removed automatically on uninstall; they then point to a missing host, which the browsers ignore.

## Echte Identität

Das echte Paket für den Store liest später die Identität aus den Variablen des Repos: `MSIX_IDENTITY_NAME`, `MSIX_PUBLISHER` und `MSIX_PUBLISHER_DISPLAY_NAME`. Der Versuch bleibt bei der Platzhalter-Identität, weil ein selbst signiertes Zertifikat genau auf den Publisher lauten muss. Den echten Publisher signiert erst der Store.
