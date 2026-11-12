# CLAUDE.md – Modul Lebenslauf

Lebenslauf-Generator des Bewerbungsbegleiters: Inhalt (YAML, JSON-Resume-Schema) und Design (Typst-Themes) getrennt. Entstanden im Spike MIN-294.

## Aufbau
- `build.py` – YAML → Zuschnitt (`tailor.py`) → `<build-dir>/cv.json` → Typst → PDF. Typst-Stammordner aus `typst_root.py`: gemeinsamer Oberordner von Themes, Build-Ordner und Foto; liegen sie auf verschiedenen Laufwerken (Windows), werden Themes und Foto in den Build-Ordner kopiert.
- `tests/` – pytest (`python -m pytest`), u.a. dass mit `--build-dir` nichts in `build/` des Moduls entsteht.
- `fotoausschnitt.py` – Fotoausschnitt lesen, prüfen, als Vorschau rendern (wiederverwendeter `typst.Compiler`) und per ruamel.yaml ohne Verlust von Kommentaren speichern. Die Oberfläche dazu liegt im Modul `bewerbungen` (Seite „Foto“), die Entwürfe legt dessen Ablage an.
- `anschreiben.py` – Anschreiben (YAML) → PDF; Layout `themes/brief.typ`, Stil je Theme in `themes/<name>/anschreiben.typ`, Einstieg `anschreiben-main.typ` (MIN-260).
- `dossier.py` – Bewerbungsdossier (G16, G39; `docs/design/dossier.md`): Dossier-Datei (YAML: `lebenslauf`, `anschreiben`, `gruss`, `dank`, `kennzahlen`, `anlagen`) → `<build-dir>/dossier.json` → `dossier.pdf`, `lebenslauf.pdf` und `anschreiben.pdf` aus denselben Typst-Teilen. `dossier_data.py` liest die Datenerweiterungen (Niveaus 1–6 oder A1–C2, `x-icon`, `x-monogramm`, Felder der Überschrift im Brief) und prüft sie.
- Design pro Seite (G39): `--design-deckblatt`, `--design-anschreiben`, `--design-lebenslauf`, `--design-weitere` (Standard `--theme`). Ist alles ein Design, baut dessen `dossier-main.typ`; sonst setzt `themes/dossier-mix.typ` das Dossier aus den Teilen der Designs zusammen (weitere Seiten: die des gewählten Designs an ihrem Platz). Lebenslauf und Anschreiben als Einzeldateien haben das Design ihrer Seite. Farben und Schrift kommen für alle aus `dossier.typ`.
- `mark.py`, `themes/zeichen.typ` – Zeichen und Akzentfarbe (G18, `docs/design/monogramm.md`): fünf Zeichen aus den Initialen (Ring, Block, Verschränkt nur mit zwei Buchstaben, Linie, Punkt) oder ein eigenes Logo (`x-logo`, nur im Datenordner, SVG ohne Skript und ohne Inhalte von aussen, eingepasst, nie verzerrt; `svg_check.py` liest das SVG als XML ohne DOCTYPE und Entitäten (eine schlichte DOCTYPE von SVG 1.0 oder 1.1 nimmt `without_doctype` beim Hochladen weg, #243) und prüft Elemente und Attribute nach ihrem Namen ohne Präfix, Links und url() in Stilen nur nach innen oder auf eingebettete Rasterbilder), gross auf dem Deckblatt und klein auf den Folgeseiten, bei Raster auch in der Fusszeile. Ohne Wahl (`passend`) zeichnet jedes Design sein bisheriges Zeichen, und Raster hat keines in der Fusszeile. Die Akzentfarbe ohne Wahl ist die Hauptfarbe des Designs auf dem Deckblatt (`mark.MAIN_COLOURS`); eine eigene gilt nur mit Kontrast 4.5:1 für Schrift und 3:1 auf dem Papier, sonst mit dunklerem Vorschlag. Optionen `--zeichen`, `--logo`, `--akzent` gehen vor `cv.yaml`. Jedes Zeichen setzt die Marke `<dossier-mark>` für die Tests (`tests/test_dossier_mark.py`).
- `themes/tokens.typ` – Farben, Abstände und Radien aus `docs/design/system/tokens.json` (Test hält sie gleich); `themes/dossier.typ` – Gemeinsames der Dossier-Designs; `themes/icons/` – Lucide-Auswahl (ISC) für Interessen.
- `themes/dossier-siegel/` – Entwurf „Siegel“: Teile in `theme.typ` (Lebenslauf), `anschreiben.typ` und `teile.typ` (Deckblatt, „Kurz vorgestellt“, „Danke“); Einstiege `main.typ`, `anschreiben-main.typ`, `dossier-main.typ`. Die Teile setzen nur ihren Seitenstil, Metadaten setzt die Hülle.
- `themes/dossier-raster/` – Entwurf „Raster“ (`--theme dossier-raster`): Bänder des Covers, Notenbalken, waagrechte Zeitachse aus `dossier_data.timeline` (abschaltbar mit `--ohne-zeitachse`); optionale Seiten „Auf einen Blick“ (nur mit `kennzahlen`) und Rückseite (nur mit `dank`).
- `themes/dossier-register/` – Entwurf „Register“ (`--theme dossier-register`): Deckblatt mit Inhaltsverzeichnis, Reiter am rechten Rand, Niveaus als Statusmarken mit Wort, Stationen als Tabellen mit Dauer (`dossier_data.durations`), keine Icons; optionale Seiten Beilagen (`anlagen`) und Referenzen (`references` im Lebenslauf). Die Reiterbeschriftungen zeichnet `themes/outline.typ` als Umrisse (SVG) und Typst markiert sie als Artefakt, damit `pdftotext` sie nicht liest; Einzeldateien haben keine Beschriftung.
- `page_fill.py`, `themes/page-fill.typ` – Seitenfüllung (G49, G50): Jeder Teil (Lebenslauf, Anschreiben) setzt Marken, wo er beginnt und wo sein Inhalt auf der letzten Seite endet. Ist die letzte Seite weniger als zu einem Drittel gefüllt, wählen `build.py`, `anschreiben.py` und `dossier.py` vor dem Schreiben eine Dichte (`density-cv`, `density-letter`): enger (Abstände, Zeilenhöhe, Schrift nie unter 9 pt), bis eine Seite wegfällt, oder weiter, bis die letzte Seite genug Inhalt hat; die kleinere Änderung gewinnt, Inhalt fällt nie weg. Überschriften bleiben bei ihrem ersten Eintrag, kurze Abschnitte (bis fünf Einträge) bleiben zusammen, der letzte Eintrag einzeiliger Abschnitte steht nie allein. Tests: `tests/test_page_fill.py` misst mit `pdftotext -bbox-layout`, `tests/test_page_fill_choice.py` die Wahl.
- `tailor.py` – Zuschnitt pro Stelle über `tags`, `max_highlights`, `hide`, `basics`, `sections`.
- `themes/common.typ` – Datumsformat, Beschriftungen DE/EN, Hilfsfunktionen.
- `themes/zweispaltig/` – Kopf mit rundem Foto, zwei unabhängig laufende Spalten (Design des Canva-Lebenslaufs); ab Seite 2 Hauptspalte links (Seite 1 wird ausgemessen, Einträge sind unteilbar).
- `themes/einspaltig/` – schlicht, ATS-freundlich.
- `data/beispiel.yaml`, `jobs/beispiel-daten.yaml` – erfundene Beispieldaten.
- `fonts/` – DM Sans (statisch aus der Variable Font, Familienname "DM Sans") und Liberation Sans, beide OFL.

## Regeln
- Keine persönlichen Daten in dieses Repo. Echte Daten liegen in einem separaten privaten Repo und werden per Pfad übergeben: `python build.py ../../bewerbungsassistent-daten/cv.yaml --job ../../bewerbungsassistent-daten/jobs/<firma>.yaml --build-dir ../../bewerbungsassistent-daten/.build -o ../../bewerbungsassistent-daten/out/<firma>.pdf`. Bei echten Daten immer `--build-dir` setzen.
- Strings aus den Daten werden in Typst als Text eingesetzt (`[#x]`), nie als Markup ausgewertet.
- Nach Änderungen an Themes: Beispiel in beiden Themes bauen, PDF ansehen und `pdftotext` prüfen (Text muss sauber extrahierbar sein).

## Bekannte offene Punkte (Stand 25.10.2026)
- Masse des Themes "zweispaltig" sind am Canva-Lebenslauf gemessen (Schriftgrössen über Textbreiten, Abstände über Zeilenpositionen mit `pdftotext -bbox-layout`); Abweichung meist unter 2 pt. Canva selbst ist bei Abschnittsabständen uneinheitlich, hier gilt ein fester Mittelwert.
- `--lang en` übersetzt Beschriftungen und Datumsangaben; Inhalte sind mehrsprachig, wenn sie als `{de: …, en: …}` erfasst sind (`build.waehle_sprache`, MIN-300). Einsprachige Texte bleiben, wie sie sind.

## Tests
- `tests/test_foto.py` rendert `foto-rund` als PNG und prüft Pixel (Testbild `halbe.png`: links rot, rechts blau) – fängt Fehler beim Spiegeln und Ausschnitt ab, die Texttests nicht sehen.
- Nach Layout-Änderungen zusätzlich vorher/nachher als PNG vergleichen (`pdftoppm`, `magick compare -metric AE`).
- CI: `.github/workflows/lebenslauf.yml` (Tests, Beispiel-PDFs als Artefakt).
