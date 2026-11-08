# Einstiegsvorlage (onboarding)

Eine einzelne HTML-Datei, in der Personen ohne technische Kenntnisse ihre Grundlagen erfassen: Lebenslauf, Suchprofil, Stärken mit Beispielen und den Ton ihrer Anschreiben. Zwei Zweige: **Stellensuche** und **Lehrstellensuche** (Schülerinnen und Schüler). Am Schluss speichert die Person eine Datei `einstieg-<name>.json`, mit hochgeladenen Unterlagen eine `einstieg-<name>.zip`; der Import macht daraus die vier Dateien im Datenordner und legt die Unterlagen ab. Tickets MIN-333, MIN-363.

## Für Personen, die ausfüllen

- Die Vorlage öffnen: `dist/einstieg.html` per Doppelklick. Öffentlich steht sie nicht mehr; im Normalfall erfasst man die Angaben unter „Meine Angaben“ in der App.
- Alles bleibt auf dem Gerät. Die Seite lädt nichts nach und verschickt nichts; die Eingaben werden nur im Browser zwischengespeichert („Alles löschen“ entfernt sie).
- Mit „Datei laden“ geht es mit einer gespeicherten Datei weiter (JSON oder ZIP), auch auf einem anderen Gerät.
- **Unterlagen** (Schritt nach dem Start; in der App auf dem Start): bisheriger Lebenslauf, Zeugnisse, Zertifikate und frühere Anschreiben hochladen. Erlaubt sind PDF, Word (.docx, .doc) und Text; bei Zeugnissen und Zertifikaten auch Bilder (JPG, PNG) für Scans. Grenzen stehen in `form.json` unter `documents` (Anzahl pro Art, 15 MB pro Datei, 60 MB zusammen). Die Seite bewahrt die Dateien in der IndexedDB des Browsers auf (localStorage ist dafür zu klein), so sind sie nach einem Neustart wieder da; „Alles löschen“ entfernt sie. Kann der Browser sie nicht aufbewahren (z.B. im privaten Fenster), warnt die Seite beim Schliessen, solange die Datei nicht gespeichert ist. Mit Unterlagen dürfen Angaben fehlen; die App ergänzt sie später daraus.

## Import in den Datenordner

```bash
.venv/bin/python onboarding/import_bundle.py <datenordner> einstieg-<name>.json   # oder .zip
```

- Prüft die Datei mit denselben Regeln wie die Vorlage (sie ist eine Eingabe von aussen) und nennt Fehler auf Deutsch. Eine ZIP darf nur `einstieg.json` und `dokumente/<art>/<datei>` enthalten; Grössen und Anzahl werden vor dem Lesen geprüft, nichts wird entpackt.
- Schreibt `cv.yaml`, `suchprofil.md`, `anschreiben/stil.md` und `anschreiben/bausteine.md`. Bestehende Dateien ersetzt er nur mit `--force`; der alte und der neue Stand landen als Entwurf (Oberfläche, Seite „Entwürfe“). Beim Ersetzen fliessen die Angaben in den bestehenden Lebenslauf ein, statt ihn neu zu schreiben (`cv_merge.py`): Was das Formular nicht schreibt (etwa `basics.image`, `basics.x-image`, `projects`, `teaching`, `x-…`), Felder an Einträgen, die es nicht kennt (etwa `x-display`, `text`), Kommentare und Reihenfolge bleiben. Tags an Stationen, Kenntnissen, Zertifikaten und Stichpunkten zeigt das Formular seit G24; sie gehören damit zu den Angaben: Ein Stichpunkt mit Tags wird zu `{text, tags}`, einer ohne zu reinem Text. Eine leere Liste `tags: []` in den Antworten entfernt die Tags; fehlt der Schlüssel (etwa in Dateien und Zwischenständen von vor G24, oder bei einem Stichpunkt als reinem Text), bleiben die Tags aus `cv.yaml`. Die Seite schickt darum die Tags überall mit, wo sie sie kennt, auch leer. Tags, die keine Liste von Wörtern sind, zeigt es nicht und lässt sie stehen. Ein ohne Änderung gespeicherter Lebenslauf bleibt Zeichen für Zeichen gleich. Lässt sich `cv.yaml` nicht lesen, bleibt die Datei unverändert.
- Legt Unterlagen unter `dokumente/<art>/` ab (nicht in Git) und listet sie in `dokumente/neu.yaml`. Gleicher Name mit anderem Inhalt bekommt „ (2)“, gleicher Inhalt wird nicht doppelt abgelegt.
- Fehlen mit Unterlagen noch Angaben (nur fehlend, nicht falsch), schreibt er die Grundlagen noch nicht, sondern legt die Antworten als `dokumente/einstieg.json` ab.
- In der App: „Aus Unterlagen vorbefüllen“ (siehe unten). Dort gelesene Unterlagen stehen mit `gelesen: true` in `dokumente/neu.yaml`; nach dem vollständigen Übernehmen verschwinden diese Einträge, die Dateien bleiben.
- Danach übernimmt der Skill `einstieg` die Unterlagen (Schritt 1a) und ergänzt, was fehlt. Die Skills `jobsuche` und `bewerbung` starten ihn von selbst, solange `dokumente/neu.yaml` Einträge hat oder eine Grundlage fehlt.

Die Vorlage liest die Unterlagen nicht selbst; sie bleibt ohne Netz und ohne KI (Entscheid 3.11.2026, MIN-362). Das Lesen übernimmt Claude im Skill `einstieg`, später die App (MIN-367).

