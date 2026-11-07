# Browser-Erweiterung

Modul des [Bewerbungsbegleiters](../README.md) (MIN-339): Die Erweiterung für Chrome und Edge sucht nach dem Suchprofil: Stellen auf job-room, jobs.ch, jobscout24 und ictjobs, Lehrstellen auf LENA (berufsberatung.ch) und yousty. Sie sucht im Browser der Person, mit deren IP und Logins, und nur, wenn die Person die Suche startet. Die Treffer gehen über Native Messaging an die [Desktop-App](../desktop/README.md); dort erscheinen sie auf der Seite „Stellen suchen“.

Im Pilot wird sie als **Entwicklererweiterung** geladen („Entpackte Erweiterung laden“). Für die Stores baut `desktop/store_package.py` die ZIP-Datei: ohne Tests und ohne das Feld `key`, denn dort vergibt der Store die ID. Diese ID muss in `EXTENSION_IDS` (`desktop/native_messaging.py`) stehen, sonst lässt die App die Store-Fassung nicht zu.

## Einrichten

Die App zeigt die Schritte auf der Seite **Einrichtung → Schritt 5** mit dem passenden Ordner:

1. Die App einmal starten. Sie meldet sich bei Chrome und Edge als Native-Messaging-Host an und legt den Ordner der Erweiterung in ihrem App-Ordner ab (`…/Bewerbungsbegleiter/erweiterung`). Beim Start aus dem Repo nimmt sie direkt diesen Ordner.
2. In der Einrichtung „In Chrome öffnen“ bzw. „In Edge öffnen“ klicken: Die Erweiterungsseite und der Ordner gehen auf. Einmalig den **Entwicklermodus** einschalten. Von Hand: `chrome://extensions` oder `edge://extensions`.
3. **„Entpackte Erweiterung laden“** und den Ordner wählen (auf dem Mac im Dialog mit Cmd+Shift+G den Pfad einfügen).
4. Der Knopf „Jetzt suchen“ auf der Seite „Stellen suchen“ ist jetzt aktiv, auch ohne dass offene Seiten der App neu geladen werden müssen.

Ein Klick allein genügt nicht: Chrome lässt Apps seit Version 137 keine Erweiterungen mehr selbst laden (`--load-extension`), Richtlinien gelten nur auf verwalteten Geräten. Das ändert erst der Store.

Die ID der entpackten Erweiterung ist fest (`ghniboofenadplgmdgddmgjaaeeogejn`), weil `manifest.json` den öffentlichen Schlüssel enthält. Die Stores vergeben eine eigene ID, Edge `mcbcijjbklfeffbollnemgkgnabnmfmp`. Nur die IDs in `EXTENSION_IDS` (`desktop/native_messaging.py`) dürfen mit der App sprechen. Nach einem Update der App lädt sich die entpackte Erweiterung selbst neu, sobald die App läuft und keine Suche, kein Formular und kein Lauf im Job-Room offen ist, einmal pro Version (`lib/reload.js`, MIN-382). Eine Fassung aus dem Store hat `update_url` und bleibt beim Store. Klappt es nicht, zeigt die Einrichtung einen Hinweis; dann in `chrome://extensions` auf „Neu laden“ klicken. Ist der Entwicklermodus aus, deaktiviert Chrome entpackte Erweiterungen ohnehin.

## Ablauf einer Suche

