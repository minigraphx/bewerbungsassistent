# Einstiegsvorlage (onboarding)

Eine einzelne HTML-Datei, in der Personen ohne technische Kenntnisse ihre Grundlagen erfassen: Lebenslauf, Suchprofil, Stärken mit Beispielen und den Ton ihrer Anschreiben. Zwei Zweige: **Stellensuche** und **Lehrstellensuche** (Schülerinnen und Schüler). Am Schluss speichert die Person eine Datei `einstieg-<name>.json`; der Import macht daraus die vier Dateien im Datenordner. Ticket MIN-333.

## Für Personen, die ausfüllen

- Die Vorlage öffnen: über den Link (GitHub Pages) oder `dist/einstieg.html` herunterladen und per Doppelklick öffnen.
- Alles bleibt auf dem Gerät. Die Seite lädt nichts nach und verschickt nichts; die Eingaben werden nur im Browser zwischengespeichert („Alles löschen“ entfernt sie).
- Mit „Datei laden“ geht es mit einer gespeicherten Datei weiter, auch auf einem anderen Gerät.

## Import in den Datenordner

```bash
.venv/bin/python onboarding/import_bundle.py <datenordner> einstieg-<name>.json
```

- Prüft die Datei mit denselben Regeln wie die Vorlage (sie ist eine Eingabe von aussen) und nennt Fehler auf Deutsch.
- Schreibt `cv.yaml`, `suchprofil.md`, `anschreiben/stil.md` und `anschreiben/bausteine.md`. Bestehende Dateien ersetzt er nur mit `--force`; der alte und der neue Stand landen als Entwurf (Oberfläche, Seite „Entwürfe“).
- Danach den Lebenslauf bauen und mit der Person durchgehen (siehe `lebenslauf/README.md`).

Claude kann die Datei auch aus dem Interview im Skill `einstieg` vorbefüllen; die Person lädt sie dann in der Vorlage, prüft und ergänzt.

## Aufbau

| Datei | Zweck |
|---|---|
| `form.json` | Abschnitte, Felder, Texte und Prüfregeln: die einzige Quelle für Vorlage und Import |
| `src/validate.js`, `validation.py` | dieselben Prüfregeln in JavaScript und Python; gemeinsame Testfälle in `tests/cases.json` |
| `src/model.js` | Zustand der Vorlage ohne DOM (Datei bauen und lesen) |
| `src/dom.js`, `src/app.js`, `src/template.html`, `src/style.css` | Oberfläche |
| `build_template.py` | fügt alles zu `dist/einstieg.html` zusammen; CSP nur mit Hashes, ohne Netzzugriff |
| `convert.py`, `markdown_files.py` | Datei → `cv.yaml` (JSON Resume wie `lebenslauf/`) und Markdown nach `vorlagen/` |
| `import_bundle.py` | Import mit Entwürfen, über `paths.py` mit `bewerbungen/` verbunden |

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
