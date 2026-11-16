# Updates im Paket des Microsoft Store

Gehört zu G6 (#344), Schritt 2 von #47. Verbindlicher Entscheid der UI/UX-Prüfung vom 16.11.2026. Umgesetzt in `desktop/msix_package.py` (Erkennung), `desktop/routes_app.py` (Routen), `desktop/start.py` (Alias und Link) und `bewerbungen/seiten/app.js` («Über die App»).

## Wo der Hinweis steht

- **Banner und Dialog gibt es im Store-Paket nie.** Die App bietet dort nie ein Update an, darum braucht die Seite keinen eigenen Zweig:
  - `/api/app/version` antwortet mit `update: null` und zusätzlich `store: true`.
  - Keine Abfrage im Hintergrund, kein Download.
  - `POST /api/app/aktualisieren` lehnt mit 409 und dem Text «Updates kommen über den Microsoft Store.» ab.
  - «Beenden» installiert nie etwas. `aktualisiert` wird nie gesetzt, darum erscheint die Seite «wird aktualisiert» nicht.
- **Erkennung:** Ob die App im Paket läuft, entscheidet eine Funktion in Python neben `updates.py`. Sie fragt, ob Windows eine Paketidentität nennt. Alles oben hängt davon ab.
- **Der Hinweis steht nur unter «Über die App»,** in einer eigenen Zeile direkt unter «Version X»:
  - `ueberDieApp(version, store)` fügt die Zeile mit der Klasse `about__meta` an, wenn `store` gesetzt ist.
  - Die Zeile mit der Version bleibt, wie sie ist.
- **macOS, Linux und der Windows-Installer bleiben, wie sie sind.**

## Der Wortlaut

- **Der Satz:** ein neutraler Satz, «Updates kommen über den Microsoft Store.».
- **Wo er steht:** direkt in `app.js`, ohne Schlüssel in `texte.js`. Er ist für Sie, du und Lehrstelle derselbe, darum braucht er keinen Textsatz.
- **Die Ablehnung:** Die 409 von `/api/app/aktualisieren` verwendet denselben Text.
- **Was der Satz nicht sagt:** wo man im Store klickt. Das gehört in die Anleitung.

## Kein Banner, keine Statuszeile

- **Nichts zu tun:** Es gibt nichts zu entscheiden und keinen Fehler. Ein Banner oder eine Statuszeile würde auf jeder Seite stehen, ohne dass die Person etwas tun kann.
- **Keine Ansage:** Darum gibt es keine Live-Region und kein «×» zum Schliessen.
- **Wo es steht:** Der Hinweis gehört dorthin, wo man nach der Version sucht.

## Der Schalter «Vorabversionen»

- **Die ganze Karte `#vorabversionen` fehlt im Store-Paket.**
  - `GET /api/app/vorabversionen` antwortet mit 404. `vorabversionen.js` blendet den Abschnitt schon heute aus, wenn die Abfrage scheitert.
  - `POST` lehnt genauso ab.
- **Alte Einstellung:** Eine Wahl, die eine frühere Installation mit dem Installer gespeichert hat, bleibt in der Datei und wird nicht beachtet.
- **«Erweitert» bleibt:** Der Bereich behält seine übrigen Karten («Seitengrenze»), darum bleibt auch sein Eintrag links.

## Anleitung

Die Anleitung (`docs/installation.md`) folgt in #346, nicht in diesem Item.

## Prüfung des Baus (16.11.2026)

- **Ergebnis:** Die UI/UX-Prüfung der Commits 1a8e111 und 32021a4 ergab PASS.
- **Einzige Änderung:** der Wortlaut im README von `desktop/` («…hat keinen Schalter für Vorabversionen»), umgesetzt in a086c9b.
- **Ohne Browser:** Eine Prüfung im Browser war nicht nötig. Der Test `bewerbungen/tests/ueber_die_app.test.cjs` führt `app.js` in einer Sandbox aus und prüft beides: die Stelle der Zeile direkt unter der Version und dass sie ausserhalb des Pakets fehlt.

## Prüfung im echten Paket

Für den Pilot unter Windows, mit der App aus dem Store-Paket:

1. Nach dem Start erscheint kein Dialog «Neue Version verfügbar» und kein Banner, auch wenn auf dem Update-Server eine neuere Version liegt.
2. Einstellungen › Über die App zeigt in dieser Reihenfolge: «Bewerbungsbegleiter», «Version X», «Updates kommen über den Microsoft Store.», «von Andreas Schmidt».
3. Einstellungen › Erweitert hat keine Karte «Vorabversionen»; «Seitengrenze» ist noch da.
4. «Beenden» zeigt «Bewerbungsbegleiter beendet», nie «wird aktualisiert».
5. Die Erweiterung verbindet sich nach einem Update aus dem Store weiterhin (Pfad über den App-Alias).
6. Ein Einladungslink `bewerbungsbegleiter://…` öffnet die App.
