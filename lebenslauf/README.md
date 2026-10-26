# Lebenslauf

Modul des [Bewerbungsassistenten](../README.md): Lebenslauf und Anschreiben als PDF aus Daten erzeugen – Inhalt und Design getrennt.

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

Optionen: `--theme` (Standard `zweispaltig`), `--lang de|en` (Beschriftungen, Datumsangaben und mehrsprachige Inhalte), `-o` Ausgabedatei, `--build-dir` Ordner für Zwischenstände (Standard `build/` in diesem Modul).

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

## Anschreiben

```bash
python anschreiben.py data/anschreiben-beispiel.yaml -o build/anschreiben.pdf
python anschreiben.py ../../meine-daten/bewerbungen/firma/anschreiben.yaml --build-dir ../../meine-daten/.build -o ../../meine-daten/out/firma-anschreiben.pdf
```

Ein Anschreiben ist eine kleine YAML-Datei (Beispiel: [`data/anschreiben-beispiel.yaml`](data/anschreiben-beispiel.yaml)):

| Feld | Zweck |
|---|---|
| `lebenslauf` | Pfad zum Lebenslauf (relativ zur Datei); daraus kommen Name und Kontaktzeile. Alternativ `--cv` oder `absender: {name, zeile}` |
| `empfaenger` | Zeilen der Anschrift, z.B. `[Firma AG, Frau Petra Meier, Strasse 5, 3011 Bern]` |
| `ort`, `datum` | Ort und Datum (`2026-10-24`); ohne Datum gilt heute |
| `betreff`, `anrede`, `gruss` | Betreffzeile, Anrede, Grussformel |
| `text` | Brieftext; Absätze durch Leerzeilen trennen |
| `sprache` | `de` (Standard) oder `en`, für das Datumsformat |

Das Layout steht in `themes/brief.typ`; jedes Theme setzt darin nur seinen Stil (`themes/<name>/anschreiben.typ`). Gruss und Unterschrift werden nie getrennt.

## Fotoausschnitt einstellen

Im Browser über die lokale Oberfläche des Moduls [`bewerbungen`](../bewerbungen/README.md), Seite „Foto“: Foto per Maus verschieben, mit dem Mausrad zoomen und spiegeln. Die Vorschau rendert Typst mit derselben Funktion wie das Theme. Gespeichert wird `basics.x-image`; Kommentare und Formatierung der Datendatei bleiben erhalten (`fotoausschnitt.py`).

## Mehrsprachige Inhalte

Jeder Text kann statt eines Strings eine Zuordnung nach Sprache sein; `--lang` wählt die Sprache, fehlt sie, gilt Deutsch:

```yaml
summary:
  de: Software-Entwicklerin mit zehn Jahren Praxis …
  en: Software developer with ten years of experience …
highlights:
  - {de: Aufbau von Datenpipelines, en: Built data pipelines}
  - text: {de: Schulungen intern, en: Internal training}
    tags: [bildung]
```

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
