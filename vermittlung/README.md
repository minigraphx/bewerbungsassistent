# KI-Vermittlung

Modul des [Bewerbungsbegleiters](../README.md) für den Pilot (MIN-344): Die App der Teilnehmenden ruft die KI über diese Vermittlung auf. Auf den Rechnern liegt kein API-Schlüssel; jeder eingelöste Code ist ein eigener Zugang mit einem Budget in CHF pro Monat (G98).

- **Schnittstelle** wie die Messages API von Anthropic (`POST /v1/messages`, auch Streaming). Die App nutzt das Anthropic SDK mit der Adresse der Vermittlung als `base_url`.
- **Zugang pro Person:** Einladungscode (16 Zeichen, standardmässig 45 Tage gültig, nur einmal) → die App löst ihn ein (`POST /v1/invitations/redeem`) und legt den Zugang im Schlüsselbund ab. Codes und Zugänge stehen nur als Hash in der Datenbank. Sperren für alle Geräte einer Person oder für eines.
- **Budget:** Jeder Zugang darf pro Kalendermonat ein Budget brauchen, standardmässig CHF 5, mitgegeben vom Code. Es erneuert sich am Monatsersten um Mitternacht Schweizer Zeit (Europe/Zurich); was übrig bleibt, verfällt. `admin.py budget` setzt es pro Person höher, höchstens CHF 100. Ein USD, den Anthropic verrechnet, zählt als ein CHF (`CHF_PER_USD` in `pricing.py`, ohne Wechselkurs; was übrig bleibt, trägt den Server). Ist es aufgebraucht, antwortet die Vermittlung mit 402 und dem Typ `credit_used_up`. Einen weiteren Code kann die Person trotzdem einlösen; der neue Zugang bringt sein eigenes Budget.
- **Grenzen:** das Budget, Anfragen pro Minute und gleichzeitig, nur freigegebene Modelle, höchstens `VERMITTLUNG_MAX_TOKENS` Ausgabe-Tokens, nur Text (keine Bilder, keine Tools). Texte selbst lassen sich nicht einschränken: Wer einen Zugang hat, kann beliebigen Text schicken, begrenzt durch Budget und Limits.
- **Kosten** pro Aufruf: Person, Zugang, Modell, Tokens, Kosten in USD, wie Anthropic sie verrechnet. **Inhalte werden nie gespeichert oder protokolliert**; sie sind schon in der App pseudonymisiert (MIN-334).
- `GET /v1/account` zeigt der App Budget und Verbrauch des laufenden Monats in CHF (`credit_chf`, `spent_chf`; die Namen bleiben für ältere Apps), dazu den Monat und den Tag, an dem es sich erneuert, beides vom Server gerechnet: `{"credit_chf": 5.0, "spent_chf": 1.25, "monat": "2026-11", "erneuert_am": "2026-12-01"}`.
- **Ältere Datenbanken** übernimmt die Vermittlung beim Start, ohne etwas umzuschreiben: Das Guthaben eines Zugangs oder offenen Codes aus G80 gilt nun als Budget pro Monat, Zugänge von vor G80 bekommen CHF 5. Kostenprotokolle bleiben; die alten Spalten `budget_usd` und `credit_since` bleiben ungenutzt stehen.

## Betrieb

Container hinter Caddy (HTTPS):

```bash
cp compose.example.yaml compose.yaml
cp Caddyfile.example Caddyfile        # Domain eintragen
echo "ANTHROPIC_API_KEY=…" > .env     # nur auf dem Server; Datei ist in .gitignore
docker compose up -d --build
```

Ohne Container (z.B. Hosting mit Python 3.12): `pip install -r requirements.txt`, Umgebungsvariablen setzen, `python main.py` unter einem Prozess-Manager starten und HTTPS davor schalten.

| Variable | Standard | Bedeutung |
|---|---|---|
| `ANTHROPIC_API_KEY` | – | Schlüssel von Anthropic, nur als Geheimnis des Servers |
| `VERMITTLUNG_DB` | `/data/vermittlung.sqlite` | Datenbank (Personen, Zugänge, Kosten) |
| `VERMITTLUNG_HOST`, `VERMITTLUNG_PORT` | `0.0.0.0`, `8080` | Adresse im Container |
| `VERMITTLUNG_ANFRAGEN_PRO_MINUTE` | `20` | pro Person |
| `VERMITTLUNG_GLEICHZEITIG` | `5` | Anfragen pro Person, die gleichzeitig laufen; begrenzt, wie weit parallele Anfragen das Guthaben überschreiten können |
| `VERMITTLUNG_MAX_TOKENS` | `16000` | höchstens so viele Ausgabe-Tokens pro Anfrage |
| `VERMITTLUNG_HINTER_PROXY` | `1` | Adresse der Person aus `X-Forwarded-For` (für das Limit beim Einlösen) |

