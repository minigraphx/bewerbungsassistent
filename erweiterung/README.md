# Browser-Erweiterung

Modul des [Bewerbungsassistenten](../README.md) (MIN-339): Die Erweiterung für Chrome und Edge sucht nach dem Suchprofil: Stellen auf job-room, jobs.ch, jobscout24 und ictjobs, Lehrstellen auf LENA (berufsberatung.ch) und yousty. Sie sucht im Browser der Person, mit deren IP und Logins, und nur, wenn die Person die Suche startet. Die Treffer gehen über Native Messaging an die [Desktop-App](../desktop/README.md); dort erscheinen sie auf der Seite „Treffer“.

Im Pilot wird sie als **Entwicklererweiterung** geladen („Entpackte Erweiterung laden“). In den Store kommt sie später.

## Einrichten

Die App zeigt die Schritte auf der Seite **Einrichtung → Schritt 4** mit dem passenden Ordner:

1. Die App einmal starten. Sie meldet sich bei Chrome und Edge als Native-Messaging-Host an und legt den Ordner der Erweiterung in ihrem App-Ordner ab (`…/Bewerbungsassistent/erweiterung`). Beim Start aus dem Repo nimmt sie direkt diesen Ordner.
2. In der Einrichtung „In Chrome öffnen“ bzw. „In Edge öffnen“ klicken: Die Erweiterungsseite und der Ordner gehen auf. Einmalig den **Entwicklermodus** einschalten. Von Hand: `chrome://extensions` oder `edge://extensions`.
3. **„Entpackte Erweiterung laden“** und den Ordner wählen (auf dem Mac im Dialog mit Cmd+Shift+G den Pfad einfügen).
4. Der Knopf „Stellen suchen“ auf der Seite „Treffer“ ist jetzt aktiv, auch ohne dass offene Seiten der App neu geladen werden müssen.

Ein Klick allein genügt nicht: Chrome lässt Apps seit Version 137 keine Erweiterungen mehr selbst laden (`--load-extension`), Richtlinien gelten nur auf verwalteten Geräten. Das ändert erst der Store.

Die ID der Erweiterung ist fest (`ghniboofenadplgmdgddmgjaaeeogejn`), weil `manifest.json` den öffentlichen Schlüssel enthält. Nur diese ID darf mit der App sprechen. Nach einem Update der App mit einer neuen Erweiterung zeigt die Einrichtung einen Hinweis; dann in `chrome://extensions` bei der Erweiterung auf „Neu laden“ klicken.

## Ablauf einer Suche

1. Start im Popup der Erweiterung oder mit „Stellen suchen“ auf der Seite „Treffer“.
2. Die Erweiterung holt den **Suchplan** von der App (`GET /api/suche/plan`, gebaut aus `suchprofil.md`): Stichworte, Orte, PLZ, Kantone, Titelfilter und Portale.
3. Pro Portal öffnet sie einen Tab im Hintergrund und führt dort die Anpassung aus `portals/` aus (`fetch` auf derselben Seite, wie im Skill `jobsuche`). Grenzen: höchstens 3 Seiten pro Abfrage, 30 Abfragen pro Portal, Inserate bis 45 Tage alt, 0,6 Sekunden zwischen den Abrufen.
4. Die Trefferliste geht zuerst an die App zum **Sichten** (`POST /api/suche/sichten`): bekannte Stellen, ausgeschlossene Titel und zu alte Inserate fallen weg. Dieselbe Stelle von einem anderen Portal (gleiche Firma, gleicher Titel, gleicher Ort) hängt die App gleich als weiteren Link an. Nur für die übrigen holt die Erweiterung den Volltext.
5. Die Treffer gehen in Zehnergruppen an die App (`POST /api/suche/treffer`), am Ende die Zusammenfassung pro Portal (`POST /api/suche/abschluss`). Ein Inserat, das nicht lädt (z.B. zu viele Abrufe), schickt sie nicht; es kommt bei der nächsten Suche wieder. Ändert ein Portal seine Seiten, gibt es mehr Abfragen als erlaubt oder fehlen Texte, steht das als Problem bei der letzten Suche.

Die App nimmt über den Host nur diese vier Anfragen und die zwei für die offene Seite (siehe unten) an. Alles andere lehnt der Host ab. Die Erweiterung selbst nimmt Aufträge nur vom Popup und von der Seite der laufenden App an; eine andere Seite auf `127.0.0.1` mit demselben Kennzeichen wird abgewiesen, weil ihre Adresse nicht die ist, die die App über Native Messaging meldet (`lib/senders.js`).

## Stelle auf der offenen Seite prüfen oder speichern (MIN-345)

