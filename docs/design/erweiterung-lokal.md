# Erweiterung und App über den lokalen Server

Stand 23.11.2026. Board-Item #357, nur Entwurf, kein Code. Andy hat am 16.11.2026 entschieden, das Paket für den Microsoft Store auf 0.4 zu verschieben: Deinstallieren soll nichts zurücklassen, und unter Linux sollen auch Browser als Snap und Flatpak gehen. Hintergrund ist `docs/design/msix-versuch.md`, «Folgen für #47», Punkt 1, dritter Weg: Die Erweiterung spricht ohne Native Messaging mit der App, über den lokalen Server, den die App ohnehin betreibt.

## Heute

- **Erweiterung:** `erweiterung/lib/app.js` öffnet mit `chrome.runtime.connectNative('bewerbungsbegleiter')` einen Port (Zeile 24) und schickt `hallo` und `anfrage`. Dafür steht `nativeMessaging` in `erweiterung/manifest.json` (Zeile 9).
- **Host:** Der Browser startet die App mit dem Origin der Erweiterung als Argument (`desktop/start.py`, `main`, Zeile 110; `desktop/native_host.py`, `invoked`). Der Host liest Port und Token aus `instanz.json` und reicht nur die Routen in `ALLOWED` weiter (`native_host.py`, Zeilen 30–37, `Host.answer`). Läuft die App nicht, startet er sie (`Host.running`, `launch`).
- **Eintrag beim Browser:** Bei jedem Start schreibt die App das Manifest des Hosts, unter Windows dazu vier Schlüssel unter HKCU (`desktop/native_messaging.py`, `register`; `desktop/start.py`, `prepare_extension`). Nur die IDs in `EXTENSION_IDS` stehen in `allowed_origins` (`native_messaging.py`, Zeilen 24–26 und `manifest`).
- **Lokaler Server:** `bewerbungen/server.py` bindet nur `127.0.0.1` (Zeile 114), auf einem freien Port, denn `erstelle_server` übergibt `port=0` (`bewerbungen/app.py`, Zeile 205). Er prüft den Header `Host` gegen DNS-Rebinding (`_host_erlaubt`), verlangt für `/api/` das Token pro Start (GET `t`, POST `X-Token`, `_token_gueltig`) und gibt Seiten nur mit Sitzung heraus (`_page_with_proof`). Port, Token und PID schreibt `desktop/instance.py`, `write`, nur für die Person lesbar (Modus 0600).

Die Erweiterung hat schon `http://127.0.0.1/*` in `host_permissions` und läuft als Inhaltsskript `app-bridge.js` auf Seiten der App (`manifest.json`, `content_scripts`). Neue Berechtigungen braucht der Vorschlag nicht.

## Vorschlag in Kürze

1. Die App lauscht zuerst auf einem von zehn festen Ports. Die Erweiterung probiert den zuletzt bekannten Port und dann diese zehn.
2. Die Erweiterung koppelt sich einmal mit der App, ohne Code und ohne Klick: Bestätigt wird die Kopplung von der Seite der App, die die Person ohnehin offen hat. Danach hat jede Erweiterung ein eigenes Geheimnis.
3. Vor jeder Sitzung beweist die App der Erweiterung, dass sie dieses Geheimnis kennt. Erst dann schickt die Erweiterung Daten.
4. Die App nimmt mit dem Geheimnis nur die Routen an, die heute der Host erlaubt.
5. Läuft die App nicht, startet sie die Erweiterung nicht mehr selbst. Das Popup bietet «App öffnen» über den Link `bewerbungsbegleiter://`.
6. Nach dem Übergang entfernt die App beim Start ihre Einträge für Native Messaging.

## Die App finden

**Heute zufällig.** Der Port ist bei jedem Start ein anderer (`port=0`). Die Erweiterung kann `instanz.json` nicht lesen; sie kennt den Port nur, weil der Host ihn meldet (`hallo` in `native_host.py`, Zeile 182).

**Vorschlag: feste Folge, sonst frei.**

