# CLAUDE.md – Bewerbungsassistent

Öffentliches Repo `minigraphx/bewerbungsassistent`. Werkzeuge und Skills für den Bewerbungsablauf: Stellensuche → Lebenslauf und Anschreiben pro Stelle → Prüfung → Versand. Geplant und verfolgt im Linear-Projekt "Bewerbungs-Assistent" (Team Minigraphx, Tickets ab MIN-255).

## Aufbau
- `lebenslauf/` – Lebenslauf und Anschreiben als PDF (eigene `CLAUDE.md` dort).
- `bewerbungen/` – lokale Oberfläche und Verwaltung: Register, Unterlagen, Prüfung, Versand, Entwürfe/Versionen (eigene `CLAUDE.md`). Baut auf `lebenslauf/` auf.
- `skills/jobsuche/SKILL.md` – allgemeiner Skill für die Stellensuche; alles Persönliche steht im Suchprofil.
- `skills/bewerbung/SKILL.md` – Skill für den Ablauf Stelle → Unterlagen → Prüfung → Versand; Persönliches in Stilprofil und Bausteinen.
- `vorlagen/` – Vorlagen für persönliche Dateien, mit erfundenen Werten.
- `requirements.txt` – Python-Abhängigkeiten aller Module; venv unter `.venv/`.

## Regeln
- Keine persönlichen Daten in dieses Repo: keine echten Namen, Adressen, Fotos, Sheet-IDs, Bewerbungsstände oder konkreten Zielfirmen mit Status. Sie liegen im privaten Ordner `../bewerbungsassistent-daten/` (eigenes privates Repo) und werden per Pfad übergeben.
- Skills bleiben allgemein: personenbezogene Kriterien, Region, Keywords und Zielfirmen gehören ins Suchprofil, nicht in den Skill.
- Texte auf Deutsch, Schweizer Schreibweise (ss statt ß).
- Dateien im Datenordner vor und nach jeder Änderung mit `bewerbungen/entwurf.py <datenordner> <datei> -m "<was>"` als Entwurf sichern; committet wird dort erst beim Versand.
