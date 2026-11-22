# Erweiterung automatisch in die Stores

Gehört zu #365. Seit dieser Änderung lädt `.github/workflows/erweiterung-einreichen.yml` die Browser-Erweiterung in den Chrome Web Store und zu Microsoft Edge Add-ons, sobald Andy ein Release veröffentlicht. Bis dahin baute Andy die ZIP-Datei direkt nach dem Tag und lud sie in beiden Stores von Hand hoch.

## Ablauf

Der Workflow läuft beim Veröffentlichen eines Releases (`release: released`). Eine Vorabversion geht nicht in die Stores. Wird aus einer Vorabversion später ein Release, lädt der Workflow dann hoch.

Je Store gibt es einen eigenen Job, `chrome` und `edge`. Sie hängen weder voneinander noch von `update-ausrollen.yml` ab: Scheitert ein Store, ist nur sein Job rot. Das Update der App und die Webseite gehen trotzdem aus. Beide Jobs dürfen nur das Repo lesen (`contents: read`). Sie kommen weder an den Signaturschlüssel der Updates noch ans Release.

Jeder Job geht so vor:

1. **Tag auschecken.** Der Job holt den Stand des Tags, nicht `main`.
2. **Einstellungen prüfen.** `python3 desktop/store_upload.py ready <chrome|edge>` prüft, ob alle Secrets und Variablen des Stores gesetzt sind. Fehlt etwas, endet der Job grün mit einem Hinweis, der die fehlenden Namen nennt, nie die Werte. Die übrigen Schritte entfallen dann. Nach dem Eintragen den Lauf unter Actions neu starten («Re-run jobs»).
3. **ZIP bauen und Version prüfen.** `desktop/store_package.py` baut `bewerbungsbegleiter-erweiterung-<Version>.zip` aus dem Tag. `store_upload.py version <Tag> <ZIP>` liest die Version aus dem Manifest in der ZIP-Datei. Weicht sie vom Tag ab, schlägt der Job fehl, bevor etwas hochgeladen wird.
4. **Hochladen und einreichen**, mit `curl` und `jq` des Runners, ohne fremde Action:
   - **Chrome Web Store:** Der Job holt mit dem Refresh Token einen Zugriffsschlüssel. Er lädt die ZIP-Datei als Update des bestehenden Eintrags hoch und wartet, bis das Hochladen fertig ist. Dann reicht er die Version zur Prüfung ein. Sie erscheint, sobald die Prüfung durch ist. Der Hinweis am Ende nennt den Stand, meist `PENDING_REVIEW`.
   - **Edge Add-ons:** Der Job lädt die ZIP-Datei in den Entwurf des bestehenden Produkts und wartet auf den Vorgang. Dann veröffentlicht er den Entwurf, womit die Prüfung beginnt, und wartet auch darauf.

Secrets und Zugriffsschlüssel kommen nur über Umgebungsvariablen in die Schritte. `curl` bekommt sie über die Standardeingabe oder eine Datei mit Rechten nur für den Runner, nie auf der Befehlszeile. Den Zugriffsschlüssel von Google blendet der Job im Protokoll aus.

Abgefragt wird alle 10 Sekunden, höchstens 60-mal (`POLL_SECONDS`, `POLL_TRIES`). Der Job bricht nach 30 Minuten ab.

## Später in den Stores

Der Workflow lädt erst beim Veröffentlichen hoch, nicht schon beim Tag. Darum beginnt die Prüfung der Stores um die Zeit zwischen Tag und Veröffentlichen später. Bisher lag die ZIP-Datei gleich nach dem Tag in den Stores, weil die Prüfung dort Tage dauert. Wer die Erweiterung aus einem Store hat, bekommt die neue Fassung also später als die App. Wo das zählt, das Release bald nach dem Tag veröffentlichen.

## Secrets und Variablen

| Name | Art | Store | Woher |
| --- | --- | --- | --- |
| `CHROME_CLIENT_ID` | Secret | Chrome | Client-ID des OAuth-Clients in Google Cloud |
| `CHROME_CLIENT_SECRET` | Secret | Chrome | Clientschlüssel desselben OAuth-Clients |
| `CHROME_REFRESH_TOKEN` | Secret | Chrome | Refresh Token aus dem OAuth Playground |
| `CHROME_PUBLISHER_ID` | Variable | Chrome | Developer Dashboard, Publisher › Settings |
| `CHROME_EXTENSION_ID` | Variable | Chrome | ID des Eintrags, `nopiegcdnjpkekgfakgglegkeifpmopo` (siehe `erweiterung/README.md`) |
| `EDGE_CLIENT_ID` | Secret | Edge | Partner Center, Microsoft Edge › Publish API, Client ID |
| `EDGE_API_KEY` | Secret | Edge | Partner Center, Microsoft Edge › Publish API, API key |
| `EDGE_PRODUCT_ID` | Variable | Edge | Partner Center, Extension overview › Product ID (eine GUID, nicht die ID im Store) |

## Einmalige Einrichtung (Andy)

Beide Stores nehmen über die API nur Updates an. Die Einträge gibt es schon; die erste Fassung ging von Hand.

### Chrome Web Store

