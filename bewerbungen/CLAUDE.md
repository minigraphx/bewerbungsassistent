# CLAUDE.md – Modul Bewerbungen

Verwaltung und lokale Oberfläche des Bewerbungsassistenten (MIN-261 Ablauf, MIN-262 Prüfung, MIN-263 Versand, MIN-303/304 Entwürfe und Versionen, MIN-306 Register, MIN-307 Varianten). Baut auf `../lebenslauf` auf, nie umgekehrt (`pfade.py` macht es importierbar; pytest über `pythonpath` in `pytest.ini`).

## Aufbau
- `app.py` – Einstieg: `python app.py <datenordner>`; Server (`server.py`), Routen (`routen_*.py`), Seiten (`seiten/`).
- `server.py` – nur 127.0.0.1, Token pro Start (GET `t`, POST `X-Token` + JSON), Host-Prüfung, CSP ohne Inline-Skripte; ValueError → 400, KeyError → 404.
- `kontext.py` – Datenordner, Build-Ordner, Ablage, Versionierung; `mit_entwurf` legt beim Schreiben Entwürfe davor/danach an.
- `ablage.py` – Entwürfe in `.entwuerfe/` (SHA-256, Index); löschbar solange nicht genutzt.
- `versionen.py` – zusätzlicher Git-Commit beim Versand, nur wenn Git installiert ist (nur die genannten Dateien, Ersatz-Autor ohne Git-Konfiguration); ohne Git `OhneGit`. Die eigene Ablage ist auch ohne Git vollständig (MIN-304).
- `register.py` – `bewerbungen.yaml`, Prüfung, IDs, Job-Room-Angaben (nur abgeleitet, nie gespeichert), Import/Export im Format der Jobliste.
- `varianten.py` – `varianten.yaml`, Vorschlag per Stichwort-Abgleich.
- `unterlagen.py` – Lebenslauf (Variante) und Anschreiben pro Bewerbung bauen.
- `inhalte.py` – Inhalte (MIN-302): erlaubte Dateien nach Muster, Titel für die Oberfläche, Prüfung je Dateityp mit Probebau im Build-Ordner. Die Seiten zeigen standardmässig das PDF; der Text liegt hinter „Als Text“.
- `textdokument.py` – Markdown als PDF: markdown-it zerlegt, `typst/dokument.typ` setzt alles als Text (HTML bleibt Text, keine Bilder, Links nur Web/Mail).
- `pruefung.py` – formale Prüfung der PDFs und des Anschreibens.
- `versand.py` – Versand erfassen: ablegen (dedupliziert), Entwürfe genutzt, Register, Git falls vorhanden; `versendete` listet die Versionen aus Register und Ablage.
- `dateien.py` – atomar schreiben, Pfade auf den Datenordner beschränken.
- `ai/` – KI-Aufgaben (MIN-334, MIN-338): `personal.py` (welche Werte persönlich sind, auch im Inserat gefunden), `pseudonym.py` (Platzhalter, Varianten, unabhängige Endkontrolle), `gateway.py` (einziger Weg zur API: maskieren, prüfen, senden, zurücksetzen, protokollieren), `tasks.py` (bewerten, entwerfen, prüfen), `prompts.py` (aus den Skills), `connection.py` (Vermittlung oder `ANTHROPIC_API_KEY`), `usage.py` (Kosten ohne Inhalte), `errors.py` (deutsche Meldungen). `routes_ai.py` hängt sie an die App; Tests ersetzen `routes_ai.new_client`.
- `entwurf.py` – Befehl, der Dateien als Entwurf sichert; für Änderungen ausserhalb der Oberfläche (Claude im Chat), vorher und nachher aufrufen.

## Regeln
- Keine persönlichen Daten in diesem Repo; Tests nutzen die erfundenen Beispieldaten aus `../lebenslauf/data/`.
- Seiten setzen Inhalte nur per `textContent` (Helfer `App.el`), nie `innerHTML`; keine Inline-Skripte (CSP).
- Jeder Pfad aus Anfragen oder Index-Dateien läuft über `dateien.im_ordner` / `relativ`.
- Schreiben ins Register immer über die ID.
- KI-Aufrufe nur über `ai.gateway.Gateway` mit Pseudonymizer; Tests nie gegen die echte API.