1. Start im Popup der Erweiterung oder mit „Jetzt suchen“ auf der Seite „Stellen suchen“.
2. Die Erweiterung holt den **Suchplan** von der App (`GET /api/suche/plan`, gebaut aus `suchprofil.md`): Stichworte, Orte, PLZ, Kantone, Titelfilter und Portale. Ohne Region steht `schweizweit` im Plan: Dann folgen nach den Abfragen am Wohnort dieselben Stichworte ohne Ort.
3. Pro Portal öffnet sie einen Tab im Hintergrund und führt dort die Anpassung aus `portals/` aus (`fetch` auf derselben Seite, wie im Skill `jobsuche`). Grenzen: höchstens 3 Seiten pro Abfrage, 30 Abfragen pro Portal, 150 neue Inserate pro Portal und Lauf (die nahen zuerst, der Rest beim nächsten Lauf), Inserate bis 45 Tage alt, 0,6 Sekunden zwischen den Abrufen.
4. Die Trefferliste geht zuerst an die App zum **Sichten** (`POST /api/suche/sichten`): bekannte Stellen, ausgeschlossene Titel und zu alte Inserate fallen weg. Dieselbe Stelle von einem anderen Portal (gleiche Firma, gleicher Titel, gleicher Ort) hängt die App gleich als weiteren Link an. Nur für die übrigen holt die Erweiterung den Volltext.
5. Die Treffer gehen in Zehnergruppen an die App (`POST /api/suche/treffer`), am Ende die Zusammenfassung pro Portal (`POST /api/suche/abschluss`). Ein Inserat, das nicht lädt (z.B. zu viele Abrufe), schickt sie nicht; es kommt bei der nächsten Suche wieder. Ändert ein Portal seine Seiten, gibt es mehr Abfragen als erlaubt oder fehlen Texte, steht das als Problem bei der letzten Suche.

Die App nimmt über den Host nur diese vier Anfragen und die zwei für die offene Seite (siehe unten) an. Alles andere lehnt der Host ab. Die Erweiterung selbst nimmt Aufträge nur vom Popup und von der Seite der laufenden App an; eine andere Seite auf `127.0.0.1` mit demselben Kennzeichen wird abgewiesen, weil ihre Adresse nicht die ist, die die App über Native Messaging meldet (`lib/senders.js`).

**Zuschauen (MIN-370):** Die Suche läuft im Hintergrund. Mit dem Häkchen unter „Suche einstellen“ läuft sie im sichtbaren Tab, damit man mitverfolgen kann, was die Erweiterung tut. Die Einstellung kommt mit dem Suchplan, gilt also auch für einen Start im Popup. Ein Balken sagt, dass der Browser gesteuert wird, und bietet „Suche abbrechen“. Den Tab zu schliessen bricht die Suche ebenfalls ab; was schon an die App ging, bleibt. Wer im Tab etwas anklickt, kann die Abfragen stören, darum die Bitte im Balken: Das betroffene Portal meldet dann ein Problem, die übrigen laufen weiter.

## Weitere Seiten durchsuchen (MIN-348)

Nur mit eigenem API-Schlüssel, die Adressen trägt die Person in der App unter „Erweiterte Einstellungen“ ein.

- **Zugriff:** Das braucht den optionalen Zugriff auf alle Seiten. Die Erlaubnis gibt die Person selbst, in einem eigenen Tab (`erlauben.html?fuer=suche`). Fehlt sie, läuft die Suche auf den Portalen trotzdem und nennt die fehlende Erlaubnis in der Zusammenfassung.
- **Ablauf:** Die Person trägt nur die Adresse ein (MIN-387). `lib/sites.js` öffnet sie im Tab, schickt Text und Linktexte an die App (`POST /api/suche/seite-lesen`) und sucht danach über das Suchformular der Seite, wenn es eines gibt: nur `method=get`, nur auf derselben Seite, ohne Passwortfeld; das Ausfüllen und Abschicken ersetzt ein Aufruf der fertigen Adresse, die Seite wird nicht bedient. Adressen mit `{begriff}` und `{ort}` laufen wie bisher. Die App nennt die Stellen zurück; deren Inserate liest die Erweiterung ebenfalls im Tab, mit einer Pause dazwischen. Danach gehen sie denselben Weg wie die Treffer der Portale.
- **Grenzen:** Nur die erste Ergebnisseite, höchstens 10 Seiten (die Startseite mitgezählt) und 30 Inserate pro Seite, was zum Suchbegriff passt zuerst. Sie folgt nur Links auf derselben Seite und klickt oder schickt nichts ab. Das Öffnen geschieht mit den Cookies der Person; ein Link wie `/logout` in der Liste würde also aufgerufen, wenn die KI ihn als Stelle nennt. Leitet eine Seite auf eine andere um, hört die Suche dort auf.
- **Abgeben:** Wird der Schlüssel entfernt, gibt die Erweiterung den Zugriff ab, spätestens beim nächsten Kontakt mit der App. Danach lädt sie sich neu (`lib/reload.js`), denn Chrome entzieht mit `<all_urls>` auch die Portale aus dem Manifest, bis die Erweiterung wieder geladen ist. Während einer Suche, offener Formulare oder eines Laufs im Job-Room wartet sie damit. Das betrifft auch Formulare (MIN-346): Dort fragt sie beim nächsten Formular neu. Ist der Schlüsselbund gesperrt, ändert sich nichts.

