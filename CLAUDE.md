# CLAUDE.md – Bewerbungsbegleiter

Die App heisst **Bewerbungsbegleiter**, auch technisch (seit 0.2.11, MIN-395). `bewerbungsassistent` bleibt nur, wo ein Wechsel mehr kostet als nützt: Repo, Dienst und Subdomain der Vermittlung, Datenformat und Browser-Speicher der Einstiegsvorlage, privater Datenordner. Dazu die `OLD_*`-Konstanten und `desktop/rename_migration.py`, die alte Installationen übernehmen. Tauchen sie nicht mehr auf, können sie weg.

Öffentliches Repo `minigraphx/bewerbungsassistent`. Werkzeuge und Skills für den Bewerbungsablauf: Stellensuche → Lebenslauf und Anschreiben pro Stelle → Prüfung → Versand. Geplant und verfolgt im Linear-Projekt "Bewerbungs-Assistent" (Team Minigraphx, Tickets ab MIN-255).

## Aufbau
- `lebenslauf/` – Lebenslauf und Anschreiben als PDF (eigene `CLAUDE.md` dort).
- `bewerbungen/` – lokale Oberfläche und Verwaltung: Register, Unterlagen, Prüfung, Versand, Entwürfe/Versionen (eigene `CLAUDE.md`). Baut auf `lebenslauf/` auf.
- `desktop/` – lokale App als Paket (MIN-342): Start, eine Instanz, Einladungslink, Updates aus GitHub Releases; PyInstaller und Inno Setup in `.github/workflows/app.yml`. Version in `desktop/version.py`, Release per Tag `v<Version>` (Entwurf, erst Veröffentlichen rollt aus). Mit `--mcp` lokaler MCP-Server für Claude mit dem eigenen Abo (MIN-377); `desktop/mcp_tools.py` ist die Grenze, was Claude erreicht.
- `erweiterung/` – Browser-Erweiterung (MIN-339), im Pilot als entpackte Entwicklererweiterung: Suche auf den Portalen nach dem Suchplan der App, Treffer per Native Messaging an `desktop/native_host.py`; füllt Bewerbungsformulare in Tabs, die die Person aus der App öffnet, offene Felder mit Hilfe der KI (MIN-346), abgeschickt wird nie durch das Tool. Trägt abgeschickte Bewerbungen im Job-Room ein (MIN-347): gespeichert wird nur durch die Person, die Daten gehen nie an die KI. Feste ID über den öffentlichen Schlüssel in `manifest.json`; der private Schlüssel gehört nie ins Repo. Tests: `node --test erweiterung/tests/*.test.mjs`. ZIP für die Stores: `desktop/store_package.py`; Bilder dafür in `docs/store/`, nur erfundene Daten.
- `vermittlung/` – KI-Vermittlung für den Pilot (MIN-344): Messages API mit Zugang pro Person, Budgets, Kostenprotokoll ohne Inhalte; eigener Container. Der Anthropic-Schlüssel nur als Geheimnis des Servers.
- `onboarding/` – Formular für die Grundlagen, gebaut aus `src/` und `form.json`: die Seite „Meine Angaben“ der App (`bewerbungen/seiten/angaben.html`, generiert) und die eigenständige Datei `dist/einstieg.html`, die weder öffentlich steht noch im App-Paket liegt. Dazu der Import nach `cv.yaml`, Suchprofil, Stil und Bausteine, auch für Dateien aus dem Skill `einstieg`. Nach Änderungen `build_template.py` laufen lassen; Prüfregeln in JS und Python über `tests/cases.json` gleich halten.
- Skills gibt es in der App als ZIP zum Hochladen; steht der Connector `bewerbungsbegleiter` bereit, arbeiten sie über dessen Werkzeuge statt über Repo und Datenordner (Abschnitt „Mit der App“).
- `skills/einstieg/SKILL.md` – Interview für den Einstieg: Lebenslauf, Suchprofil, Stilprofil, Bausteine; Zweige Stellen- und Lehrstellensuche.
- `skills/jobsuche/SKILL.md` – allgemeiner Skill für die Stellensuche; alles Persönliche steht im Suchprofil.
- `skills/bewerbung/SKILL.md` – Skill für den Ablauf Stelle → Unterlagen → Prüfung → Versand; Persönliches in Stilprofil und Bausteinen.
- `vorlagen/` – Vorlagen für persönliche Dateien, mit erfundenen Werten.
- `requirements.txt` – Python-Abhängigkeiten aller Module; venv unter `.venv/`.

## Regeln
- Nichts direkt auf `main`: Jede Änderung läuft über einen eigenen Branch und einen Pull Request, mit Ticket-ID in Commit und PR. Gemergt wird erst nach Andys Freigabe. `main` ist geschützt: Die Checks müssen grün und der Branch aktuell sein. Auch der Versions-Commit eines Releases läuft so; den Tag `v<Version>` setzt man danach auf den Merge-Stand.
- Keine persönlichen Daten in dieses Repo: keine echten Namen, Adressen, Fotos, Sheet-IDs, Bewerbungsstände oder konkreten Zielfirmen mit Status. Sie liegen im privaten Ordner `../bewerbungsassistent-daten/` (eigenes privates Repo) und werden per Pfad übergeben.
- Skills bleiben allgemein: personenbezogene Kriterien, Region, Keywords und Zielfirmen gehören ins Suchprofil, nicht in den Skill.
- Dokumentation und Texte für Nutzer (Oberfläche, Fehlermeldungen) auf Deutsch, Schweizer Schreibweise (ss statt ß).
- Code auf Englisch: Bezeichner, Docstrings, Kommentare und Testnamen. Gilt für neuen Code; bestehende deutsche Bezeichner werden nur in einem eigenen Refactoring umbenannt.
- Dateien im Datenordner vor und nach jeder Änderung mit `bewerbungen/entwurf.py <datenordner> <datei> -m "<was>"` als Entwurf sichern; committet wird dort erst beim Versand.
