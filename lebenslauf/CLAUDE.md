# CLAUDE.md – Modul Lebenslauf

Lebenslauf-Generator des Bewerbungsassistenten: Inhalt (YAML, JSON-Resume-Schema) und Design (Typst-Themes) getrennt. Entstanden im Spike MIN-294.

## Aufbau
- `build.py` – YAML → Zuschnitt (`tailor.py`) → `<build-dir>/cv.json` → Typst → PDF. Typst-Stammordner ist der gemeinsame Oberordner von Modul, Build-Ordner und Foto; das Foto wird direkt referenziert.
- `tests/` – pytest (`python -m pytest`), u.a. dass mit `--build-dir` nichts in `build/` des Moduls entsteht.
- `foto_editor.py` + `editor/foto.html` – lokaler Editor für den Fotoausschnitt (MIN-301): Server nur auf 127.0.0.1, Token pro Start, Host-Prüfung gegen DNS-Rebinding. Logik in `fotoausschnitt.py` (Vorschau mit wiederverwendetem `typst.Compiler`, Speichern per ruamel.yaml ohne Verlust von Kommentaren, Sicherung im Build-Ordner).
- `anschreiben.py` – Anschreiben (YAML) → PDF; Layout `themes/brief.typ`, Stil je Theme in `themes/<name>/anschreiben.typ`, Einstieg `anschreiben-main.typ` (MIN-260).
- `tailor.py` – Zuschnitt pro Stelle über `tags`, `max_highlights`, `hide`, `basics`, `sections`.
- `themes/common.typ` – Datumsformat, Beschriftungen DE/EN, Hilfsfunktionen.
- `themes/zweispaltig/` – Kopf mit rundem Foto, zwei unabhängig laufende Spalten (Design des Canva-Lebenslaufs).
- `themes/einspaltig/` – schlicht, ATS-freundlich.
- `data/beispiel.yaml`, `jobs/beispiel-daten.yaml` – erfundene Beispieldaten.
- `fonts/` – DM Sans (statisch aus der Variable Font, Familienname "DM Sans") und Liberation Sans, beide OFL.

## Regeln
- Keine persönlichen Daten in dieses Repo. Echte Daten liegen in einem separaten privaten Repo und werden per Pfad übergeben: `python build.py ../../bewerbungsassistent-daten/cv.yaml --job ../../bewerbungsassistent-daten/jobs/<firma>.yaml --build-dir ../../bewerbungsassistent-daten/.build -o ../../bewerbungsassistent-daten/out/<firma>.pdf`. Bei echten Daten immer `--build-dir` setzen.
- Strings aus den Daten werden in Typst als Text eingesetzt (`[#x]`), nie als Markup ausgewertet.
- Nach Änderungen an Themes: Beispiel in beiden Themes bauen, PDF ansehen und `pdftotext` prüfen (Text muss sauber extrahierbar sein).

## Bekannte offene Punkte (Stand 25.10.2026)
- Masse des Themes "zweispaltig" sind am Canva-Lebenslauf gemessen (Schriftgrössen über Textbreiten, Abstände über Zeilenpositionen mit `pdftotext -bbox-layout`); Abweichung meist unter 2 pt. Canva selbst ist bei Abschnittsabständen uneinheitlich, hier gilt ein fester Mittelwert.
- `--lang en` übersetzt nur Beschriftungen und Datumsangaben; Inhalte (Stichpunkte, `x-display`) bleiben in der Sprache der Daten. Mehrsprachige Inhalte sind noch offen.
- Einbindung in den Ablauf Stelle → Entwurf → Review (MIN-261).

## Tests
- `tests/test_foto.py` rendert `foto-rund` als PNG und prüft Pixel (Testbild `halbe.png`: links rot, rechts blau) – fängt Fehler beim Spiegeln und Ausschnitt ab, die Texttests nicht sehen.
- Nach Layout-Änderungen zusätzlich vorher/nachher als PNG vergleichen (`pdftoppm`, `magick compare -metric AE`).
- CI: `.github/workflows/lebenslauf.yml` (Tests, Beispiel-PDFs als Artefakt).
