# CLAUDE.md – Bewerbungsassistent

Öffentliches Repo `minigraphx/bewerbungsassistent`. Werkzeuge und Skills für den Bewerbungsablauf: Stellensuche → Lebenslauf und Anschreiben pro Stelle → Prüfung → Versand. Geplant und verfolgt im Linear-Projekt "Bewerbungs-Assistent" (Team Minigraphx, Tickets MIN-255 bis MIN-263, MIN-294).

## Aufbau
- `lebenslauf/` – Lebenslauf-Generator (eigene `CLAUDE.md` dort).
- `skills/jobsuche/SKILL.md` – allgemeiner Skill für die Stellensuche; alles Persönliche steht im Suchprofil.
- `vorlagen/` – Vorlagen für persönliche Dateien, mit erfundenen Werten.
- `requirements.txt` – Python-Abhängigkeiten aller Module; venv unter `.venv/`.

## Regeln
- Keine persönlichen Daten in dieses Repo: keine echten Namen, Adressen, Fotos, Sheet-IDs, Bewerbungsstände oder konkreten Zielfirmen mit Status. Sie liegen im privaten Ordner `../bewerbungsassistent-daten/` (eigenes privates Repo) und werden per Pfad übergeben.
- Skills bleiben allgemein: personenbezogene Kriterien, Region, Keywords und Zielfirmen gehören ins Suchprofil, nicht in den Skill.
- Texte auf Deutsch, Schweizer Schreibweise (ss statt ß).
