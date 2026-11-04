# CLAUDE.md – Bewerbungsassistent

Öffentliches Repo `minigraphx/bewerbungsassistent`. Werkzeuge und Skills für den Bewerbungsablauf: Stellensuche → Lebenslauf und Anschreiben pro Stelle → Prüfung → Versand. Geplant und verfolgt im Linear-Projekt "Bewerbungs-Assistent" (Team Minigraphx, Tickets ab MIN-255).

## Aufbau
- `lebenslauf/` – Lebenslauf und Anschreiben als PDF (eigene `CLAUDE.md` dort).
- `bewerbungen/` – lokale Oberfläche und Verwaltung: Register, Unterlagen, Prüfung, Versand, Entwürfe/Versionen (eigene `CLAUDE.md`). Baut auf `lebenslauf/` auf.
- `desktop/` – lokale App als Paket (MIN-342): Start, eine Instanz, Einladungslink, Updates aus GitHub Releases; PyInstaller und Inno Setup in `.github/workflows/app.yml`. Version in `desktop/version.py`, Release per Tag `v<Version>` (Entwurf, erst Veröffentlichen rollt aus).
- `erweiterung/` – Browser-Erweiterung (MIN-339), im Pilot als entpackte Entwicklererweiterung: Suche auf den Portalen nach dem Suchplan der App, Treffer per Native Messaging an `desktop/native_host.py`; füllt Bewerbungsformulare in Tabs, die die Person aus der App öffnet (MIN-346), abgeschickt wird nie durch das Tool. Feste ID über den öffentlichen Schlüssel in `manifest.json`; der private Schlüssel gehört nie ins Repo. Tests: `node --test erweiterung/tests/*.test.mjs`. ZIP für die Stores: `desktop/store_package.py`; Bilder dafür in `docs/store/`, nur erfundene Daten.
- `vermittlung/` – KI-Vermittlung für den Pilot (MIN-344): Messages API mit Zugang pro Person, Budgets, Kostenprotokoll ohne Inhalte; eigener Container. Der Anthropic-Schlüssel nur als Geheimnis des Servers.
- `onboarding/` – Einstiegsvorlage: eine HTML-Datei (`dist/einstieg.html`, gebaut aus `src/` und `form.json`) und Import nach `cv.yaml`, Suchprofil, Stil und Bausteine. Dieselben Quellen ergeben die Seite „Meine Angaben“ der App (`bewerbungen/seiten/angaben.html`, generiert). Nach Änderungen `build_template.py` laufen lassen; Prüfregeln in JS und Python über `tests/cases.json` gleich halten.
- `skills/einstieg/SKILL.md` – Interview für den Einstieg: Lebenslauf, Suchprofil, Stilprofil, Bausteine; Zweige Stellen- und Lehrstellensuche.
- `skills/jobsuche/SKILL.md` – allgemeiner Skill für die Stellensuche; alles Persönliche steht im Suchprofil.
- `skills/bewerbung/SKILL.md` – Skill für den Ablauf Stelle → Unterlagen → Prüfung → Versand; Persönliches in Stilprofil und Bausteinen.
- `vorlagen/` – Vorlagen für persönliche Dateien, mit erfundenen Werten.
- `requirements.txt` – Python-Abhängigkeiten aller Module; venv unter `.venv/`.

## Regeln
- Keine persönlichen Daten in dieses Repo: keine echten Namen, Adressen, Fotos, Sheet-IDs, Bewerbungsstände oder konkreten Zielfirmen mit Status. Sie liegen im privaten Ordner `../bewerbungsassistent-daten/` (eigenes privates Repo) und werden per Pfad übergeben.
- Skills bleiben allgemein: personenbezogene Kriterien, Region, Keywords und Zielfirmen gehören ins Suchprofil, nicht in den Skill.
- Dokumentation und Texte für Nutzer (Oberfläche, Fehlermeldungen) auf Deutsch, Schweizer Schreibweise (ss statt ß).
- Code auf Englisch: Bezeichner, Docstrings, Kommentare und Testnamen. Gilt für neuen Code; bestehende deutsche Bezeichner werden nur in einem eigenen Refactoring umbenannt.
- Dateien im Datenordner vor und nach jeder Änderung mit `bewerbungen/entwurf.py <datenordner> <datei> -m "<was>"` als Entwurf sichern; committet wird dort erst beim Versand.
