# Bewerbungsassistent

Werkzeuge und Claude-Skills für den ganzen Bewerbungsablauf: passende Stellen finden, Lebenslauf und Anschreiben pro Stelle zuschneiden, vor dem Absenden prüfen und den Versand vorbereiten. Ausgelegt auf den Schweizer Stellenmarkt (job-room.ch, jobs.ch, LinkedIn).

## Module

| Ordner | Inhalt | Stand |
|---|---|---|
| [`lebenslauf/`](lebenslauf/README.md) | Lebenslauf als PDF aus YAML (JSON Resume) und Typst-Themes, Zuschnitt pro Stelle über Tags | Prototyp |
| [`skills/jobsuche/`](skills/jobsuche/SKILL.md) | Claude-Skill: Stellensuche auf job-room.ch, jobs.ch, LinkedIn und Karriereseiten, Bewertung, Jobliste in Google Sheets | im Einsatz |
| [`vorlagen/`](vorlagen/) | Vorlagen für die persönlichen Dateien (z.B. `suchprofil.md`) | |
| `anschreiben/` | Bausteine und Ablauf fürs Anschreiben | geplant |
| `pruefung/` | Prüfung vor dem Absenden | geplant |

## Eigene Daten

Dieses Repo enthält nur Code, Themes, Skills und erfundene Beispieldaten. Persönliche Daten – Stammdaten des Lebenslaufs, Foto, Suchprofil, Zuschnitte pro Stelle, erzeugte PDFs – liegen in einem separaten privaten Ordner oder Repo daneben und werden per Pfad übergeben:

```
dev/
  bewerbungsassistent/          ← dieses Repo
  bewerbungsassistent-daten/    ← privat: cv.yaml, foto.jpg, suchprofil.md, jobs/, out/
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
  -o ../../bewerbungsassistent-daten/out/ki.pdf
```

## Skill einrichten

`skills/jobsuche/` in Claude Code nach `~/.claude/skills/jobsuche/` kopieren oder verlinken; in claude.ai als Skill hochladen. Vorher `vorlagen/suchprofil.md` in den privaten Datenordner kopieren und ausfüllen. Der Skill braucht Claude in Chrome (Suche im eingeloggten Browser-Tab) und für die Jobliste den Google-Sheets-Connector.

## Lizenz

[GNU General Public License v3.0](LICENSE). Ohne Gewährleistung und ohne Haftung (Abschnitte 15 und 16 der Lizenz).

Schriften unter `lebenslauf/fonts/`: SIL Open Font License (siehe dort).