Aus denselben Quellen entsteht die Seite „Meine Angaben“ der App (`bewerbungen/seiten/angaben.html`, MIN-366): zusätzlich mit `src/appbackend.js`, mit Netzwerk nur zur App selbst (`connect-src 'self'`), Zwischenstand und Unterlagen im Datenordner. Gibt es dort schon einen `cv.yaml`, füllt die Seite die Schritte des Lebenslaufs daraus (`cv_read.py`, G23), ausser es liegen noch nicht übernommene Eingaben vor. Für Tags schlägt sie vor, was schon in `cv.yaml`, `varianten.yaml` und `jobs/*.yaml` des Datenordners steht (`known_tags.py`, G24); neue Tags lassen sich frei eingeben, ein Wort pro Tag, mit Komma getrennt. Die Datei zum Weitergeben schlägt nur Tags vor, die schon im Formular stehen. Die Datei zum Weitergeben enthält diesen Teil nicht und bleibt ohne Netz. `build_template.py` schreibt beide Fassungen, `--check` prüft beide.

Seit der Gestaltung MIN-369 hat die Seite der App das Menü der übrigen Seiten (aus `bewerbungen/seiten/uebersicht.html` übernommen, darum nach einer Änderung dort neu bauen) und lädt `texte.js` und `app.js` der App (`script-src 'self'` plus Hash). Der Start zeigt die Wahl aus der Einrichtung (Stelle oder Lehrstelle, Anrede, RAV) statt der zwei Karten und daneben die Unterlagen mit „Vorbefüllen“; einen eigenen Schritt „Unterlagen“ gibt es nur in der Datei zum Weitergeben. Die Abschnitte von `form.json` stehen in beiden Fassungen in fünf Schritten (`src/steps.js`), untereinander statt als Reiter, damit Marken und fehlende Angaben sichtbar bleiben.

## Aufbau

| Datei | Zweck |
|---|---|
| `form.json` | Abschnitte, Felder, Texte und Prüfregeln: die einzige Quelle für Vorlage und Import |
| `src/validate.js`, `validation.py` | dieselben Prüfregeln in JavaScript und Python; gemeinsame Testfälle in `tests/cases.json` |
| `src/model.js` | Zustand der Vorlage ohne DOM (Datei bauen und lesen) |
| `src/steps.js` | die fünf Schritte: welche Abschnitte zusammen stehen, pro Zweig |
| `src/documents.js`, `documents.py` | Regeln für Unterlagen (Art, Dateityp, Grösse, Anzahl); gemeinsame Testfälle in `tests/cases.json` |
| `src/zip.js`, `archive.py` | ZIP schreiben und lesen in der Vorlage, sicher lesen beim Import |
| `src/dom.js`, `src/uploads.js`, `src/app.js`, `src/template.html`, `src/style.css` | Oberfläche |
| `src/appbackend.js`, `src/prefill.js`, `src/appnav.css` | nur Seite der App: Anfragen an die App, Vorbefüllen, Stil des Menüs |
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

## Aus Unterlagen vorbefüllen (nur in der App)

Die Datei zum Weitergeben (`dist/einstieg.html`) bleibt ohne Netz; nur die Seite „Meine Angaben“ der App kann vorbefüllen.

- **Lesen, lokal** (`read_documents.py`): PDF mit `pypdf`, Word `.docx` über `word/document.xml` (Grössen begrenzt, keine DTD und Entitäten), Text direkt. Der Lebenslauf zuerst, höchstens 40 000 Zeichen pro Datei und 120 000 insgesamt. Alte `.doc`-Dateien, Bilder und Scans werden nicht gesendet; die Person bekommt den Grund und was zu tun ist.
- **Senden** (`prefill.py`, Aufgabe `prefill` in `bewerbungen/ai/tasks.py`): nur über das Gateway. Ohne Namen im Formular oder in `cv.yaml` geht nichts raus. Maskiert werden die Angaben aus dem Formular und `cv.yaml`, dazu was in den Unterlagen gefunden wird: E-Mail, Telefon, Strasse, Postleitzahl mit Ort, Geburtsdatum, Heimatort, Nationalität, AHV-Nummer, Weblinks, „Frau/Herr Name“. Unsichtbare Zeichen werden vorher entfernt. Dateinamen bleiben auf dem Computer; die KI sieht „Unterlage 1“.
- **Grenze:** Namen anderer Personen ohne „Frau“ oder „Herr“, etwa die Unterschrift auf einem Zeugnis, werden nicht erkannt und gehen mit. Die Seite sagt das vor dem Klick.
- **Prüfen** (`prefill.clean_answer`): Nur bekannte Abschnitte und Felder, Werte nach denselben Regeln wie im Formular, jeder Eintrag mit Quelle. Was nicht passt, fällt weg und wird gezählt. Kontaktangaben und Suchwünsche werden gar nicht erst erfragt.
- **Oberfläche:** Vorschläge kommen nur in leere Felder und bleiben markiert („Vorschlag aus …, bitte prüfen“), bis die Person sie bestätigt oder den Eintrag entfernt (`state.suggested`, im Zwischenstand mitgespeichert); Ändern allein zählt nicht als Prüfen. Solange etwas ungeprüft ist, lässt sich nichts übernehmen. In `cv.yaml` landet erst etwas beim Übernehmen.