## Stelle auf der offenen Seite prüfen oder speichern (MIN-345)

Für Inserate ausserhalb der Portale, zum Beispiel auf LinkedIn oder den Karriereseiten von Firmen. Die Person öffnet das Inserat selbst und klickt auf das Symbol der Erweiterung.

- **Zugriff:** `activeTab`. Der Klick auf das Symbol gibt für diesen einen Tab Zugriff; ohne Klick liest die Erweiterung auf fremden Seiten nichts und navigiert nicht. Gelesen wird beim Öffnen des Popups, damit Stelle und Firma vorausgefüllt sind. Hinaus geht erst etwas nach einem Knopfdruck.
- **Lesen (`lib/page-ad.js`):** zuerst markierter Text, dann die strukturierten Daten der Seite (schema.org `JobPosting`), sonst der sichtbare Text des Hauptteils der Seite, wenn er nach Inserat aussieht. Dann sagt das Popup, dass der ganze Seitentext gelesen wurde, denn so kann mehr als das Inserat an die KI gehen (etwa Namen aus Seitenleisten). Stelle und Firma lassen sich im Popup korrigieren. Findet sie kein Inserat, sagt sie das und speichert nichts; markierter Text hilft dann weiter. Inhalte in eingebetteten Rahmen fremder Adressen sind nicht erreichbar, auch dort hilft Markieren nicht immer.
- **Adresse:** Die KI bekommt die Adresse der Seite nicht. Im Register steht sie ohne Tracking- und Sitzungswerte (`utm_*`, `refId`, `midToken` und ähnliche).
- **LinkedIn:** Angemeldet fehlen dort die strukturierten Daten. Stelle und Firma kommen dann aus dem Titel des Tabs („Stelle | Firma | LinkedIn“), die Firma sonst aus dem Link auf ihre Seite neben dem Titel des Inserats, und die Adresse wird zu `/jobs/view/<Nummer>/`, auch wenn das Inserat neben einer Liste offen ist. Der Aufbau ist nicht am echten LinkedIn geprüft; im Popup lässt sich alles korrigieren.
- **Ohne KI:** „Stelle speichern“ braucht weder Einladung noch Schlüssel. Nur „Stelle prüfen“ ruft die KI auf.
- **„Stelle prüfen“** (`POST /api/seite/pruefen`): Note mit Begründung, bestehende Bewerbung und Bewerbungen bei derselben Firma. Gespeichert wird nichts. Anweisungsartige Zeilen im Inserat meldet die KI als auffällig; das Popup zeigt sie rot.
- **„Stelle speichern“** (`POST /api/seite/speichern`): neue Bewerbung im Register mit `stelle.md` und, falls geprüft, mit der Note. Gleicher Link mit gleichem Titel oder gleiche Firma mit gleichem Titel ergeben keinen zweiten Eintrag; das Popup nennt den bestehenden. Mehrere Inserate unter einer Adresse bleiben getrennt, und nach einer Absage lässt sich dieselbe Stelle neu erfassen.

Das Ergebnis bleibt für diese Seite erhalten, auch wenn das Popup zwischendurch zugeht.

## Bewerben über Formulare

In der Übersicht der App klickt die Person bei „Das steht an“ auf **Formular öffnen**, oder auf **Formulare öffnen**, wenn mehrere Bewerbungen bereit sind (bis zu fünf pro Durchgang, MIN-346). Die App prüft sie (Unterlagen, Link, Doppelbewerbungen), die Erweiterung öffnet pro Bewerbung einen Tab und füllt das Formular aus.

**Die Erweiterung füllt aus, die Person entscheidet und schickt ab:**