- Die App versucht der Reihe nach zehn feste Ports, etwa `31470` bis `31479` (Beispielwerte, das Item legt sie fest). Sind alle besetzt, nimmt sie wie heute einen freien Port.
- Die Folge liegt unter 32768. Damit bleibt sie ausserhalb der Bereiche, aus denen Windows, macOS und Linux die Ports für ausgehende Verbindungen nehmen: 49152–65535 nach RFC 6335 (https://www.rfc-editor.org/rfc/rfc6335#section-6) und unter Windows (https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/default-dynamic-port-range-tcpip-chang), 32768–60999 als Vorgabe unter Linux (`ip_local_port_range`, https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt).
- Die Erweiterung merkt sich den Port des letzten Erfolgs in `chrome.storage.local` und probiert ihn zuerst, dann die zehn. Ein geschlossener Port auf `127.0.0.1` antwortet sofort mit einer Ablehnung; die Suche dauert also kaum.
- Jede Seite der App meldet ihren Origin über `app-bridge.js`. Liegt die App auf einem freien Port ausserhalb der Folge, lernt die Erweiterung ihn so, sobald eine Seite der App im selben Browser offen ist.

**Warum nicht nur die Seite der App?** Die App öffnet beim Start ihre Seite (`start.py`, `serve`, Zeile 255) und beendet sich eine Minute nach dem letzten Tab (`desktop/presence.py`, G36). Meist ist also eine Seite offen. Seit G99 öffnet sie sich aber im gewählten Browser (`start.py`, `open_app`). Wer die App in Edge öffnet und die Erweiterung in Chrome nutzt, braucht die feste Folge.

**Nebenwirkung:** Mit festem Port bleibt der Origin der Seiten über einen Neustart gleich. `localStorage` der Seiten überlebt dann den Neustart; heute geht er meist verloren, weil der Port wechselt. Das Cookie der Sitzung trägt den Port im Namen (`server.py`, `SESSION_COOKIE`) und wird bei jedem Start neu gesetzt; daran ändert sich nichts.

## Nur die eigene Erweiterung

### Wer die App erreichen kann

| Wer | Was er heute kann | Was der Vorschlag dagegen setzt |
| --- | --- | --- |
| Eine Webseite im Browser der Person | Anfragen an `127.0.0.1` schicken; die Antwort lesen kann sie nicht, denn der Server sendet keine CORS-Header (`server.py`, `_senden`). | Origin muss `chrome-extension://<ID aus EXTENSION_IDS>` sein; den Origin setzt der Browser, eine Seite kann ihn nicht fälschen. Dazu Host-Prüfung, Token oder Geheimnis und Local Network Access (unten). |
| Eine andere Erweiterung | Mit eigener Berechtigung für `127.0.0.1` dieselben Anfragen; mit Zugriff auf die Seiten der App liest sie dort das Token, das in jeder Seite steht (`server.py`, `_seite`). | Ihr Origin trägt ihre eigene ID, Kopplung und Routen der Erweiterung lehnt die App ab. Das Token in der Seite bleibt lesbar wie heute; das ändert der Vorschlag nicht. |
| Ein anderes Konto auf demselben Rechner | Den Port erreichen, aber `instanz.json` nicht lesen (`server.py`, Docstring; `instance.py`, `write`). | Es kann jeden Origin setzen, aber keine Kopplung bestätigen, denn dafür braucht es die Sitzung der Person. Besetzt es einen festen Port, weicht die App auf den nächsten aus, und die Erweiterung schickt ihm nichts, weil es den Beweis nicht liefert. |
| Ein Prozess derselben Person | Alles: Er liest `instanz.json`, den App-Ordner und den Datenordner. | Bleibt so. Er liest dann auch die Datei mit den Geheimnissen der Erweiterungen. Native Messaging schützt davor heute ebenso wenig. |

### Kopplung

1. Der Service Worker erzeugt eine Kennung und ein Geheimnis (32 Zufallsbytes, `crypto.getRandomValues`) und legt beide in `chrome.storage.local` ab. Dieser Speicher gehört nur dieser Erweiterung in diesem Profil und wird nicht synchronisiert.
2. Er schickt `POST /api/erweiterung/kopplung` mit Kennung, Geheimnis und Browser (Chrome oder Edge). Die App nimmt das nur mit dem Origin einer ID aus `EXTENSION_IDS` an und hält es als offen, höchstens fünf Anfragen und zwei Minuten lang.
3. `app-bridge.js` gibt der Seite der App nur die Kennung weiter. Die Seite schickt mit ihrem Token `POST /api/erweiterung/kopplung/bestaetigen` mit dieser Kennung. Erst dann gilt die Kopplung.
4. Die App speichert Kennung, Geheimnis, Browser und Datum in `erweiterungen.json` im App-Ordner, Modus 0600 wie `instanz.json`. Die Kopplung überdauert Neustarts von App und Browser.

Das Geheimnis geht nie durch die Seite. Bestätigt wird nur die Kennung, die die echte Erweiterung über ihr Inhaltsskript meldet; eine offene Anfrage eines anderen Kontos bestätigt niemand. Die Person sieht davon nichts, ausser der Zeile «verbunden» (Abschnitt «Sichtbare Schritte»).

### Jede Sitzung

- **Beweis der App:** `POST /api/erweiterung/hallo` mit Kennung und einer Zufallszahl. Die App antwortet mit HMAC-SHA256 über `bewerbungsbegleiter-app:` und die Zahl, mit dem Geheimnis als Schlüssel. Stimmt der Wert nicht, probiert die Erweiterung den nächsten Port und schickt dem falschen nichts.
- **Anfragen der Erweiterung:** danach mit dem Header `X-Erweiterung: <Kennung>:<Geheimnis>`, auch bei GET, damit nichts davon in einer Adresse steht. Die App vergleicht mit `secrets.compare_digest` wie beim Token.
- **Erlaubte Routen:** Mit diesem Header nimmt der Server nur die Routen aus `ALLOWED` an, die heute in `native_host.py` stehen, dazu `hallo`. Die Liste wandert vom Host in den Server; alles andere lehnt er mit 403 ab.
- **Origin:** Die App prüft den Header `Origin` bei jeder Anfrage mit `X-Erweiterung`. Gegen eine Webseite ist das ein Schutz, gegen einen Prozess nicht, denn der setzt jeden Header. Darum entscheidet das Geheimnis.
- **Einstiegslink:** `hallo` gibt heute `einstieg` zurück, die Adresse mit dem Token der App (`native_host.py`, Zeile 183). Die Erweiterung braucht sie, um die Trefferliste in einem Browser ohne Sitzung zu öffnen (`erweiterung/lib/app-tab.js`, `showHits`). Der Vorschlag ersetzt sie durch einen Link mit einem einmaligen Code, der nur eine Sitzung startet. So erreicht die Erweiterung nie das volle Token.
- **Trennen:** Entfernt die Person eine Kopplung in den Einstellungen, antwortet die App auf diese Kennung mit 403. Die Erweiterung löscht dann ihr Geheimnis und koppelt sich neu, sobald eine Seite der App offen ist.

`erweiterung/lib/senders.js`, `senderKind`, vertraut einer Seite auf `127.0.0.1` heute nur, wenn ihr Origin die Adresse ist, die der Host meldet. Künftig ist es der Origin, dessen App den Beweis geliefert hat.

## Was Chrome und Edge erlauben

- **Host-Berechtigung statt CORS:** Der Service Worker einer Erweiterung darf Server ausserhalb seines Origin erreichen, wenn die Erweiterung dafür eine Host-Berechtigung hat; Inhaltsskripte dürfen das nicht, für sie gilt die Same-Origin-Policy der Seite (https://developer.chrome.com/docs/extensions/develop/concepts/network-requests). Alle Anfragen gehen darum vom Service Worker aus, nie von `app-bridge.js`. `http://127.0.0.1/*` steht schon im Manifest; neue Warnungen beim Update gibt es nur für neue Berechtigungen (https://developer.chrome.com/docs/extensions/develop/concepts/permission-warnings).
- **Private Network Access ist abgelöst.** Die Vorabanfragen (Preflights) von Private Network Access wurden zurückgestellt; Local Network Access ersetzt sie (https://developer.chrome.com/blog/local-network-access). Chrome fragt seit Version 142 nach, wenn eine Seite aus dem öffentlichen Netz das lokale Netz oder `127.0.0.1` erreichen will. Für `127.0.0.1` gilt die Berechtigung `loopback-network` (https://developer.chrome.com/docs/modern-web-guidance/guides/security/local-network-access).
- **Erweiterungen sind ausgenommen.** Microsoft schreibt für Edge ab Version 143, Local Network Access gelte vorerst nicht für Erweiterungen mit den nötigen Host-Berechtigungen (https://learn.microsoft.com/deployedge/ms-edge-local-network-access). Für Chrome sagt das Chrome-Team im Forum dasselbe und nennt einen Fehler, der Erweiterungen trotz Host-Berechtigung traf und ab Chrome 144.0.7512.0 behoben ist (https://groups.google.com/a/chromium.org/g/chromium-extensions/c/pUDh8RiTjJk). Eine Seite der offiziellen Dokumentation von Chrome, die Erweiterungen ausdrücklich nennt, habe ich nicht gefunden.
- **Service Worker ohne Fenster:** Für gewöhnliche Webseiten gilt, dass ein Service Worker die Abfrage nicht selbst auslösen kann; er braucht die Berechtigung schon aus einem Fenster (gleiche Quellen wie oben). Für den Service Worker einer Erweiterung mit Host-Berechtigung sollte das nach der Ausnahme nicht gelten. Das muss der Prototyp zeigen.
- **Die Seiten der App selbst** laufen auf `127.0.0.1` und sprechen mit `127.0.0.1`; Anfragen innerhalb von Loopback lösen keine Abfrage aus (Edge-Dokument oben, Abschnitt zu lokalem Testen).
- **Vorabanfrage OPTIONS:** Der Server kennt kein `do_OPTIONS`. Nach dem Dokument zu Netzwerkanfragen sollte der Service Worker mit Host-Berechtigung keine Vorabanfrage schicken. Ob Chrome und Edge bei `X-Erweiterung` wirklich keine schicken und welchen Origin sie setzen, prüft der Prototyp.

## Wenn die App nicht läuft

**Heute** startet der Host die App, sobald eine Anfrage kommt (`Host.running`, mit `--kein-browser`, `launch_command`). Das Popup fragt bewusst nur `hallo`, damit das Öffnen des Popups die App nicht startet (`erweiterung/background.js`, `status`, Zeile 224); «Treffer in der App ansehen» startet sie dagegen (`openApp`, Zeile 300).

**Künftig** kann die Erweiterung kein Programm starten. Ein Weg bleibt, der schon heute für die Einladung gilt: der Link `bewerbungsbegleiter://`.

- Er ist überall eingetragen: Windows über `urlscheme.register_windows` oder im Paket über `windows.protocol` (`desktop/msix/AppxManifest.xml`, Zeilen 33–35), macOS im Bundle (`desktop/bewerbungsbegleiter.spec`, `CFBundleURLTypes`), Linux über `linux_desktop.register_quietly` (`start.py`, `register_link`).
- Ein Link ohne `einladung` startet die App gewöhnlich (`urlscheme.invitation_code` gibt `None`, `start.main`). Läuft sie schon, öffnet sie ihre Seite erneut.
- Neu bekommt der Link einen Teil `?browser=chrome` oder `?browser=edge`. Die App öffnet ihre Seite dann in diesem Browser statt im gewählten (G99). So landet die Seite dort, wo die Erweiterung sich koppeln kann.
- Das Popup zeigt «App öffnen», und erst der Klick öffnet den Link. Der Browser fragt dann mit seinem eigenen Dialog, ob er die App öffnen darf. Wie Chrome und Edge diesen Dialog für einen Link aus einer Erweiterung zeigen und ob «Immer erlauben» angeboten wird, ist ungeprüft.
- Danach probiert die Erweiterung die Ports bis zu 40 Sekunden lang, so lange wie heute `START_TIMEOUT`. Den Auftrag führt sie nicht von selbst weiter, denn das Popup ist dann zu; die Person klickt nochmals.
- Ist die Erweiterung schon gekoppelt, soll der Link die App ohne neue Seite starten, wie heute `--kein-browser`; ob das trägt, zeigt der Prototyp (Schritt 9 unter «Sichtbare Schritte»).

Eine Suche hält die App wie heute offen, denn die Anfragen laufen über dieselbe Aktivität (`presence.py`, `SEARCH_START`).

## Übergang und Aufräumen

Die Erweiterung aus den Stores aktualisiert sich unabhängig von der App. Darum zwei Schritte:

1. **0.4.0:** Die App bietet die neuen Routen und meldet sich weiter als Host an, ausser im Store-Paket (wie `register_link` dort schon nichts schreibt, `start.py`, Zeile 201). Die Erweiterung 0.4.0 spricht zuerst über den Server und nur, wenn keine App antwortet, über Native Messaging. So geht neue Erweiterung mit alter App und alte Erweiterung mit neuer App.
2. **Sobald die Erweiterung in beiden Stores ausgerollt ist** (Andy gibt frei): Die App entfernt beim Start ihre Einträge, und die Erweiterung verliert `nativeMessaging` und den Rückweg. Die entpackte Erweiterung kommt mit der App (`desktop/extension.py`, `install`) und lädt sich selbst neu (`erweiterung/lib/reload.js`); für sie gibt es keinen Versatz.

**Was die App entfernt,** mit den Namen `bewerbungsbegleiter` und `bewerbungsassistent`:

- Windows: die Schlüssel unter den vier `WINDOWS_KEYS` (`native_messaging.py`, Zeile 32), `native-messaging-host.json` und `native-messaging-host.bat` im App-Ordner;
- macOS und Linux: die Manifeste in `_manifest_dirs`, dazu `native-messaging-host.sh` im App-Ordner.

`forget_old_host` (`native_messaging.py`, Zeilen 84–95) macht das heute für den alten Namen; es wird auf beide Namen und die Dateien erweitert. Fehlt etwas, ist das kein Fehler, nur eine Zeile im Protokoll. Der Installer entfernt die Schlüssel beim Deinstallieren weiterhin (`desktop/installer.iss`, Zeilen 68–76); diese Zeilen bleiben für alte Installationen.

## Linux: Snap und Flatpak

- **Native Messaging geht dort nicht.** Ein strikt eingeschränkter Snap darf kein beliebiges Programm des Rechners starten, also auch keinen Host; der Fehler ist seit Jahren offen (https://forum.snapcraft.io/t/native-messaging-support-in-strictly-confined-browser-snaps/26849, https://bugs.launchpad.net/ubuntu/+source/goopg/+bug/1741074). Chromium gibt es unter Ubuntu nur als Snap. `native_messaging._manifest_dirs` kennt ohnehin nur `~/.config/<Browser>` (Zeile 66).
- **Der lokale Server geht dort.** Die Schnittstelle `network` erlaubt einem Snap jede ausgehende Verbindung als Client und ist automatisch verbunden (https://snapcraft.io/docs/reference/interfaces/network-interface). Ein Flatpak mit `--share=network` hat Netzzugang (https://docs.flatpak.org/en/latest/sandbox-permissions.html); die Browser auf Flathub haben ihn. Keine der beiden Seiten nennt `127.0.0.1` ausdrücklich; der Prototyp prüft es.
- **«App öffnen»** braucht im Snap und im Flatpak den Weg nach aussen über `xdg-open` oder ein Portal. Ob der Link die App dort startet, ist ungeprüft. Antwortet nach 40 Sekunden keine App, sagt das Popup, wie man sie über ihr Programmsymbol öffnet.
- **Entpackte Erweiterung:** Der App-Ordner liegt unter `~/.config/bewerbungsbegleiter` (`desktop/settings.py`, `app_dir`). Ob ein Browser im Snap oder Flatpak dort einen Ordner laden darf, ist ungeprüft. Die Erweiterung aus dem Store braucht das nicht.

## Paket für den Microsoft Store

**Ergebnis: Ohne Native Messaging braucht das Paket `unvirtualizedResources` nicht mehr.** Der zweite Versuch brauchte beide Schalter allein für Schlüssel und Manifest des Hosts (`msix-versuch.md`, «Zweiter Versuch», Folgen 1). Die Variante `store` in `desktop/msix/manifest.py` (`STORE_VARIANT`, Zeile 29) wird zu `standard`: kein `rescap:Capability unvirtualizedResources`, keine `desktop6`-Schalter. `windows.protocol` und der App-Alias stehen schon im Template (`AppxManifest.xml`, Zeilen 33–41).

Was Windows mit eingeschalteter Virtualisierung tut (https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes):

- Neue Dateien und Ordner unter `AppData` landen in einer privaten Ablage des Pakets; die App sieht sie am gewohnten Ort.
- Bestehende Dateien unter `AppData` ändert sie an ihrem echten Ort.
- Schreiben unter HKCU geht in eine private Kopie.
- Beim Deinstallieren entfernt Windows das Paket und alles, was so umgeleitet wurde. Was die App an ihrem echten Ort geändert hat, nennt das Dokument dabei nicht; es bleibt, wie der zweite Versuch für die Schlüssel des Hosts zeigte (`msix-versuch.md`, Zeile Deinstallieren).

**App-Ordner.** `%APPDATA%\Bewerbungsbegleiter` liegt dann unter `LocalCache` des Pakets, wie im ersten Versuch (Prüfung 2). Die App selbst, ein zweiter Start und der MCP-Server über den Alias laufen im Paket und sehen ihn. Von aussen las ihn bisher nur der Host; den gibt es nicht mehr. Bleiben zwei Stellen:

- «Ordner zeigen» für die entpackte Erweiterung (`desktop/routes_setup.py`, Zeilen 109–119) gäbe dem Explorer einen Pfad, den es ausserhalb nicht gibt. Im Store-Paket fällt der Weg über die entpackte Erweiterung weg; die Einrichtung zeigt nur die Stores.
- Wer vorher mit Inno Setup installiert hatte, hat einen echten Ordner `%APPDATA%\Bewerbungsbegleiter`. Nach dem Dokument öffnet die App bestehende Dateien dort am echten Ort, neue Dateien landen privat. Der Ordner wäre dann gemischt. Das ist ungeprüft und gehört in den Versuch des Items unten.

**Claude Desktop.** Die App ändert `%APPDATA%\Claude\claude_desktop_config.json` (`desktop/claude_setup.py`, `desktop_config`). Besteht die Datei, ändert sie sie am echten Ort; das zeigte der erste Versuch (Prüfung 5). Fehlt der Ordner `Claude`, legt `_write` ihn an (Zeile 60), und er landet nach dem Dokument privat, wo Claude Desktop ihn nicht sieht. Vorschlag: Im Store-Paket trägt die App nur ein, wenn die Datei schon besteht, sonst bittet sie, Claude Desktop zuerst einmal zu starten. Der Eintrag bleibt nach dem Deinstallieren zurück und zeigt auf den Alias, den es dann nicht mehr gibt; Claude Desktop meldet den Server dann als nicht erreichbar. «Aus Claude Desktop entfernen» gibt es schon in den Einstellungen. Ungeprüft bleibt, ob Claude Desktop seine Einstellungen am selben Ort liest, wenn es selbst als MSIX installiert ist (`msix-versuch.md`, Folgen 4).

**Link.** `windows.protocol` trägt das Schema von aussen sichtbar ein, und der Link kam bei der laufenden App an (erster Versuch, Auswege). Die App schreibt im Paket keinen eigenen Eintrag (`start.py`, `register_link`). Windows entfernt ihn beim Deinstallieren (zweiter Versuch, Zeile Deinstallieren).

Nach dem Deinstallieren bleiben damit nur der Datenordner, den die Person gewählt hat, und, falls eingetragen, der Eintrag in Claude Desktop.

## Sichtbare Schritte

Verbindlicher Entscheid der UI/UX-Prüfung 23.11.2026. Wo «Sie» steht, gilt im Textsatz mit «du» die Du-Form.

1. **Einrichtung, Schritt «Browser-Erweiterung laden»:** Der Titel bleibt. Wie heute die Knöpfe zu den Stores; der Balken «Wartet auf die Erweiterung» wartet, bis die Erweiterung da und gekoppelt ist. Gelingt es, sagt der Status «Erweiterung verbunden.», danach geht es weiter. Der Hinweis «Zurück in diesem Tab geht es von selbst weiter.» bleibt.
2. **Einrichtung, keine Kopplung 15 Sekunden nach der ersten Anfrage der Erweiterung:**
   - im selben Browser: «Die Erweiterung ist da, aber noch nicht mit der App verbunden.» mit dem Knopf «Seite neu laden»;
   - Erweiterung und Seite in verschiedenen Browsern: «Die Erweiterung ist in Chrome, diese Seite aber in Edge. Verbunden wird sie, wenn die App in Chrome offen ist.» mit dem Hauptknopf «In Chrome weitermachen», der die Einrichtung dort öffnet;
   - ohne jede Anfrage: weiter warten, kein neuer Text.
3. **Einrichtung im Store-Paket, «Klappt es nicht?»:** «Die Erweiterung gibt es für Chrome und Edge. Haben Sie sie in einem anderen Browser hinzugefügt als diese Seite, öffnen Sie die App dort:» (du: «Hast du … öffne …»), dazu «In Chrome öffnen» und «In Edge öffnen», nur für installierte Browser. Ausserhalb des Store-Pakets bleiben die Schritte mit dem Ordner.
4. **Einstellungen, Browser und Erweiterung, Karte «Erweiterung»:** eine Zeile pro Kopplung, «Chrome · verbunden seit 23.11.2026», mit dem unauffälligen Knopf «Trennen»; zwei Profile ergeben zwei Zeilen. Wahlweise dahinter «· zuletzt heute» oder «· zuletzt am …». Ohne Kopplung: «Noch keine Erweiterung verbunden.»
5. **«Trennen»:** Rückfrage «Verbindung mit Chrome trennen? Die Erweiterung verbindet sich wieder, sobald Sie die App in Chrome öffnen. Ganz weg ist sie erst, wenn Sie sie in Chrome entfernen.» mit «Trennen» (normaler Stil, nicht rot) und «Abbrechen».
6. **Gleiche Karte, je installierter Browser ohne Kopplung:** der unauffällige Knopf «App in Edge öffnen» mit dem Hinweis «Ist die Erweiterung dort hinzugefügt, verbindet sie sich von selbst.»
7. **Popup, App läuft nicht:** Titel «Die App ist nicht geöffnet» (bisher «Die App läuft nicht»), Hauptknopf «App öffnen» (bisher «Nochmals verbinden»). «Suche starten», «Stelle prüfen» und «Stelle speichern» sind gesperrt, bis die App antwortet. Darunter «Chrome fragt dann, ob es den Bewerbungsbegleiter öffnen darf. Bitte erlauben.», mit dem Namen des Browsers. Eine Zeile zu «Immer erlauben» gibt es nur, wenn der Prototyp diese Wahl zeigt, und dann mit den Worten des Browsers.
8. **Popup, App offen, Erweiterung nicht gekoppelt:** Titel «Noch nicht mit der App verbunden», Text «Die App ist offen, die Erweiterung aber noch nicht mit ihr verbunden.», Hauptknopf «Verbinden», dieselbe Zeile zum Dialog des Browsers.
9. **Nach dem Klick:** der Dialog des Browsers in seinem Wortlaut. Dann:
   - schon gekoppelt: «App öffnen» startet die App ohne neue Seite (wie `--kein-browser`), und die App bleibt offen, solange die Erweiterung arbeitet (`presence.py`). Das gilt nur, wenn der Prototyp zeigt, dass es geht; sonst öffnet die App ihre Seite;
   - Kopplung nötig: Die App öffnet ihre Seite in diesem Browser. Nach der Kopplung sagt sie «Die Erweiterung ist mit der App verbunden. Im Popup der Erweiterung geht es jetzt weiter.»
10. **Popup während des Wartens:** «Die App wird geöffnet …» mit einem Balken für «beschäftigt». Nach 40 Sekunden «Die App hat sich nicht gemeldet.» und je nach System:
    - Windows: «Bitte den Bewerbungsbegleiter selbst öffnen, etwa über das Startmenü.»
    - macOS: «Bitte den Bewerbungsbegleiter selbst öffnen, etwa über das Dock oder den Ordner Programme.»
    - Linux: «Bitte den Bewerbungsbegleiter selbst öffnen, etwa über das Anwendungsmenü.»
    «App öffnen» bleibt stehen.
11. **Fehler während eines Laufs:** `APP_MISSING` fällt weg. Sichtbar ist nur «Verbindung zur App unterbrochen.»; die Angabe des Browsers (etwa «Failed to fetch») geht ins Protokoll. Der Stand des Laufs sagt weiter «Die Suche wurde unterbrochen. Was schon gefunden war, ist da.»
12. **Store-Paket, Claude Desktop noch nicht eingerichtet:** «In Claude Desktop eintragen» bleibt sichtbar, aber gesperrt, mit «Claude Desktop ist auf diesem Computer noch nicht eingerichtet. Bitte Claude Desktop einmal öffnen und wieder schliessen; danach geht es hier.» Die Seite prüft das erneut, sobald sie den Fokus zurückbekommt.

**Seitenleiste:** Ein Chip zeigt den Stand der Erweiterung im Browser dieser Seite, gemeldet über `app-bridge.js`:

- gekoppelt: «Erweiterung verbunden»;
- da, aber nicht gekoppelt: «Erweiterung nicht verbunden» mit «Verbinden» (lädt die Seite neu);
- keine Erweiterung: wie heute, dazu «Einrichten».

**Muss:**

- Texte nur über `textContent`.
- Der Name des Browsers kommt aus der Kopplung oder dem User-Agent, nie aus einer Eingabe der Seite.
- Keine sichtbaren Zähler für die 15 oder 40 Sekunden.
- «Immer erlauben» nur, wenn der Prototyp es bestätigt.

**Anleitung und Webseite:**

- `docs/installation.md` ändert sich an diesen Stellen: der Schritt zur Erweiterung, die Karte in den Einstellungen, «Häufige Fehler» und der Satz zu Claude Desktop im Store-Paket.
- Bilder, die alte Texte zeigen, werden neu aufgenommen.
- Ein Begleit-Item auf dem Board der Webseite folgt nach den Items, die bauen.
- Die Datenschutzerklärung bleibt, ausser sie nennt Native Messaging.

Unsichtbar bleiben das Entfernen der alten Einträge und der Wechsel des Ports.

## Offen und ungeprüft

- Ob Chrome und Edge bei Anfragen des Service Worker mit `X-Erweiterung` an `127.0.0.1` ohne Vorabanfrage und ohne Abfrage von Local Network Access durchgehen, und welchen `Origin` sie setzen.
- Ob für Chrome eine Mindestversion nötig wird (Fehlerbehebung ab 144.0.7512.0). Heute gilt `minimum_chrome_version` 116.
- Wie Chrome und Edge den Dialog für `bewerbungsbegleiter://` aus einer Erweiterung zeigen, ob sie «Immer erlauben» anbieten, und ob der Link aus Snap und Flatpak die App startet.
- Ob «App öffnen» eine schon gekoppelte App ohne neue Seite starten kann, ohne dass sie sich nach einer Minute wieder beendet.
- Ob Snap und Flatpak `127.0.0.1` des Rechners erreichen.
- Wie sich ein bestehender App-Ordner von Inno Setup unter dem Store-Paket verhält, und wohin der Eintrag für Claude Desktop ohne Ordner `Claude` geht.

## Entwurf der Spec-Zeilen

Nur Text, für Andy. Nicht angelegt.

- **E1** Die Erweiterung spricht mit der App über deren lokalen Server auf 127.0.0.1, nicht über Native Messaging.
- **E2** Die Erweiterung verbindet sich mit der App von selbst, sobald eine Seite der App im selben Browser offen ist; die Person tippt keinen Code. Unter Einstellungen, «Browser und Erweiterung», sieht sie die verbundenen Browser und kann jeden trennen. Die Seitenleiste zeigt, ob die Erweiterung in diesem Browser verbunden ist.
- **E3** Die App nimmt Anfragen nur von einer verbundenen Erweiterung mit einer der eigenen IDs an und nur für die Aufgaben, die die Erweiterung braucht. Die Erweiterung schickt einer App Daten erst, wenn diese bewiesen hat, dass sie die verbundene ist.
- **E4** Läuft die App nicht, zeigt das Popup das und bietet «App öffnen»; die App startet nur nach diesem Klick. Ist die Erweiterung schon verbunden, startet die App ohne neue Seite, sofern der Prototyp das trägt; sonst öffnet sie sich in diesem Browser. Meldet sich die App nicht, sagt das Popup, wie man sie auf diesem System selbst öffnet.
- **E5** Sobald die Erweiterung in beiden Stores ohne Native Messaging auskommt, entfernt die App beim Start ihre Einträge für Native Messaging in allen Browsern.
- **E6** Unter Linux funktioniert die Erweiterung auch in Chromium als Snap und in Browsern als Flatpak.
- **E7** Das Paket für den Microsoft Store braucht keine eingeschränkte Fähigkeit. Nach dem Deinstallieren bleiben nur der Datenordner und, falls eingetragen, der Eintrag in Claude Desktop.

## Items für 0.4

Alle in der Lane `app`. Was die Anleitung oder die Webseite zeigt (Schritte 1–12), bekommt ein Begleit-Item auf dem Board von `minigraphx/bewerbungsbegleiter-webseite` (Item 10). Was an KI, Vermittlung und Update-Server geht, ändert sich nicht; die Datenschutzerklärung bleibt, ausser sie nennt Native Messaging.

| # | Item | Kriterium in einem Satz | Hängt ab von |
| --- | --- | --- | --- |
| 1 | Prototyp: Service Worker an 127.0.0.1 | Ein Test lädt die entpackte Erweiterung in Chrome und Edge (stabil) und hält fest, dass eine Anfrage des Service Worker mit `X-Erweiterung` an `127.0.0.1` ohne Vorabanfrage und ohne Abfrage ankommt und welchen `Origin` sie trägt, ob «App öffnen» eine schon gekoppelte App ohne neue Seite starten und offen halten kann und ob der Browser beim Link «Immer erlauben» anbietet; die Ergebnisse stehen in diesem Dokument. | Freigabe E1 |
| 2 | Feste Ports | Die App lauscht auf dem ersten freien Port der festen Folge und sonst auf einem freien; ein Test besetzt die ersten Ports und sieht die App auf dem nächsten. | 1 |
| 3 | Kopplung und Zugang im Server | `hallo`, `kopplung` und `kopplung/bestaetigen` arbeiten wie beschrieben, `X-Erweiterung` erreicht genau die Routen aus `ALLOWED`, ein falscher Origin oder ein falsches Geheimnis ergibt 403, und `einstieg` trägt nur einen einmaligen Code. | 1 |
| 4 | Erweiterung über den Server | Die Erweiterung findet die App über die Ports, prüft den Beweis, schickt dem falschen Server nichts und fällt auf Native Messaging zurück, wenn keine App antwortet; `node --test` deckt jeden Fall ab. | 2, 3 |
| 5 | Kopplung auf den Seiten | Einrichtung, Einstellungen und Seitenleiste zeigen die Schritte 1, 2 und 4–6 und den Chip nach dem Entscheid der UI/UX-Prüfung, auch für Erweiterung und Seite in verschiedenen Browsern, und eine Seite der App koppelt eine neue Erweiterung ohne Klick. | 3, 4 |
| 6 | «App öffnen» | Der Link `bewerbungsbegleiter://oeffnen?browser=…` startet eine gekoppelte App nach dem Ergebnis von Item 1 ohne neue Seite und öffnet sonst die App in diesem Browser, und das Popup zeigt die Schritte 7–11 mit den Knöpfen «Suche starten», «Stelle prüfen» und «Stelle speichern». | 1, 4 |
| 7 | Store-Paket ohne Fähigkeit | `manifest.py` baut `store` wie `standard`, die App meldet sich im Paket nicht als Host an, zeigt die Schritte 3 und 12, trägt Claude Desktop nur bei bestehender Datei ein, und `msix-versuch.yml` zeigt mit der Variante `standard` die Erweiterung über den Server, den Link und das Deinstallieren ohne Rest. | 3, 4 |
| 8 | Linux mit Snap und Flatpak | Auf einem Linux-Rechner (Andy, Hold) erreicht die Erweiterung aus dem Store die App aus Chromium als Snap und aus einem Browser als Flatpak; das Ergebnis steht in diesem Dokument. | 4 |
| 9 | Alte Einträge entfernen | Beim Start entfernt die App Schlüssel, Manifeste und Startskripte beider Namen, die Erweiterung verliert `nativeMessaging` und den Rückweg; erst nach Andys Freigabe, wenn Erweiterung 0.4 in beiden Stores steht. | 4, Hold |
| 10 | Anleitung, Bilder und Webseite | `docs/installation.md` (Schritt zur Erweiterung, Karte in den Einstellungen, «Häufige Fehler», Satz zu Claude Desktop im Store-Paket), `erweiterung/README.md` und `desktop/README.md` beschreiben den neuen Weg, die Bilder mit alten Texten in `docs/bilder/` sind neu aufgenommen, und das Begleit-Item auf dem Board der Webseite wartet mit `--after` auf dieses Item. | 5, 6, 7 |