Für Inserate ausserhalb der Portale, zum Beispiel auf LinkedIn oder den Karriereseiten von Firmen. Die Person öffnet das Inserat selbst und klickt auf das Symbol der Erweiterung.

- **Zugriff:** `activeTab`. Der Klick auf das Symbol gibt für diesen einen Tab Zugriff; ohne Klick liest die Erweiterung auf fremden Seiten nichts und navigiert nicht. Gelesen wird beim Öffnen des Popups, damit Stelle und Firma vorausgefüllt sind. Hinaus geht erst etwas nach einem Knopfdruck.
- **Lesen (`lib/page-ad.js`):** zuerst markierter Text, dann die strukturierten Daten der Seite (schema.org `JobPosting`), sonst der sichtbare Text des Hauptteils der Seite, wenn er nach Inserat aussieht. Dann sagt das Popup, dass der ganze Seitentext gelesen wurde, denn so kann mehr als das Inserat an die KI gehen (etwa Namen aus Seitenleisten). Stelle und Firma lassen sich im Popup korrigieren. Findet sie kein Inserat, sagt sie das und speichert nichts; markierter Text hilft dann weiter. Inhalte in eingebetteten Rahmen fremder Adressen sind nicht erreichbar, auch dort hilft Markieren nicht immer.
- **Adresse:** Die KI bekommt die Adresse der Seite nicht. Im Register steht sie ohne Tracking- und Sitzungswerte (`utm_*`, `refId`, `midToken` und ähnliche).
- **„Stelle prüfen“** (`POST /api/seite/pruefen`): Note mit Begründung, bestehende Bewerbung und Bewerbungen bei derselben Firma. Gespeichert wird nichts. Anweisungsartige Zeilen im Inserat meldet die KI als auffällig; das Popup zeigt sie rot.
- **„Stelle speichern“** (`POST /api/seite/speichern`): neue Bewerbung im Register mit `stelle.md` und, falls geprüft, mit der Note. Gleicher Link mit gleichem Titel oder gleiche Firma mit gleichem Titel ergeben keinen zweiten Eintrag; das Popup nennt den bestehenden. Mehrere Inserate unter einer Adresse bleiben getrennt, und nach einer Absage lässt sich dieselbe Stelle neu erfassen.

Das Ergebnis bleibt für diese Seite erhalten, auch wenn das Popup zwischendurch zugeht.

## Bewerben über Formulare

In der Übersicht der App kreuzt die Person bis zu fünf Bewerbungen an und klickt auf **Bewerben** (MIN-346). Die App prüft sie (Unterlagen, Link, Doppelbewerbungen), die Erweiterung öffnet pro Bewerbung einen Tab und füllt das Formular aus.

**Die Erweiterung füllt aus, die Person entscheidet und schickt ab:**

- Sie drückt nie einen Knopf, der etwas absendet, setzt keine Häkchen, Einwilligungen oder Optionsfelder und meldet sich nirgends an. Ein Passwortfeld hält den Tab an.
- Versteckte Felder bleiben leer, Vorhandenes bleibt stehen, und was die Person löscht, wird nicht wieder gefüllt.
- Unklare Felder bleiben leer und orange markiert, Einwilligungen rot, Ausgefülltes grün.
- Hochgeladen werden nur Dateien dieser Bewerbung: Lebenslauf, Anschreiben, Arbeitszeugnisse und die ZIP-Datei mit den gewählten Zertifikaten. Felder für nur eine Datei und Felder ohne klare Bedeutung bleiben offen.
- Der Versand wird erst erfasst, wenn die Person im Balken „Abgeschickt? Ja“ drückt.

**Zugriff:** Formulare liegen auf beliebigen Seiten, darum fragt die Erweiterung beim ersten „Bewerben“ auf `erlauben.html` einmal um Zugriff auf alle Seiten (`optional_host_permissions`). Sie nutzt ihn nur für Tabs aus ihrer eigenen Liste (`storage.session`). Ohne Frage zählen nur die Adresse nach dem ersten Laden und ihre Subdomains; bei jeder anderen fragt der Balken zuerst („Hier ausfüllen“). Das gilt auch hinter „Jetzt bewerben“: Diesem Link folgt sie einmal, wenn auf der Seite kein Formular ist, die Seite bestimmt aber nicht, wohin die Angaben gehen. Die Werte gehen nur an die geprüften Dokumente, nicht an das, was der Tab inzwischen zeigt.

**Seiten und Rahmen:** Ein Formular braucht mindestens drei sichtbare Felder ohne Häkchen, sonst bleibt der Rahmen unberührt (Suchfelder, Newsletter, Filter). Neue und neu eingeblendete Felder werden nachgefüllt, die nächste Seite derselben Adresse ebenfalls, später gebaute Rahmen auch. Knöpfe drückt sie nur auf Seiten ganz ohne Felder und nie in einem Formular.

