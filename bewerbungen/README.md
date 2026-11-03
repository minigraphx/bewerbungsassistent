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
| Bewerbung | Angaben ändern (inkl. „beworben am“, „Absage am“), Stellentext, Vorschlag der Lebenslauf-Variante, KI-Unterstützung (Passung bewerten, Anschreiben entwerfen, Inhalt prüfen), Unterlagen erstellen, PDFs ansehen mit automatischer Prüfung, Versand erfassen, Angaben für den Job-Room (Arbeitsbemühungen) zum Kopieren – nur abgeleitet aus den Angaben, eine Absage ergibt immer „Absage“ |
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
  dokumente/                 Originale: zeugnisse/, zertifikate/, anschreiben-bisher/, lebenslauf-bisher/ (nicht in Git)
  .entwuerfe/                Entwürfe (nicht in Git)
  .ki/nutzung.jsonl          KI-Nutzung: Aufgabe, Modell, Tokens, Kosten, ersetzte Felder – nie Inhalte (nicht in Git)
```

`app.py` ergänzt die `.gitignore` des Datenordners um `.entwuerfe/`, `.build/`, `bewerbungen/*/*.pdf`, `dokumente/` und `.ki/`.

### Entwürfe und Versionen

- **Entwurf**: Jedes Speichern über die Oberfläche legt einen Entwurf mit Datum an (Inhalte nach SHA-256, jeder nur einmal). Änderungen ausserhalb der Oberfläche, etwa durch Claude im Chat, sichert `python entwurf.py <datenordner> <datei> -m "<was>"` (vorher und nachher aufrufen). Entwürfe sind löschbar, solange sie nicht genutzt wurden. Die Editoren (Inhalte, Foto) zeigen unter „Letzte Entwürfe“ die drei neuesten Entwürfe der gerade bearbeiteten Datei, mit Link auf alle.
- **Version**: Genutzt heisst versendet. Das PDF kommt einmal nach `versendet/`, die Daten, aus denen es entstand, bleiben als genutzte Entwürfe erhalten und sind nicht mehr löschbar. Das Register sagt, was wann an wen ging. Die Seite „Entwürfe & Versionen“ listet die Versionen daraus.
- **Git ist freiwillig**: Ohne Git fehlt nichts. Ist Git installiert, kommt jeder Versand zusätzlich als Commit ins lokale Git des Datenordners (nie automatisch gepusht); Fassungen aus der Zeit ohne Git werden beim nächsten Versand mitgenommen. Ein privates GitHub-Repo braucht es nicht.

### Varianten (`varianten.yaml`)

```yaml
- id: ki
  quelle: jobs/ki.yaml            # Zuschnitt, wird gebaut – oder datei: fertig.pdf – oder extern: "Canva, Google Drive"
  beschreibung: Software-Entwickler – KI-Anwendungen und Qualitätssicherung
  tags: [ki, test]                # Profil
  stichworte: [Python, LLM, RAG]  # Begriffe für den Abgleich mit dem Stellentext
```

Bei externen Varianten das PDF selbst als `bewerbungen/<id>/lebenslauf.pdf` ablegen.

### KI-Unterstützung (MIN-334, MIN-338)

Auf der Seite einer Bewerbung: **Passung bewerten** (Note 1–6 mit Begründung, übernehmbar), **Anschreiben entwerfen** (schreibt `anschreiben.yaml`, alter Stand bleibt als Entwurf) und **Inhalt prüfen** (Anforderungen abgedeckt / fehlt / überdehnt, unbelegte Aussagen). Grundlage sind `cv.yaml`, `suchprofil.md`, `anschreiben/stil.md`, `anschreiben/bausteine.md` und der gespeicherte Stellentext.

- **Pseudonymisierung**: Jede Anfrage läuft durch `ai/gateway.py`. Name, Kontaktdaten, Adresse, Geburtsdatum, Profile, Referenzen und Ansprechpersonen werden durch Platzhalter wie `{{NAME}}` ersetzt (auch in anderen Schreibweisen: Telefon mit +41, Links ohne https, Daten als 1. Mai 2011) und in der Antwort zurückgesetzt. E-Mail-Adressen, Telefonnummern und Personen nach „Frau“/„Herr“ im Inserat werden ebenfalls ersetzt; andere Namen im Inserat bitte unter „Kontaktperson“ eintragen. Bleibt danach eine E-Mail-Adresse, Telefonnummer oder ein bekannter Wert übrig, wird nichts gesendet. Bilder und Scans gehen nie an die KI.
- **Inserate sind Daten**: Zeilen, die sich an eine KI richten, befolgt sie nicht; die Oberfläche zeigt sie als „verdächtige Zeile“.
- **Verbindung**: im Pilot über die [Vermittlung](../vermittlung/README.md) (`BEWERBUNGSASSISTENT_KI_URL`). Die Person gibt einmal ihren Einladungscode ein; die App löst ihn ein und legt den Zugang im Schlüsselbund des Systems ab (oder `BEWERBUNGSASSISTENT_KI_ZUGANG`). Die Seite zeigt dann Verbrauch und Budget des Monats. Zum Entwickeln direkt mit `ANTHROPIC_API_KEY`. Ohne Verbindung bleiben die Knöpfe aus und die Seite sagt, was fehlt.
- **Kosten**: `.ki/nutzung.jsonl` hält pro Anfrage Modell, Tokens und Kosten fest; die Seite zeigt die Summe des Monats.

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