### Betrieb mit nginx und systemd

Für einen Server, auf dem nginx schon andere Seiten ausliefert (`deploy/`): Der Container hört nur auf `127.0.0.1:8010`, läuft ohne Rechte und mit nur lesbarem Dateisystem; systemd startet ihn, nginx macht HTTPS.

Einmal einrichten (als Benutzer mit `sudo`):

```bash
sudo install -d -m 700 /etc/bewerbungsassistent-vermittlung
sudo install -d -m 700 -o 10002 -g 10002 /var/lib/bewerbungsassistent-vermittlung
sudo install -m 600 /dev/null /etc/bewerbungsassistent-vermittlung/vermittlung.env
sudoedit /etc/bewerbungsassistent-vermittlung/vermittlung.env   # ANTHROPIC_API_KEY=… eintragen
deploy/deploy.sh <ssh-host>                                      # vom eigenen Rechner: Code kopieren, Image bauen
sudo cp /opt/bewerbungsassistent-vermittlung/deploy/vermittlung.service \
        /etc/systemd/system/bewerbungsassistent-vermittlung.service
sudo systemctl enable --now bewerbungsassistent-vermittlung
# nginx: deploy/nginx.conf.example mit Domain und Zertifikat anpassen, dann
sudo nginx -t && sudo systemctl reload nginx
```

Neue Fassung: `deploy/deploy.sh <ssh-host>` baut ein Image mit dem Git-Stand als Tag und startet den Dienst neu. Verwaltung dann mit `sudo docker exec bewerbungsassistent-vermittlung-vermittlung-1 python admin.py …`.

Im Anthropic-Konto für die Vermittlung einen eigenen Workspace mit Ausgabenlimit anlegen; das ist die zweite Sicherung neben den Budgets hier.

## Verwaltung

Auf dem Server (im Container: `docker compose exec vermittlung python admin.py …`):

```bash
python admin.py invite T01                 # Person anlegen, Code und Link ausgeben (CHF 5 pro Monat, Code 45 Tage gültig)
python admin.py invite T01 --budget 10     # anderes Budget pro Monat in CHF, höchstens 100
python admin.py invite T01 --months 2      # andere Gültigkeit: --days, --weeks oder --months, höchstens 12 Monate
python admin.py budget T01 20 [--access 3] # Budget pro Monat setzen: aktive Zugänge und offene Codes, oder ein Zugang
python admin.py accesses T01               # Geräte mit Zugang, Budget und Verbrauch des Monats, Einwilligung
python admin.py revoke T01 [--access 3]    # alle Zugänge und offenen Einladungen sperren, oder einen Zugang
python admin.py costs [--month 2026-11]    # Kosten pro Person im Monat, in CHF
python admin.py due                        # Personen, deren Daten zu löschen sind
python admin.py forget T01 [--yes]         # gesperrte Person löschen; ohne --yes nur anzeigen
```

Kostenprotokolle löschen: nach der Auswertung, spätestens 30 Tage nach der Sperrung (so steht es in der Datenschutzerklärung). `forget` entfernt Person, Zugänge, Einladungen und Kostenprotokolle und lehnt ab, solange ein Zugang aktiv ist, weil der Verbrauch des Monats aus den Protokollen berechnet wird. Gelöscht wird nichts von selbst: `due` zeigt, wer fällig ist.

`--months` zählt Kalendermonate: vom 31. Januar einen Monat weiter ist der 28. Februar.

Personen nur mit Kürzel anlegen (T01, T02 …), nicht mit echtem Namen. Monate zählen in Schweizer Zeit (Europe/Zurich), für das Budget wie für `costs`; die Zeitzone kommt aus der Zeitzonen-Datenbank des Systems (im Container das Paket `tzdata`).

## Tests

```bash
pip install -r ../requirements-dev.txt
python -m pytest -q
```

Die Tests laufen mit einer simulierten Anthropic-API und dem SDK als Client, nie gegen die echte API.
