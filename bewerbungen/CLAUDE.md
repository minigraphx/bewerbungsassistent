# CLAUDE.md – Modul Bewerbungen

Verwaltung und lokale Oberfläche des Bewerbungsassistenten (MIN-261 Ablauf, MIN-262 Prüfung, MIN-263 Versand, MIN-303/304 Entwürfe und Versionen, MIN-306 Register, MIN-307 Varianten). Baut auf `../lebenslauf` auf, nie umgekehrt (`pfade.py` macht es importierbar; pytest über `pythonpath` in `pytest.ini`).

## Aufbau
- `app.py` – Einstieg: `python app.py <datenordner>`; Server (`server.py`), Routen (`routen_*.py`), Seiten (`seiten/`).
- `server.py` – nur 127.0.0.1, Token pro Start (GET `t`, POST `X-Token` + JSON), Host-Prüfung, CSP ohne Inline-Skripte; ValueError → 400, KeyError → 404.
- `kontext.py` – Datenordner, Build-Ordner, Ablage, Versionierung; `mit_entwurf` legt beim Schreiben Entwürfe davor/danach an.
- `ablage.py` – Entwürfe in `.entwuerfe/` (SHA-256, Index); löschbar solange nicht genutzt.
- `versionen.py` – Git-Commit beim Versand (nur die genannten Dateien, Ersatz-Autor ohne Git-Konfiguration); `OhneGit` als Ausweichlösung.
- `register.py` – `bewerbungen.yaml`, Prüfung, IDs, Job-Room-Vorschlag, Import/Export im Format der Jobliste.
- `varianten.py` – `varianten.yaml`, Vorschlag per Stichwort-Abgleich.
- `unterlagen.py` – Lebenslauf (Variante) und Anschreiben pro Bewerbung bauen.
- `inhalte.py` – Text-Editor (MIN-302): erlaubte Dateien nach Muster, Prüfung je Dateityp mit Probebau im Build-Ordner.
- `pruefung.py` – formale Prüfung der PDFs und des Anschreibens.
- `versand.py` – Versand erfassen: ablegen (dedupliziert), Entwürfe genutzt, Register, Git.
- `dateien.py` – atomar schreiben, Pfade auf den Datenordner beschränken.

## Regeln
- Keine persönlichen Daten in diesem Repo; Tests nutzen die erfundenen Beispieldaten aus `../lebenslauf/data/`.
- Seiten setzen Inhalte nur per `textContent` (Helfer `App.el`), nie `innerHTML`; keine Inline-Skripte (CSP).
- Jeder Pfad aus Anfragen oder Index-Dateien läuft über `dateien.im_ordner` / `relativ`.
- Schreiben ins Register immer über die ID.
