# Bewerbungen

Modul des [Bewerbungsassistenten](../README.md): Bewerbungen verwalten, Unterlagen erstellen und prüfen, Versand festhalten. Mit lokaler Oberfläche im Browser.

```bash
pip install -r ../requirements.txt
python app.py ../../meine-daten
```

Die Oberfläche läuft nur auf `127.0.0.1` und öffnet sich im Browser:

| Seite | Inhalt |
|---|---|
| Bewerbungen | Alle Bewerbungen mit Status und Daten, Suche, neue Bewerbung anlegen; Spalten per Klick auf die Überschrift sortierbar (Sortierung, Suche, Filter und Scrollposition bleiben beim Seitenwechsel erhalten), mit Passung (Note 1–6), Datum der Erfassung und Link zum Inserat |
| Bewerbung | Angaben ändern (inkl. „beworben am“, „Absage am“), Stellentext, Vorschlag der Lebenslauf-Variante, Unterlagen erstellen, PDFs ansehen mit automatischer Prüfung, Versand erfassen, Angaben für den Job-Room (Arbeitsbemühungen) zum Kopieren |
| Inhalte | Lebenslauf, Zuschnitte, Anschreiben, Stilprofil, Bausteine und Suchprofil als PDF ansehen; hinter „Als Text“ bearbeiten (auch Varianten und Register), mit Prüfung und Vorschau; gespeichert wird nur Gültiges (mit Entwurf) |
| Entwürfe & Versionen | Jeder gespeicherte Stand mit Datum: ansehen, vergleichen, wiederherstellen, löschen (solange nicht genutzt); versendete Versionen aus Git |
| Foto | Fotoausschnitt per Maus einstellen (spiegeln, zoomen, verschieben), Vorschau wie im PDF |

## Ablauf

1. **Stelle wählen** – in der Übersicht oder per Skill `jobsuche`; Status „Bewerben“.
2. **Lebenslauf** – bestehende Variante wiederverwenden oder neue erstellen (`varianten.yaml`, Tags zum Wiederfinden).
3. **Anschreiben** – `bewerbungen/<id>/anschreiben.yaml`, Entwurf durch den Skill `bewerbung` aus Bausteinen und Stilprofil.
4. **Prüfung** – „Unterlagen erstellen“, PDFs ansehen; formale Prüfung automatisch, inhaltliche durch den Skill.
5. **Versand** – von Hand abschicken, dann „Versand erfassen“: Fassung nach `versendet/` (jede nur einmal), Entwürfe als genutzt markiert, alles in Git eingefroren.
6. **Bewerbungsdaten** – Status, Gespräch, Absage nachtragen; Job-Room-Angaben übernehmen.

## Datenordner

```
meine-daten/
  cv.yaml, foto.jpg          Stammdaten (Modul lebenslauf)
  jobs/<name>.yaml           Zuschnitte des Lebenslaufs
  varianten.yaml             Lebenslauf-Varianten mit Tags (MIN-307)
  bewerbungen.yaml           Register aller Bewerbungen (MIN-306)
  bewerbungen/<id>/          anschreiben.yaml, stelle.md, erstellte PDFs (nicht in Git)
  versendet/                 versendete Fassungen, jede nur einmal (in Git)
  anschreiben/               bausteine.md, stil.md (persönlich)
  .entwuerfe/                Entwürfe (nicht in Git)
```

`app.py` ergänzt die `.gitignore` des Datenordners um `.entwuerfe/`, `.build/` und `bewerbungen/*/*.pdf`.

### Entwürfe und Versionen

- **Entwurf**: Jedes Speichern über die Oberfläche legt einen Entwurf mit Datum an (Inhalte nach SHA-256, jeder nur einmal). Änderungen ausserhalb der Oberfläche, etwa durch Claude im Chat, sichert `python entwurf.py <datenordner> <datei> -m "<was>"` (vorher und nachher aufrufen). Entwürfe sind löschbar, solange sie nicht genutzt wurden.
- **Version**: Genutzt heisst versendet. Beim Versand werden PDFs und Quelldaten im lokalen Git des Datenordners committet (nie automatisch gepusht).
- **Ohne Git**: Der Versand funktioniert trotzdem; die Fassungen bleiben unter `versendet/` und im Register und werden beim ersten Versand mit Git nachträglich eingefroren.

### Varianten (`varianten.yaml`)

```yaml
- id: ki
  quelle: jobs/ki.yaml            # Zuschnitt, wird gebaut – oder datei: fertig.pdf – oder extern: "Canva, Google Drive"
  beschreibung: Software-Entwickler – KI-Anwendungen und Qualitätssicherung
  tags: [ki, test]                # Profil
  stichworte: [Python, LLM, RAG]  # Begriffe für den Abgleich mit dem Stellentext
```

Bei externen Varianten das PDF selbst als `bewerbungen/<id>/lebenslauf.pdf` ablegen.

## Kommandozeile

```bash
python register.py importiere jobliste.csv ../../meine-daten     # CSV-Export der Google-Sheet-Jobliste übernehmen
python register.py exportiere ../../meine-daten > jobliste.csv   # zurück ins Format der Jobliste
python varianten.py vorschlag ../../meine-daten --stelle ../../meine-daten/bewerbungen/<id>/stelle.md
python varianten.py liste ../../meine-daten --tag ki
```

## Tests

```bash
pip install -r ../requirements-dev.txt
python -m pytest
```
