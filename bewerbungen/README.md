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

### Sicherung (MIN-359)

Im Menü steht **„Sicherung erstellen“**. Der Browser fragt, wo die Datei `bewerbungsassistent-sicherung-<Datum>.zip` hin soll, zum Beispiel auf einen USB-Stick. Die App lädt nichts irgendwohin hoch. Browser ohne diese Frage (Firefox, Safari) laden die Datei herunter; dann bestätigt die Person, dass sie gespeichert ist.

- **Inhalt:** alle Daten mit `.entwuerfe/`, `versendet/`, `dokumente/` und `.ki/`, ohne `.build/` (lässt sich neu erstellen), ohne frühere Sicherungen im Datenordner und ohne `.git/`. Symlinks kommen nicht mit.
- **Erinnerung:** In der Übersicht erscheint ein ruhiger Hinweis nach 5 versendeten Bewerbungen oder nach 30 Tagen ohne Sicherung. Das Datum der letzten Sicherung steht in `.sicherung.yaml`. Als Sicherung zählt erst, was der Browser fertig gespeichert hat oder was die Person nach dem Download bestätigt.
- **Wiederherstellen:** Die ZIP-Datei entpacken und den Ordner in der App unter „Einrichtung“ wählen. Register, Entwürfe und Versionen sind wieder da. Die Git-Geschichte kommt nicht mit; wer sie braucht, sichert `.git/` selbst.

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

Auf der Seite **Treffer** bewertet die KI in Paketen von zehn Inseraten pro Anfrage (MIN-372):

- **Knöpfe nach Anzahl:** bis 10 offene „Bewerten (N)“, darüber „Nächste 10 bewerten“ und „Alle bewerten (N)“, über 30 „Nächste 30 bewerten“. Ein Lauf lässt sich anhalten, Bewertetes bleibt.
- **Automatik:** Nach einer Suche bei offener Seite werden höchstens 30 neue Treffer von selbst bewertet; abschaltbar auf der Seite (`suche/einstellungen.yaml`).
- **Unsichere Noten:** Eine Antwort, die ein Inserat auslässt oder unbrauchbar ist, trifft nur dieses Inserat: Es wird einzeln nochmals versucht. Ist ein Inserat so knapp, dass die Note wenig sagt, steht ein „?“ daneben und in den Details der Grund.
- **Lehrstellen:** Die Note hat einen eigenen Massstab, in den Details stehen Beruf- und Lehrstellennote. Die Person gibt ihren Berufen 1 bis 5 Sterne; sie sortieren zuerst, ändern die Note nicht und gehen nicht an die KI.
- **Schnupperlehren (MIN-373):** Auf der Seite „Treffer“ wählt die Person Lehrstellen, Schnupperlehren oder beides; die Wahl steht im Suchprofil unter „Gesucht“. Eine Schnupperlehre ist ein eigener Treffer, auch beim selben Betrieb wie eine Lehrstelle, und lässt sich in der Liste filtern. Ins Register kommt sie als „Schnupperlehre <Beruf>“ mit `art: Schnupperlehre`; der KI-Entwurf schreibt dann eine kurze Anfrage statt eines Motivationsschreibens.

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