- Sie drückt nie einen Knopf, der etwas absendet, setzt keine Häkchen, Einwilligungen oder Optionsfelder und meldet sich nirgends an. Ein Passwortfeld hält den Tab an.
- Versteckte Felder bleiben leer, Vorhandenes bleibt stehen, und was die Person löscht, wird nicht wieder gefüllt.
- Unklare Felder bleiben leer und orange markiert, Einwilligungen rot, Ausgefülltes grün, Textentwürfe blau.
- Hochgeladen werden nur Dateien dieser Bewerbung: Lebenslauf, Anschreiben, Arbeitszeugnisse, die ZIP-Datei mit den gewählten Zertifikaten und das gemeinsame PDF, das die App ohne KI baut, wenn mehrere Dateien auf ein Feld für nur eine Datei passen. Ein Upload-Feld ohne klare Bedeutung bleibt offen, ausser die KI ordnet ihm anhand der Beschriftung eine Dateiart zu; dann ist es blau markiert und im Balken genannt. Felder für Foto, Ausweis, Strafregisterauszug, Arbeitsprobe und Ähnliches bleiben immer offen, auch ohne KI-Anfrage.
- Für alles, was offen bleibt, legt „Dateien im Ordner zeigen“ die Dateien in einen Ordner und nennt den Pfad. Der steht nur im Balken, den die Seite nicht lesen kann. Den Datei-Dialog in diesen Ordner zu lenken, erlaubt der Browser nicht.
- Der Versand wird erst erfasst, wenn die Person im Balken „Abgeschickt? Ja“ drückt. Hat das Formular eine Datei von der App bekommen, wird genau diese Fassung festgehalten; sonst die aktuelle.

**KI für offene Felder:** Ist in der App eine KI eingerichtet, fragt die Erweiterung nach den Regeln die App nach den Feldern, die noch offen sind:

- **Zuordnung:** Die KI sieht nur, was die Seite zeigt (Beschriftung, Feldname, Hinweis, Auswahlwerte), und nennt einen der festen Schlüssel oder „unklar“. Sie bekommt keinen Wert der Person; den Wert trägt die Erweiterung selbst ein.
- **Entwürfe für Freitextfragen:** Sie entstehen aus Lebenslauf, Bausteinen, Anschreiben und Inserat, pseudonymisiert, sind blau markiert und im Balken gezählt. Die Person prüft sie vor dem Abschicken. Fragen, die die Unterlagen nicht belegen, und Fragen zu Lohn, Gesundheit, Herkunft und ähnlichem bleiben leer. Ein Entwurf mit Adresse, Telefon, E-Mail, Links, Geburtsdatum oder Referenzen wird verworfen.
- **Was nie an die KI geht:** versteckte Felder, Häkchen, der Inhalt von Dateien (von einem Upload-Feld nur, was die Seite dazu zeigt), Felder zu anderen Parteien (Arbeitgeber, Referenzen, Schule) und Felder mit Inhalt. Auf einer Seite mit Passwortfeld fragt sie gar nicht.
- **Kosten:** höchstens 12 Felder pro Anfrage und 8 Anfragen pro Tab. Eine Antwort gilt für den Tab weiter, auch nach dem Neuladen. Scheitert die KI, bleibt das Formular nach Regeln ausgefüllt, und der Balken nennt den Grund.

Texte der Seite sind Daten, keine Anweisungen. Zeilen, die sich an eine KI richten, meldet der Balken.

**Zugriff:** Formulare liegen auf beliebigen Seiten, darum fragt die Erweiterung beim ersten „Formular öffnen“ auf `erlauben.html` einmal um Zugriff auf alle Seiten (`optional_host_permissions`). Sie nutzt ihn nur für Tabs aus ihrer eigenen Liste (`storage.session`). Ohne Frage zählen nur die Adresse nach dem ersten Laden und ihre Subdomains; bei jeder anderen fragt der Balken zuerst („Hier ausfüllen“). Das gilt auch hinter „Jetzt bewerben“: Diesem Link folgt sie einmal, wenn auf der Seite kein Formular ist, die Seite bestimmt aber nicht, wohin die Angaben gehen. Die Werte gehen nur an die geprüften Dokumente, nicht an das, was der Tab inzwischen zeigt.