1. Das Google-Konto, dem der Eintrag gehört, braucht die Bestätigung in zwei Schritten.
2. In der Google Cloud Console ein Projekt anlegen oder wählen und die «Chrome Web Store API» aktivieren.
3. Unter «OAuth-Zustimmungsbildschirm» den Typ «Extern» wählen, Name und Kontaktadresse eintragen und das eigene Konto als Testnutzer hinzufügen.
4. Den Zustimmungsbildschirm danach auf **«In Produktion»** stellen. Steht er auf «Testen», läuft das Refresh Token nach 7 Tagen ab, und der nächste Lauf scheitert bei der Anmeldung.
5. Unter «Anmeldedaten» eine OAuth-Client-ID vom Typ «Webanwendung» anlegen, mit der Weiterleitungs-URI `https://developers.google.com/oauthplayground`. Client-ID und Clientschlüssel notieren.
6. Im [OAuth 2.0 Playground](https://developers.google.com/oauthplayground) über das Zahnrad «Use your own OAuth credentials» wählen und Client-ID und Clientschlüssel eintragen. Als Scope `https://www.googleapis.com/auth/chromewebstore` eingeben und «Authorize APIs» klicken. Mit dem Konto anmelden, dem der Eintrag gehört, dann «Exchange authorization code for tokens». Die Antwort enthält `refresh_token`.
7. Die Publisher-ID im Developer Dashboard unter Publisher › Settings ablesen.

### Microsoft Edge Add-ons

1. In Partner Center unter Microsoft Edge › **Publish API** die neue Fassung mit API-Schlüsseln einschalten («Enable»).
2. «Create API credentials» klicken. Client ID und API key notieren. Der Schlüssel hat ein Ablaufdatum, das auf derselben Seite steht. Vor Ablauf einen neuen erstellen und das Secret ersetzen.
3. Die Product ID auf der Übersicht der Erweiterung ablesen. Sie steht auch in der Adresszeile zwischen `microsoftedge/` und `/packages`.

### Im Repo eintragen

`gh secret set` fragt den Wert ab, so landet er nicht im Verlauf der Shell:

```
gh secret set CHROME_CLIENT_ID
gh secret set CHROME_CLIENT_SECRET
gh secret set CHROME_REFRESH_TOKEN
gh variable set CHROME_PUBLISHER_ID --body <Publisher-ID>
gh variable set CHROME_EXTENSION_ID --body nopiegcdnjpkekgfakgglegkeifpmopo
gh secret set EDGE_CLIENT_ID
gh secret set EDGE_API_KEY
gh variable set EDGE_PRODUCT_ID --body <Product ID>
```

Es geht auch nur ein Store: Fehlen die Einstellungen des anderen, endet dessen Job grün mit dem Hinweis.

## Wenn ein Job scheitert

Die Meldung nennt Store, Schritt und HTTP-Status oder den Stand des Stores, darunter die Antwort des Stores, nie ein Secret. Typische Fälle:

- **Anmeldung bei Google abgelehnt:** Das Refresh Token ist abgelaufen oder widerrufen, oft wegen Schritt 4 oben. Ein neues holen und `CHROME_REFRESH_TOKEN` ersetzen.
- **Chrome lehnt das Hochladen ab:** Die Version im Manifest muss höher sein als die im Store.
- **Edge meldet `InProgressSubmission`:** Eine frühere Einreichung ist noch in Prüfung. Nach deren Abschluss den Job neu starten.
- **Edge meldet `NoModulesUpdated`:** Das Paket ist schon eingereicht. Es gibt nichts zu tun.

Ein neuer Start lädt dasselbe Paket nochmals hoch; das ist in beiden Stores unschädlich, solange die Version noch nicht veröffentlicht ist.

## Quellen

Geprüft am 23.11.2026:

- Chrome Web Store API V2, Ablauf und Einrichtung: <https://developer.chrome.com/docs/webstore/using-api>. Endpunkte: `POST https://oauth2.googleapis.com/token`, `POST https://chromewebstore.googleapis.com/upload/v2/publishers/<Publisher-ID>/items/<ID>:upload`, `GET …/v2/publishers/<Publisher-ID>/items/<ID>:fetchStatus`, `POST …/v2/publishers/<Publisher-ID>/items/<ID>:publish`. Referenz: <https://developer.chrome.com/docs/webstore/api/reference/rest/v2/publishers.items/publish>. Die alte API V1.1 lief laut Google am 15.10.2026 aus.
- Ablauf des Refresh Tokens im Zustand «Testen»: <https://developers.google.com/identity/protocols/oauth2#expiration>.
- Microsoft Edge Add-ons API v1.1: <https://learn.microsoft.com/microsoft-edge/extensions/update/api/using-addons-api> und die Referenz <https://learn.microsoft.com/microsoft-edge/extensions/update/api/addons-api-reference>. Endpunkte unter `https://api.addons.microsoftedge.microsoft.com`: `POST /v1/products/<Product ID>/submissions/draft/package`, `GET …/draft/package/operations/<Vorgang>`, `POST /v1/products/<Product ID>/submissions`, `GET …/submissions/operations/<Vorgang>`; Header `Authorization: ApiKey <API key>` und `X-ClientID: <Client ID>`.

Ungeprüft, bis ein echtes Release hochgeladen ist: ob Edge den Header `Location` wie in der Referenz als blosse ID liefert (der Job nimmt auch eine Adresse, die auf die ID endet) und ob Edge die Notizen für die Prüfung als JSON annimmt. Die Anleitung zeigt dafür JSON, die Referenz spricht von Text.
