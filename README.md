# Bewerbungsassistent

Werkzeuge und Claude-Skills für den ganzen Bewerbungsablauf: passende Stellen finden, Lebenslauf und Anschreiben pro Stelle zuschneiden, vor dem Absenden prüfen und den Versand vorbereiten. Ausgelegt auf den Schweizer Stellenmarkt (job-room.ch, jobs.ch, LinkedIn).

## Module

| Ordner | Inhalt |
|---|---|
| [`lebenslauf/`](lebenslauf/README.md) | Lebenslauf und Anschreiben als PDF aus YAML und Typst-Themes, Zuschnitt pro Stelle über Tags, mehrsprachige Inhalte |
| [`bewerbungen/`](bewerbungen/README.md) | Lokale Oberfläche: Bewerbungsregister, Unterlagen erstellen und prüfen, Versand erfassen, Entwürfe und Versionen, Job-Room-Angaben, Fotoausschnitt |
| [`skills/jobsuche/`](skills/jobsuche/SKILL.md) | Claude-Skill: Stellensuche auf job-room.ch, jobs.ch, LinkedIn und Karriereseiten, Jobliste in Google Sheets |
| [`skills/bewerbung/`](skills/bewerbung/SKILL.md) | Claude-Skill: von der Stelle zur fertigen Bewerbung – Variante wählen, Anschreiben im eigenen Stil, Prüfung, Versand |
| [`vorlagen/`](vorlagen/) | Vorlagen für die persönlichen Dateien (Suchprofil, Stilprofil, Bausteine fürs Anschreiben) |

## Eigene Daten

Dieses Repo enthält nur Code, Themes, Skills und erfundene Beispieldaten. Persönliche Daten – Stammdaten des Lebenslaufs, Foto, Suchprofil, Zuschnitte pro Stelle, erzeugte PDFs – liegen in einem separaten privaten Ordner oder Repo daneben und werden per Pfad übergeben:

```
dev/
  bewerbungsassistent/          ← dieses Repo
  bewerbungsassistent-daten/    ← privat: cv.yaml, foto.jpg, suchprofil.md, jobs/, bewerbungen.yaml, …
```

## Schnellstart

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd lebenslauf
python build.py data/beispiel.yaml -o build/beispiel.pdf
```

Eigene Fassung:

```bash
python build.py ../../bewerbungsassistent-daten/cv.yaml \
  --job ../../bewerbungsassistent-daten/jobs/ki.yaml \
  --build-dir ../../bewerbungsassistent-daten/.build \
  -o ../../bewerbungsassistent-daten/out/ki.pdf
```

Lokale Oberfläche:

```bash
cd bewerbungen
python app.py ../../bewerbungsassistent-daten
```

## Skills einrichten

`skills/jobsuche/` und `skills/bewerbung/` in Claude Code nach `~/.claude/skills/` kopieren oder verlinken; in claude.ai als Skill hochladen. Vorher die Vorlagen aus `vorlagen/` in den privaten Datenordner kopieren und ausfüllen (`suchprofil.md`, `anschreiben/stil.md`, `anschreiben/bausteine.md`). Der Skill braucht Claude in Chrome (Suche im eingeloggten Browser-Tab) und für die Jobliste den Google-Sheets-Connector.

## Lizenz

[GNU General Public License v3.0](LICENSE). Ohne Gewährleistung und ohne Haftung (Abschnitte 15 und 16 der Lizenz).

Schriften unter `lebenslauf/fonts/`: SIL Open Font License (siehe dort).
