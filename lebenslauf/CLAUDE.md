# CLAUDE.md – Modul Lebenslauf

Lebenslauf-Generator des Bewerbungsassistenten: Inhalt (YAML, JSON-Resume-Schema) und Design (Typst-Themes) getrennt. Entstanden im Spike MIN-294.

## Aufbau
- `build.py` – YAML → Zuschnitt (`tailor.py`) → `<build-dir>/cv.json` → Typst → PDF. Typst-Stammordner ist der gemeinsame Oberordner von Modul, Build-Ordner und Foto; das Foto wird direkt referenziert.
- `tests/` – pytest (`python -m pytest`), u.a. dass mit `--build-dir` nichts in `build/` des Moduls entsteht.
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
- Abstände im Theme "zweispaltig" etwas enger als im Canva-Original; Überschrift "Berufserfahrung (Fortsetzung)" auf Seite 2 fehlt.
- Englische Fassung (`--lang en`) noch nicht getestet.
- Einbindung in den Ablauf Stelle → Entwurf → Review (MIN-261).
- CI: Beispiel-PDFs in GitHub Actions bauen.
