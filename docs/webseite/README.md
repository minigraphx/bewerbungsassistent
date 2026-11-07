# Webseite

Statische Webseite der App: Startseite und Anleitung. Sie stellt die App vor und führt zum Download, für Stellensuchende und Eltern von Lehrstellensuchenden. Gestaltet nach dem freigegebenen Entwurf in `docs/design/seiten/Webseite.dc.html`.

## Bauen

```bash
.venv/bin/python docs/webseite/build.py --datenschutz https://…/datenschutz --downloads https://…
```

Das Ergebnis liegt in `docs/webseite/build/` (nicht im Repo). Zwei Adressen stehen nicht im Repo und kommen als Parameter oder aus der Umgebung, wie beim Build der App:

- `--datenschutz` oder `BEWERBUNGSBEGLEITER_DATENSCHUTZ_URL`: die Datenschutz-Seite. Sie nennt den Namen des Betreibers.
- `--downloads` oder `BEWERBUNGSBEGLEITER_UPDATE_URL`: der Update-Server. Die Knöpfe „Für Windows laden“ und „Für macOS laden“ zeigen direkt auf die Pakete dieser Version, `<Adresse>/<Version>/<Paket>`, so wie `update-ausrollen.yml` sie hochlädt.

## Woher die Inhalte kommen

| Teil | Quelle |
| --- | --- |
| Kopf, Fuss, Rahmen | `vorlagen/rahmen.html` |
| Startseite | `vorlagen/start.html` |
| Anleitung | `docs/installation.md`, dieselbe Datei, die GitHub zeigt. Verweise auf andere Anleitungen führen auf GitHub. |
| Aussehen | `stil.css`, Werte aus `docs/design/system/tokens.json` |
| Version | `desktop/version.py` |
| Bilder | `docs/bilder/`, nur mit erfundenen Daten |
| Logo | `docs/bilder/as-logo.svg`, von der GPL ausgenommen (`docs/NOTICE`) |
| Schrift | DM Sans aus `lebenslauf/fonts/` |

Die Seite lädt nichts von fremden Servern und hat kein Skript; die Content Security Policy in `rahmen.html` erlaubt nur eigene Dateien.

## Sprachen

Die Sprachwahl (DE, EN, FR) ist gestaltet, aber mit `display: none` ausgeblendet, bis die App weitere Sprachen kann.

## Ausrollen

Automatisch: Das Veröffentlichen eines Releases startet `update-ausrollen.yml`. Nach den Paketen baut der Job `webseite` die Seite aus dem Stand des Tags und lädt sie per FTP über TLS hoch, die Startseite zuletzt. Danach vergleicht er, was der Server ausliefert. So passen Version und Download-Links immer zum veröffentlichten Release. Von Hand nochmals: den Workflow mit dem Tag starten.

Einstellungen im Environment `update-ausrollen`: Geheimnis `WEB_FTP_PASSWORD`, Variablen `WEB_FTP_USER`, `WEB_FTP_FOLDER` und `WEB_URL`. Der FTP-Benutzer ist auf den Ordner der Site beschränkt. Datenschutz- und Update-Adresse kommen aus den Repo-Variablen `DATENSCHUTZ_URL` und `UPDATE_URL`. Der Job installiert `markdown-it-py` nur mit den Hashes aus `requirements-ausrollen.txt`.