## Lehrstellen

Abschnitt „Gesucht“ im Suchprofil oder die Wahl auf der Seite „Treffer“ legen fest, ob Lehrstellen, Schnupperlehren oder beides gesucht werden (MIN-373; Listen `lehrstellen` und `schnupperadressen` auf LENA, `lehrstellen` und `schnupperlehren` auf yousty). Schnupperlehren sind in der App eigene Treffer, und „Übernehmen“ legt eine Anfrage statt einer Bewerbung an.

Hat das Suchprofil einen Abschnitt „Lehrbeginn“, sucht die Erweiterung nur auf LENA und yousty, pro Beruf im gewählten Umkreis um den Wohnort (Standard 25 km), ohne Wohnort in jedem Kanton. Höchstens 20 Seiten pro Abfrage. Nur Lehrstellen mit dem gewählten Lehrbeginn kommen an; ohne Jahr im Profil alle. Schnupperlehren sucht sie noch nicht.

- **Berufe:** Der Name im Profil wird bei jeder Suche über die Vorschläge des Portals auf dessen Beruf abgebildet, Geschlechtsformen zählen dabei nicht („Fachfrau“, „Fachmann/-frau“; `professionWords` in `portals/common.js`). Findet das Portal einen Beruf oder den Ort nicht, steht das als Problem bei der letzten Suche, und die übrigen Berufe laufen weiter.
- **LENA** füllt die Trefferliste erst im Browser. Darum öffnet der Tab pro Abfrage die Adresse aus `searchUrl`, lädt die Anpassung neu und liest die Karten aus der Seite („Mehr anzeigen“ ist die nächste Seite). Das Formular öffnet seine Vorschläge nur mit einem Fokus-Ereignis, das ein Tab im Hintergrund nicht von selbst auslöst; die Anpassung löst es aus.
- **yousty** liest wie die Stellenportale fertige Seiten per `fetch`, den Inseratstext aus den strukturierten Daten der Seite (schema.org `JobPosting`).
- **Zwillinge:** Dieselbe Lehrstelle auf beiden Portalen (gleicher Betrieb, gleicher Beruf laut Suchprofil, gleicher Ort) wird zu einem Treffer mit zweitem Link.

## Aufbau

- `manifest.json`: MV3, Berechtigungen nur für die sechs Portale, `127.0.0.1` und Native Messaging, dazu `activeTab` für die offene Seite nach einem Klick und der optionale Zugriff auf alle Seiten für Formulare.
- `background.js`: Service Worker; startet die Suche, öffnet und schliesst die Portal-Tabs, meldet den Fortschritt.
- `lib/`: `queries.js` (Abfragen pro Portal aus dem Suchplan, alle Stichworte zuerst am ersten Ort), `search.js` (Ablauf einer Suche, ohne Browser testbar), `app.js` (Verbindung zur App), `senders.js` (wer Aufträge geben darf), `progress.js` (Text für den Fortschritt).
- `portals/`: eine Anpassung pro Portal mit `list(query, page)` und `details(hit)`, dazu `common.js` (HTML zu Text, Alter, Pensum, Abrufe).
- `app-bridge.js`: läuft nur auf Seiten der App (`<meta name="bewerbungsassistent">`), zeigt ihr per Zeichen, dass die Erweiterung da ist, und reicht Start und Fortschritt weiter.
- `popup.*`: Start der Suche und Stand des letzten Laufs.
- `form/`: im Tab eines Formulars: `fields.js` (was ein Feld ist, nur Regeln, ohne Seite testbar), `filler.js` (füllt pro Rahmen), `bar.js` (Balken im oberen Rahmen). `lib/apply.js` führt die Tabs, `erlauben.*` fragt um den Zugriff.

Gegenstück in der App: `desktop/native_host.py` (Host, Weiterleitung an die laufende App, startet sie bei Bedarf), `desktop/native_messaging.py` (Anmeldung beim Browser), `bewerbungen/search_plan.py`, `bewerbungen/hits.py` und `bewerbungen/routes_search.py`.

## Tests

```bash
node --test tests/*.test.mjs
```

Die Anpassungen an die Portale sind mit gespeicherten Antworten oder kleinen Nachbildungen der Seiten getestet. Ändert ein Portal seine Seiten, zuerst die Anpassung im Portal-Tab von Hand prüfen (Code aus `portals/common.js` und der Anpassung in die Konsole einfügen, dann `bewerbungsassistentPortals['jobs.ch'].list({keyword: 'python', place: 'Bern'}, 1)`), danach Test und Anpassung nachführen.