**Seiten und Rahmen:** Ein Formular braucht mindestens drei sichtbare Felder ohne Häkchen, sonst bleibt der Rahmen unberührt (Suchfelder, Newsletter, Filter). Neue und neu eingeblendete Felder werden nachgefüllt, die nächste Seite derselben Adresse ebenfalls, später gebaute Rahmen auch. Knöpfe drückt sie nur auf Seiten ganz ohne Felder und nie in einem Formular.

## Lehrstellen

Abschnitt „Gesucht“ im Suchprofil oder die Wahl auf der Seite „Stellen suchen“ legen fest, ob Lehrstellen, Schnupperlehren oder beides gesucht werden (MIN-373; Listen `lehrstellen` und `schnupperadressen` auf LENA, `lehrstellen` und `schnupperlehren` auf yousty). Schnupperlehren sind in der App eigene Treffer, und „Übernehmen“ legt eine Anfrage statt einer Bewerbung an.

Hat das Suchprofil einen Abschnitt „Lehrbeginn“, sucht die Erweiterung nur auf LENA und yousty, pro Beruf im gewählten Umkreis um den Wohnort (Standard 25 km), ohne Wohnort in jedem Kanton. Höchstens 20 Seiten pro Abfrage. Nur Lehrstellen mit dem gewählten Lehrbeginn kommen an; ohne Jahr im Profil alle. Schnupperlehren sucht sie noch nicht.

- **Berufe:** Der Name im Profil wird bei jeder Suche über die Vorschläge des Portals auf dessen Beruf abgebildet, Geschlechtsformen zählen dabei nicht („Fachfrau“, „Fachmann/-frau“; `professionWords` in `portals/common.js`). Findet das Portal einen Beruf oder den Ort nicht, steht das als Problem bei der letzten Suche, und die übrigen Berufe laufen weiter.
- **LENA** füllt die Trefferliste erst im Browser. Darum öffnet der Tab pro Abfrage die Adresse aus `searchUrl`, lädt die Anpassung neu und liest die Karten aus der Seite („Mehr anzeigen“ ist die nächste Seite). Das Formular öffnet seine Vorschläge nur mit einem Fokus-Ereignis, das ein Tab im Hintergrund nicht von selbst auslöst; die Anpassung löst es aus.
- **yousty** liest wie die Stellenportale fertige Seiten per `fetch`, den Inseratstext aus den strukturierten Daten der Seite (schema.org `JobPosting`).
- **Zwillinge:** Dieselbe Lehrstelle auf beiden Portalen (gleicher Betrieb, gleicher Beruf laut Suchprofil, gleicher Ort) wird zu einem Treffer mit zweitem Link.

## Aufbau

- `manifest.json`: MV3, Berechtigungen nur für die sechs Portale, `127.0.0.1` und Native Messaging, dazu `activeTab` für die offene Seite nach einem Klick und der optionale Zugriff auf alle Seiten für Formulare und weitere Seiten.
- `background.js`: Service Worker; startet die Suche, öffnet und schliesst die Portal-Tabs, meldet den Fortschritt.
- `lib/`: `queries.js` (Abfragen pro Portal aus dem Suchplan, alle Stichworte zuerst am ersten Ort), `search.js` (Ablauf einer Suche, ohne Browser testbar), `sites.js` (weitere Seiten), `steps.js` (Abbrechen, Sichten), `app.js` (Verbindung zur App), `senders.js` (wer Aufträge geben darf), `progress.js` (Text für den Fortschritt).
- `portals/`: eine Anpassung pro Portal mit `list(query, page)` und `details(hit)`, dazu `common.js` (HTML zu Text, Alter, Pensum, Abrufe).
- `app-bridge.js`: läuft nur auf Seiten der App (`<meta name="bewerbungsbegleiter">`), zeigt ihr per Zeichen, dass die Erweiterung da ist, und reicht Start und Fortschritt weiter.
- `popup.*`, `page-panel.js`: Popup nach dem Entwurf (MIN-369): verbunden oder „Die App läuft nicht“ mit „Nochmals verbinden“, die letzte Suche oder die Portale eines laufenden Laufs mit „Suche abbrechen“ (`suche-stoppen`, hört nach dem laufenden Schritt auf), die Stelle der offenen Seite mit Note. Was es zeigt, steht ohne DOM in `lib/popup-view.js`. Die Wörter folgen der Einrichtung der App: Der Suchplan bringt die Anrede mit, bei Lehrstellen immer du; der Service Worker merkt sich den Textsatz für `erlauben.*` (`storage.local`, `textsatz`).
- `form/`: im Tab eines Formulars: `fields.js` (was ein Feld ist, nur Regeln, ohne Seite testbar), `filler.js` (füllt pro Rahmen), `bar.js` (Balken im oberen Rahmen). `lib/apply.js` führt die Tabs, `erlauben.*` fragt um den Zugriff (Wörter in `lib/permission-text.js`: was die Erweiterung dort tut und was nie).

