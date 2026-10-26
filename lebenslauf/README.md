# Lebenslauf

Modul des [Bewerbungsassistenten](../README.md): Lebenslauf als PDF aus Daten erzeugen – Inhalt und Design getrennt.

- **Inhalt:** eine YAML-Datei nach dem [JSON-Resume-Schema](https://jsonresume.org/schema) mit wenigen Erweiterungen.
- **Design:** Themes in [Typst](https://typst.app) unter `themes/<name>/`.
- **Zuschnitt pro Stelle:** eine kleine Bewerbungsdatei wählt per Tags aus, was in die Fassung kommt, und überschreibt einzelne Texte.

## Schnellstart

```bash
pip install -r ../requirements.txt
python build.py data/beispiel.yaml -o build/beispiel.pdf
python build.py data/beispiel.yaml --theme einspaltig -o build/beispiel-einspaltig.pdf
python build.py data/beispiel.yaml --job jobs/beispiel-daten.yaml -o build/daten.pdf
```

Optionen: `--theme` (Standard `zweispaltig`), `--lang de|en`, `-o` Ausgabedatei, `--build-dir` Ordner für Zwischenstände (Standard `build/` in diesem Modul).

## Daten

Standardfelder aus JSON Resume: `basics`, `work`, `projects`, `skills`, `languages`, `interests`, `education`, `certificates`.

Erweiterungen:

| Feld | Zweck |
|---|---|
| `basics.details` | Zusatzzeile im Kopf, z.B. Geburtsdatum, Nationalität |
| `basics.image` | Foto, Pfad relativ zur Datendatei |
| `basics.x-image` | Darstellung des Fotos im runden Ausschnitt: `mirror` (true/false, an der senkrechten Achse spiegeln), `zoom` (1–4), `x` und `y` (0–1, Bildausschnitt; 0 = links/oben, 0.5 = Mitte, 1 = rechts/unten). Beispiel: `{mirror: true, zoom: 1.3, x: 0.5, y: 0.2}` |
| `teaching` | Abschnitt „Lehre & Training“, gleicher Aufbau wie `work` |
| `projects[].group` | `main` (Standard) oder `more` für „Weitere Projekte“ |
| `x-display` | eigener Text statt Zeitraum, z.B. `seit 2021` |
| `text` | (Bildung/Zertifikate) fertiger Satz statt Zusammensetzung |
| `tags` | an Einträgen und Stichpunkten, für den Zuschnitt |

Daten: `"2022-06"` wird zu „Juni 2022“, `2018` bleibt eine Jahreszahl; fehlendes `endDate` heisst „heute“.

Stichpunkte (`highlights`) sind Text oder `{text: ..., tags: [...]}`.

## Fotoausschnitt im Browser einstellen

```bash
python foto_editor.py ../../meine-daten/cv.yaml --build-dir ../../meine-daten/.build
```

Öffnet eine lokale Seite (nur `127.0.0.1`). Dort lässt sich das Foto per Maus verschieben, mit dem Mausrad zoomen und spiegeln. Die Vorschau rendert Typst mit derselben Funktion wie das Theme, sie entspricht also genau dem PDF. „Speichern“ schreibt `basics.x-image` in die Datendatei; Kommentare und Formatierung bleiben erhalten, vor jedem Speichern liegt eine Sicherung `<datei>.<zeitstempel>.bak` im Build-Ordner. Optionen: `--port`, `--kein-browser`.

## Zuschnitt pro Stelle

```yaml
tags: [ki, test]          # Einträge ohne Tags sind immer dabei, getaggte nur bei Übereinstimmung
max_highlights: 4         # höchstens 4 Stichpunkte pro Station
hide: ["Sykes Enterprises"]
basics:
  label: Software-Entwickler – KI-Anwendungen
  summary: Angepasstes Profil …
sections:                 # ganzen Abschnitt ersetzen (optional)
  skills: [...]
```

## Eigenes Theme

1. `themes/zweispaltig` kopieren, z.B. nach `themes/meins`.
2. In `theme.typ` die Funktion `lebenslauf(cv, sprache, stand, stil)` anpassen. Hilfsfunktionen (Datum, Beschriftungen DE/EN) liegen in `themes/common.typ`.
3. `python build.py data/beispiel.yaml --theme meins`

Farben, Schriften, Schriftgrössen, Abstände, Ränder, Spaltenbreite und die Reihenfolge der Abschnitte stehen im Dictionary `standard-stil` am Anfang jedes Themes.

Im Theme `zweispaltig` laufen beide Spalten unabhängig über die Seiten. Wird ein Abschnitt auf der nächsten Seite fortgesetzt, steht dort sein Titel mit „(Fortsetzung)“ bzw. „(continued)“; wandert ein Abschnitt ganz auf die neue Seite, bleibt es beim normalen Titel. Titel, die breiter als die Spalte sind, werden auf Spaltenbreite verkleinert. Das Etikett im Kopf (`basics.label`) bricht nach dem ersten „ – “ um (`label-umbruch-nach-strich`, abschaltbar). Die Hilfsfunktionen dafür (`eintraege`, `foto-rund`) liegen in `themes/common.typ` und lassen sich in eigenen Themes verwenden.

## Eigene Daten

Persönliche Daten gehören **nicht** in ein öffentliches Repo. `private/` und `build/` sind in `.gitignore`; besser ist ein separates privates Repo oder ein Ordner ausserhalb des Repos. Mit `--build-dir` landet auch der Zwischenstand (`cv.json` mit allen Daten) dort statt in diesem Modul; das Foto wird direkt aus dem Datenordner gelesen, nicht kopiert:

```bash
python build.py ../../meine-daten/cv.yaml --build-dir ../../meine-daten/.build -o ../../meine-daten/out/cv.pdf
```

## Tests

```bash
pip install -r ../requirements-dev.txt
python -m pytest
```

## Schriften

`fonts/` enthält DM Sans (SIL Open Font License, siehe `fonts/DMSans-OFL.txt`) und Liberation Sans (SIL Open Font License).
