# Browser-Erweiterung

Modul des [Bewerbungsassistenten](../README.md) (MIN-339): Die Erweiterung für Chrome und Edge sucht auf job-room, jobs.ch, jobscout24 und ictjobs nach dem Suchprofil. Sie sucht im Browser der Person, mit deren IP und Logins, und nur, wenn die Person die Suche startet. Die Treffer gehen über Native Messaging an die [Desktop-App](../desktop/README.md); dort erscheinen sie auf der Seite „Treffer“.

Im Pilot wird sie als **Entwicklererweiterung** geladen („Entpackte Erweiterung laden“). In den Store kommt sie später.

## Einrichten

Die App zeigt die Schritte auf der Seite **Einrichtung → Schritt 4** mit dem passenden Ordner:

1. Die App einmal starten. Sie meldet sich bei Chrome und Edge als Native-Messaging-Host an und legt den Ordner der Erweiterung in ihrem App-Ordner ab (`…/Bewerbungsassistent/erweiterung`). Beim Start aus dem Repo nimmt sie direkt diesen Ordner.
2. `chrome://extensions` (Edge: `edge://extensions`) öffnen und den **Entwicklermodus** einschalten.
3. **„Entpackte Erweiterung laden“** und den Ordner aus der Einrichtung wählen (auf dem Mac im Dialog mit Cmd+Shift+G den Pfad einfügen).
4. Die Seite „Treffer“ der App neu laden. Der Knopf „Stellen suchen“ ist jetzt aktiv.

Die ID der Erweiterung ist fest (`ghniboofenadplgmdgddmgjaaeeogejn`), weil `manifest.json` den öffentlichen Schlüssel enthält. Nur diese ID darf mit der App sprechen. Nach einem Update der App mit einer neuen Erweiterung zeigt die Einrichtung einen Hinweis; dann in `chrome://extensions` bei der Erweiterung auf „Neu laden“ klicken.

## Ablauf einer Suche

1. Start im Popup der Erweiterung oder mit „Stellen suchen“ auf der Seite „Treffer“.
2. Die Erweiterung holt den **Suchplan** von der App (`GET /api/suche/plan`, gebaut aus `suchprofil.md`): Stichworte, Orte, PLZ, Kantone, Titelfilter und Portale.
3. Pro Portal öffnet sie einen Tab im Hintergrund und führt dort die Anpassung aus `portals/` aus (`fetch` auf derselben Seite, wie im Skill `jobsuche`). Grenzen: höchstens 3 Seiten pro Abfrage, 30 Abfragen pro Portal, Inserate bis 45 Tage alt, 0,6 Sekunden zwischen den Abrufen.
4. Die Trefferliste geht zuerst an die App zum **Sichten** (`POST /api/suche/sichten`): bekannte Stellen, ausgeschlossene Titel und zu alte Inserate fallen weg. Dieselbe Stelle von einem anderen Portal (gleiche Firma, gleicher Titel, gleicher Ort) hängt die App gleich als weiteren Link an. Nur für die übrigen holt die Erweiterung den Volltext.
5. Die Treffer gehen in Zehnergruppen an die App (`POST /api/suche/treffer`), am Ende die Zusammenfassung pro Portal (`POST /api/suche/abschluss`). Ein Inserat, das nicht lädt (z.B. zu viele Abrufe), schickt sie nicht; es kommt bei der nächsten Suche wieder. Ändert ein Portal seine Seiten, gibt es mehr Abfragen als erlaubt oder fehlen Texte, steht das als Problem bei der letzten Suche.

Die App nimmt über den Host nur diese vier Anfragen an. Alles andere lehnt der Host ab. Die Erweiterung selbst nimmt Aufträge nur vom Popup und von der Seite der laufenden App an; eine andere Seite auf `127.0.0.1` mit demselben Kennzeichen wird abgewiesen, weil ihre Adresse nicht die ist, die die App über Native Messaging meldet (`lib/senders.js`).

## Aufbau

- `manifest.json`: MV3, Berechtigungen nur für die vier Portale, `127.0.0.1` und Native Messaging.
- `background.js`: Service Worker; startet die Suche, öffnet und schliesst die Portal-Tabs, meldet den Fortschritt.
- `lib/`: `queries.js` (Abfragen pro Portal aus dem Suchplan, alle Stichworte zuerst am ersten Ort), `search.js` (Ablauf einer Suche, ohne Browser testbar), `app.js` (Verbindung zur App), `senders.js` (wer Aufträge geben darf), `progress.js` (Text für den Fortschritt).
- `portals/`: eine Anpassung pro Portal mit `list(query, page)` und `details(hit)`, dazu `common.js` (HTML zu Text, Alter, Pensum, Abrufe).
- `app-bridge.js`: läuft nur auf Seiten der App (`<meta name="bewerbungsassistent">`), zeigt ihr per Zeichen, dass die Erweiterung da ist, und reicht Start und Fortschritt weiter.
- `popup.*`: Start der Suche und Stand des letzten Laufs.

Gegenstück in der App: `desktop/native_host.py` (Host, Weiterleitung an die laufende App, startet sie bei Bedarf), `desktop/native_messaging.py` (Anmeldung beim Browser), `bewerbungen/search_plan.py`, `bewerbungen/hits.py` und `bewerbungen/routes_search.py`.

## Tests

```bash
node --test tests/*.test.mjs
```

Die Anpassungen an die Portale sind mit gespeicherten Antworten getestet. Ändert ein Portal seine Seiten, zuerst die Anpassung im Portal-Tab von Hand prüfen (Code aus `portals/common.js` und der Anpassung in die Konsole einfügen, dann `bewerbungsassistentPortals['jobs.ch'].list({keyword: 'python', place: 'Bern'}, 1)`), danach Test und Anpassung nachführen.