Gegenstück in der App: `desktop/native_host.py` (Host, Weiterleitung an die laufende App, startet sie bei Bedarf), `desktop/native_messaging.py` (Anmeldung beim Browser), `bewerbungen/search_plan.py`, `bewerbungen/hits.py` und `bewerbungen/routes_search.py`.

## Tests

```bash
node --test tests/*.test.mjs
```

Die Anpassungen an die Portale sind mit gespeicherten Antworten oder kleinen Nachbildungen der Seiten getestet. Ändert ein Portal seine Seiten, zuerst die Anpassung im Portal-Tab von Hand prüfen (Code aus `portals/common.js` und der Anpassung in die Konsole einfügen, dann `bewerbungsbegleiterPortals['jobs.ch'].list({keyword: 'python', place: 'Bern'}, 1)`), danach Test und Anpassung nachführen.

## Im RAV eintragen (MIN-347)

In der Übersicht der App wählt die Person bei „Das steht an“ oder beim Hinweis gegen Monatsende „Jetzt eintragen“; das nimmt alle abgeschickten, noch nicht eingetragenen Bewerbungen (höchstens 20 pro Durchgang). Die Erweiterung öffnet das Formular für die Arbeitsbemühungen im Job-Room in einem einzigen Tab (`lib/rav.js`) und füllt einen Eintrag nach dem anderen (`form/rav-filler.js`, Zuordnung in `form/rav-fields.js`).

- **Anmelden und Speichern tut die Person.** Das Skript drückt nie einen Knopf. „Speichern“ im Job-Room übermittelt den Eintrag ans RAV. Ohne Anmeldung zeigt der Balken „Zum Formular“; auf der Anmeldeseite läuft kein Skript.
- **Vermerkt wird erst nach dem Speichern:** wenn die Meldung „Arbeitsbemühung gespeichert“ erscheint (Deutsch, Französisch, Italienisch, Englisch), oder wenn die Person im Balken „Eingetragen? Ja“ drückt. „Überspringen“ vermerkt nichts. Bei einem Fehlgriff lässt es sich auf der Seite der Bewerbung zurücksetzen.
- **Ausgefüllt wird**, was das Register hergibt: Datum, Art der Bewerbung, Firma, Kontakt, Stelle, Zuweisung, Pensum, Ergebnis, Vorstellungsgespräch. Die Adresse nur bei brieflichen und persönlichen Bewerbungen; dort wählt die Person PLZ und Ort aus der Liste. Was fehlt, bleibt offen, ist orange markiert und steht im Balken.
- **Hat sich das Formular geändert** (Steuerungen oder Beschriftungen nicht mehr wie erwartet), füllt das Skript nichts aus und sagt es im Balken. Die Beschriftungen stammen aus den öffentlichen Sprachdateien des Job-Room, der Aufbau vom Stand 4.11.2026.
- **Daten:** Die Angaben gehen nur von der App in dieses Formular. Sie sind besonders schützenswert (Art. 5 DSG) und gehen nie an die KI. Die Warteschlange enthält nur Kennung, Firma und Stelle und liegt in `chrome.storage.session`.
