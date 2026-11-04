# KI-Vermittlung

Modul des [Bewerbungsassistenten](../README.md) für den Pilot (MIN-344): Die App der Teilnehmenden ruft die KI über diese Vermittlung auf. Auf den Rechnern liegt kein API-Schlüssel; jede Person hat einen eigenen Zugang mit Budget.

- **Schnittstelle** wie die Messages API von Anthropic (`POST /v1/messages`, auch Streaming). Die App nutzt das Anthropic SDK mit der Adresse der Vermittlung als `base_url`.
- **Zugang pro Person:** Einladungscode (16 Zeichen, standardmässig 45 Tage gültig, nur einmal) → die App löst ihn ein (`POST /v1/invitations/redeem`) und legt den Zugang im Schlüsselbund ab. Codes und Zugänge stehen nur als Hash in der Datenbank. Sperren für alle Geräte einer Person oder für eines.
- **Grenzen:** Budget pro Monat (sonst Antwort 402, die App sagt „Budget aufgebraucht“), Anfragen pro Minute, nur freigegebene Modelle, höchstens `VERMITTLUNG_MAX_TOKENS` Ausgabe-Tokens, nur Text (keine Bilder, keine Tools). So taugt die Vermittlung nicht als allgemeiner Zugang zu Claude.
- **Kosten** pro Aufruf: Person, Modell, Tokens, Kosten. **Inhalte werden nie gespeichert oder protokolliert**; sie sind schon in der App pseudonymisiert (MIN-334).
- `GET /v1/account` zeigt der App Monat, Verbrauch und Budget.

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
| `VERMITTLUNG_ANFRAGEN_PRO_MINUTE` | `10` | pro Person |
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
python admin.py invite T01 --budget 20     # Person anlegen, Code und Link ausgeben (45 Tage gültig)
python admin.py invite T01 --months 2      # andere Gültigkeit: --days, --weeks oder --months, höchstens 12 Monate
python admin.py accesses T01               # Geräte mit Zugang
python admin.py revoke T01 [--access 3]    # alle Zugänge oder einen sperren
python admin.py budget T01 30              # Budget pro Monat in USD
python admin.py costs [--month 2026-11]    # Kosten pro Person
```

`--months` zählt Kalendermonate: vom 31. Januar einen Monat weiter ist der 28. Februar.

Personen nur mit Kürzel anlegen (T01, T02 …), nicht mit echtem Namen. Monate zählen in UTC.

## Tests

```bash
pip install -r ../requirements-dev.txt
python -m pytest -q
```

Die Tests laufen mit einer simulierten Anthropic-API und dem SDK als Client, nie gegen die echte API.
