# Einstiegsvorlage (onboarding)

Eine einzelne HTML-Datei, in der Personen ohne technische Kenntnisse ihre Grundlagen erfassen: Lebenslauf, Suchprofil, Stärken mit Beispielen und den Ton ihrer Anschreiben. Zwei Zweige: **Stellensuche** und **Lehrstellensuche** (Schülerinnen und Schüler). Am Schluss speichert die Person eine Datei `einstieg-<name>.json`, mit hochgeladenen Unterlagen eine `einstieg-<name>.zip`; der Import macht daraus die vier Dateien im Datenordner und legt die Unterlagen ab. Tickets MIN-333, MIN-363.

## Für Personen, die ausfüllen

- Die Vorlage öffnen: über den Link (GitHub Pages) oder `dist/einstieg.html` herunterladen und per Doppelklick öffnen.
- Alles bleibt auf dem Gerät. Die Seite lädt nichts nach und verschickt nichts; die Eingaben werden nur im Browser zwischengespeichert („Alles löschen“ entfernt sie).
- Mit „Datei laden“ geht es mit einer gespeicherten Datei weiter (JSON oder ZIP), auch auf einem anderen Gerät.
- **Unterlagen** (Schritt nach dem Start): bisheriger Lebenslauf, Zeugnisse, Zertifikate und frühere Anschreiben hochladen. Erlaubt sind PDF, Word (.docx, .doc) und Text; bei Zeugnissen und Zertifikaten auch Bilder (JPG, PNG) für Scans. Grenzen stehen in `form.json` unter `documents` (Anzahl pro Art, 15 MB pro Datei, 60 MB zusammen). Die Seite hält die Dateien nur im Speicher und warnt beim Schliessen, solange sie nicht gespeichert sind. Mit Unterlagen dürfen Angaben fehlen; der Assistent ergänzt sie später daraus.

## Import in den Datenordner

```bash
.venv/bin/python onboarding/import_bundle.py <datenordner> einstieg-<name>.json   # oder .zip
```

- Prüft die Datei mit denselben Regeln wie die Vorlage (sie ist eine Eingabe von aussen) und nennt Fehler auf Deutsch. Eine ZIP darf nur `einstieg.json` und `dokumente/<art>/<datei>` enthalten; Grössen und Anzahl werden vor dem Lesen geprüft, nichts wird entpackt.
- Schreibt `cv.yaml`, `suchprofil.md`, `anschreiben/stil.md` und `anschreiben/bausteine.md`. Bestehende Dateien ersetzt er nur mit `--force`; der alte und der neue Stand landen als Entwurf (Oberfläche, Seite „Entwürfe“).
- Legt Unterlagen unter `dokumente/<art>/` ab (nicht in Git) und listet sie in `dokumente/neu.yaml`. Gleicher Name mit anderem Inhalt bekommt „ (2)“, gleicher Inhalt wird nicht doppelt abgelegt.
- Fehlen mit Unterlagen noch Angaben (nur fehlend, nicht falsch), schreibt er die Grundlagen noch nicht, sondern legt die Antworten als `dokumente/einstieg.json` ab.
- Danach übernimmt der Skill `einstieg` die Unterlagen (Schritt 1a) und ergänzt, was fehlt. Die Skills `jobsuche` und `bewerbung` starten ihn von selbst, solange `dokumente/neu.yaml` Einträge hat oder eine Grundlage fehlt.

Die Vorlage liest die Unterlagen nicht selbst; sie bleibt ohne Netz und ohne KI (Entscheid 3.11.2026, MIN-362). Das Lesen übernimmt Claude im Skill `einstieg`, später die App (MIN-338).

## Aufbau

| Datei | Zweck |
|---|---|
| `form.json` | Abschnitte, Felder, Texte und Prüfregeln: die einzige Quelle für Vorlage und Import |
| `src/validate.js`, `validation.py` | dieselben Prüfregeln in JavaScript und Python; gemeinsame Testfälle in `tests/cases.json` |
| `src/model.js` | Zustand der Vorlage ohne DOM (Datei bauen und lesen) |
| `src/documents.js`, `documents.py` | Regeln für Unterlagen (Art, Dateityp, Grösse, Anzahl); gemeinsame Testfälle in `tests/cases.json` |
| `src/zip.js`, `archive.py` | ZIP schreiben und lesen in der Vorlage, sicher lesen beim Import |
| `src/dom.js`, `src/uploads.js`, `src/app.js`, `src/template.html`, `src/style.css` | Oberfläche |
| `build_template.py` | fügt alles zu `dist/einstieg.html` zusammen; CSP nur mit Hashes, ohne Netzzugriff |
| `convert.py`, `markdown_files.py` | Datei → `cv.yaml` (JSON Resume wie `lebenslauf/`) und Markdown nach `vorlagen/` |
| `import_bundle.py`, `import_documents.py`, `rejected.py` | Import mit Entwürfen und Ablage der Unterlagen, über `paths.py` mit `bewerbungen/` verbunden |

Nach jeder Änderung in `src/` oder `form.json`:

```bash
cd onboarding
../.venv/bin/python build_template.py      # dist/einstieg.html neu bauen und committen
../.venv/bin/python -m pytest -q           # Python, prüft auch, dass dist/ aktuell ist
node --test tests/*.test.cjs               # JavaScript
```

Ein neues Feld kommt in `form.json`, dazu in `convert.py` oder `markdown_files.py`, wohin es geschrieben wird, und ein Fall in `tests/cases.json`. Die Datei hat eine `version`; ändert sich ihre Bedeutung, wird sie erhöht.

## Veröffentlichen

Der Workflow `.github/workflows/einstieg-pages.yml` veröffentlicht nur `dist/einstieg.html` auf GitHub Pages. Er wird von Hand gestartet; dafür muss Pages in den Einstellungen des Repos auf „GitHub Actions“ stehen.
