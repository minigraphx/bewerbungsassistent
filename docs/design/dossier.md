# Dossier: drei Entwürfe

Stand 10.11.2026, von Andy am selben Tag freigegeben: alle drei Entwürfe „Siegel“, „Raster“ und „Register“, ihre Niveaugrafiken und die Icons. Die Entwürfe liegen als Canvas unter https://claude.ai/artifact/7E4L7uKhqSdXHAJCMcaRcT, mit den Niveaugrafiken der drei Entwürfe in den Fällen keine, teilweise und alle erfasst. Alle Personen, Firmen und Texte darin sind erfunden, das Foto ist eine neutrale Platzhalterform. Baut auf `docs/design/system/` auf; Texte in Schweizer Schreibweise.

Umgesetzt in G16 und G39 bis G42: Grundlagen und „Siegel“ #109, „Raster“ #201, „Register“ #202, Wahl von Dossier oder Anschreiben und Lebenslauf pro Bewerbung #203, Wahl des Entwurfs pro Seite #204.

## Entscheide (10.11.2026)

- Gebaut werden alle drei Entwürfe, zuerst die Grundlagen mit „Siegel“, dann „Raster“ und „Register“.
- Alle Niveaus nutzen die Skala 1 bis 6, passend zum Notenbalken des Systems und zu den Sprachstufen A1 bis C2.
- Interessen in „Siegel“ und „Raster“ zeigen Linien-Icons aus Lucide (ISC-Lizenz), immer mit dem Wort, mit Lizenztext in `themes/icons/`. Es ist die erste Symbolsammlung im Projekt. „Register“ bleibt ohne Icons.

## Grundsätze

- **Eine Schrift:** DM Sans in 400, 400 kursiv, 500 und 700 (SIL Open Font License 1.1, liegt schon in `lebenslauf/fonts/`). Daten und Dauer stehen in DM Sans mit tabellarischen Ziffern statt in einer Monospace.
- **Eine Akzentfarbe:** Standard ist Schieferblau `#38495d` (`accent`), als Parameter. Dazu kommen nur die Farben des Systems: `text-strong`, `text`, `text-muted`, `accent-subtle`, `surface-subtle`, `line` und `line-strong`. Das Papier ist `bg` `#fdfcfa`, wie im Theme „zweispaltig“.
- **Abstände und Radien aus den Tokens:** Abstände 4, 8, 12, 16, 24, 32 und 48 pt; Ränder der Seite 48 pt (`space-7`). Radien 6 (`radius-md`) für Fotos und Felder, 10 (`radius-lg`) für Karten und Bänder; voll rund nur für Punkte und Statusmarken.
- **Motive des Systems statt eigener Ornamente:**
  - Schrittpunkt und Schrittweg aus dem Cover.
  - Bänder des Covers, oben angeschnitten.
  - Notenbalken aus sechs Feldern.
  - Punkt der Statusmarke.
- **Ruhig:** Etiketten ohne Grossbuchstaben und ohne Sperrung, keine Kapitälchen, keine Sterne, keine Schmuckzeichen. Wörter tragen die Bedeutung.
- **Skala der Niveaus 1 bis 6.** Sie passt zum Notenbalken des Systems und zu den Sprachstufen A1 bis C2.

## Gemeinsame Grundlagen

### Teile und Dateien

| Ausgabe | Inhalt |
|---|---|
| Dossier (eine PDF) | Deckblatt, optionale Seite davor, Anschreiben, Lebenslauf, optionale Seite danach |
| Lebenslauf einzeln | nur der Lebenslauf; das Erkennungszeichen wandert in den Kopf von Seite 1 |
| Anschreiben einzeln | nur der Brief; das Erkennungszeichen steht im Briefkopf |

Die Teile sind in Typst dieselben Funktionen. Das Dossier ruft sie nur hintereinander auf.

### Datenerweiterungen (für alle Entwürfe gleich)

| Feld | Zweck |
|---|---|
| `skills[].keywords[]` als Text **oder** `{name, level}` | Niveau je Kenntnis oder Programm |
| `languages[].x-level` | Niveau 1–6, auch als Stufe A1–C2 erfassbar; `fluency` bleibt als Text und wird immer gedruckt |
| `interests[].x-icon` | nur Entwürfe A und B: Name aus einem festen, kleinen Katalog; fehlt er, steht nur das Wort |
| `basics.x-monogramm` | eigene Initialen für das Zeichen (1–3 Buchstaben); sonst aus dem Namen |
| Anschreiben: `firma`, `stelle`, `pensum`, `referenz` | für die Überschrift; fehlen sie, gelten die erste Zeile von `empfaenger` und der `betreff` |
| Dossier-Datei: `gruss`, `dank`, `kennzahlen`, `anlagen` | Inhalte der optionalen Seiten; was fehlt, entfällt als Seite |

**Regel für Niveaus**:
- **Keine erfasst:** keine Grafik; die Gruppe sieht aus wie heute.
- **Teilweise erfasst:** Hat ein Eintrag einer Gruppe ein Niveau, zeigen alle Einträge der Gruppe die Grafik. Wer keines hat, bekommt die gestrichelte leere Form, wie der unsichere Notenbalken im System. Sie liest sich als „ohne Angabe“, nicht als „keine Kenntnis“.
- **Alle erfasst:** Jeder Eintrag zeigt sein Niveau.

### Akzentfarbe

Die Akzentfarbe ist der Parameter `stil.farbe-akzent`, Standard `#38495d`. Die Entwürfe setzen ihn als `--d-accent: var(--accent)`. Weitere Grundsätze:
- Text auf Akzentflächen folgt `on-accent`. Bei einer anderen Wunschfarbe berechnet das Theme Weiss oder `text-strong` nach Kontrast, nie fest weiss.
- Als Textfarbe dient die Akzentfarbe nur bei mindestens 4.5:1 auf dem Papier.
- `accent-subtle` wird aus der Akzentfarbe abgeleitet (`color.mix` mit Weiss).

### Icons

Das System hat noch keine Symbolsammlung, und Bedeutung tragen Wörter. Darum gilt:
- **A und B** zeigen Interessen mit einem kleinen Linien-Icon. Das Icon steht immer über dem Wort, nie allein. Der Satz ist Lucide (ISC-Lizenz), mit Lizenztext in `themes/icons/`; die erste Symbolsammlung im Projekt (Entscheid 10.11.2026).
- **C** kommt ganz ohne Icons aus; die Interessen sind eine Wortliste.

### Lesbarkeit für Bewerbungssoftware (ATS)

- Aller Inhalt ist echter Text, auch Name und Kontakt auf dem Deckblatt. Grafik sind nur Bänder, Punkte, Linien, Niveaugrafiken und Icons.
- Die Reihenfolge im Typst-Quelltext ist die Lesereihenfolge: pro Station zuerst Zeitraum, dann Titel, Firma und Stichpunkte.
- Abschnittstitel als echte Überschriften (`heading`). Daraus entstehen Lesezeichen und mit Typst 0.14 eine getaggte Struktur. `requirements.txt` sollte dafür auf `typst>=0.14` steigen.
- Für Portale, die den Lebenslauf auslesen, ist die Einzeldatei gedacht.
- Prüfung wie in `lebenslauf/CLAUDE.md`: bauen, `pdftotext` lesen, Reihenfolge per Test festhalten.

### Aufbau in Typst

- **Ordnerstruktur:** `themes/dossier-<name>/` mit `theme.typ`, `anschreiben.typ`, `teile.typ` (Deckblatt, optionale Seiten) und den Einstiegen `main.typ`, `anschreiben-main.typ`, `dossier-main.typ`.
- **Werte aus den Tokens:** Eine kleine Datei `themes/tokens.typ` übernimmt Farben, Abstände und Radien aus den Tokens des Design-Systems. So bleiben Theme und App gleich.
- **Seitenstil getrennt:** Heute setzen `lebenslauf()` und `brief()` selbst `set document` und `set page`. Fürs Dossier setzt eine Hülle die Metadaten, die Teile setzen nur ihren Seitenstil (`page(..)[..]`).
- **Betreff im Brief:** `brief.typ` bekommt einen optionalen Baustein `betreff-block` für die starke Überschrift.
- **Einstieg:** `dossier.py`, oder `build.py --dossier <datei>`, legt Lebenslauf, Anschreiben und Dossier-Datei in ein gemeinsames JSON.
- **Foto:** `foto-rund` wird zu `foto-form(pfad, breite, hoehe, radius, optionen)` verallgemeinert. So gilt der Ausschnitt aus `x-image` auch für eckige Fotos.
- **Schriften:** keine neue Schrift; DM Sans liegt schon bei.

---

## Entwurf A: „Siegel“

**Konzept.** Ruhig und persönlich: viel Weissraum, eine Spalte, warme Seiten vorne und hinten. Das Zeichen ist der Schrittpunkt des Systems, ein Ring mit den Initialen, an dem der Weg der bisherigen Stationen ankommt. Sinngemäss: „Diese Bewerbung ist der nächste Schritt.“

**Seitenfolge im Dossier**
1. Deckblatt: ein waagrechter Schrittweg über die Seite. Vier gefüllte Punkte stehen für die bisherigen Stationen und werden aus den Daten gezählt. Dann folgt der Ring mit den Initialen, danach offene Punkte. Darunter stehen Name, Bezeichnung und „Bewerbung als …“ mit Stelle und Firma. Unten ein Band in Akzentfarbe mit Kontakt, unten angeschnitten mit `radius-lg`.
2. *Optional* „Kurz vorgestellt“: rundes Foto und eine Karte auf `surface-subtle` mit drei Sätzen Gruss, unterschrieben in DM Sans kursiv.
3. Anschreiben.
4. Lebenslauf, zwei Seiten.
5. *Optional* „Danke“: ein Satz Dank, der Ring, Kontakt und ein schmales Band unten.

**Typografie.** Nur DM Sans. Name 34 pt 700, Stelle im Brief 28 pt 700, Abschnitte 12 pt 700, Text 9.5–10 pt, Nebentext in `text-muted`.

**Farbe.** Akzent für Ring, Schrittweg, Punkte und das Band. Die Karte der Grussseite ist auf `surface-subtle`, keine zweite Akzentfläche.

**Erkennungszeichen.** Der Schrittpunkt „jetzt“ aus dem System: ein Ring in Akzentfarbe auf `surface` mit den Initialen in `text-strong` 700. Er steht gross auf dem Deckblatt, klein im Fuss jeder Seite und im Kopf der Einzeldateien.

**Niveaus.** Ein kleiner Weg aus sechs Punkten: gefüllt bis zum Niveau, die übrigen hohl in `line-strong`. Ohne Angabe sind Punkte und Linie gestrichelt.

**Zeitleiste.** Die senkrechte Schrittanzeige (`steps--vertical`). Links steht der Zeitraum, in der Mitte ein Punkt pro Station: der Ring für Laufendes, gefüllt für Abgeschlossenes, verbunden durch eine Linie. Rechts stehen die Stationen.

**Interessen.** Linien-Icons in Akzentfarbe, das Wort darunter.

**Einzeldateien.** Der Lebenslauf allein hat den Ring links neben dem Namen. Das Anschreiben allein hat einen Briefkopf mit Ring, Name und Bezeichnung. Grussseite und Dank gibt es nur im Dossier.

**ATS.** Einspaltig; der Zeitraum steht im Quelltext vor seiner Station. Der Ring ist eine Zeichnung, der Name steht trotzdem auf jeder ersten Seite als Text.

**Machbarkeit in Typst.** Gut machbar und nah am Bestehenden.
- Ring und Weg: `circle` und `line`.
- Zeitleiste: `grid` mit drei Spalten, die Linie als Rand der Mittelspalte.
- Niveaus: sechs `circle` in einem `box`.
- Unteilbare Einträge mit „(Fortsetzung)“ über das bestehende `eintraege()`.

**Risiko.** Der Schrittweg auf dem Deckblatt zählt Stationen. Bei sehr langen Laufbahnen braucht er eine Obergrenze, zum Beispiel höchstens sechs Punkte.

---

## Entwurf B: „Raster“

**Konzept.** Plakativ und datenhaft. Die Bänder des Design-System-Covers tragen das Dossier:
- oben auf dem Deckblatt, mit den Initialen;
- als Briefkopf mit dem Firmennamen;
- unten auf der Rückseite, wie ein Umschlag.

Die Laufbahn erscheint als Zeitachse, Kennzahlen sind gross gesetzt.

**Seitenfolge im Dossier**
1. Deckblatt: oben die drei Bänder des Covers mit Radius 10, oben angeschnitten. Links das Akzentband mit den Initialen in 96 pt 700 und drei ausgestanzten Punkten. In der Mitte ein schmales Band in `text-strong`, rechts ein Band in `accent-subtle` mit dem Schrittweg. Darunter Name, Bezeichnung, Foto (Radius 10) und Angaben in Zeilen: Stelle, Unternehmen, Inhalt, Datum.
2. *Optional* „Auf einen Blick“: drei Kennzahlen in 64 pt 700 (`text-strong`, tabellarische Ziffern), von der Person selbst eingetragen, dazu drei Stärken.
3. Anschreiben: Das Akzentband mit dem Firmennamen in 26 pt 700 und „Bewerbung als …“ ist der Briefkopf. Absender, Datum und Referenz stehen in einer Randspalte.
4. Lebenslauf, zwei Seiten.
5. *Optional* Rückseite: die Bänder unten angeschnitten, darüber Kontakt und „Danke für Ihre Zeit.“

**Typografie.** Nur DM Sans, Hierarchie über Grösse und Gewicht: Initialen 96 pt, Name 38 pt, Kennzahlen 64 pt.

**Farbe.** Je Seite eine Akzentfläche, das Band; dazu `text-strong` und `accent-subtle` als Nachbarbänder wie im Cover. In der Zeitachse sind laufende Stationen akzentfarbig, abgeschlossene in `line`.

**Erkennungszeichen.** Das Bänderband mit den Initialen im Akzentfeld. Auf Folgeseiten ist es eine schmale, oben angeschnittene Leiste aus denselben drei Bändern.

**Niveaus.** Der Notenbalken des Systems aus sechs Feldern: gefüllt in Akzentfarbe, leer in `line`. Ohne Angabe sind die Felder gestrichelt, wie bei einer unsicheren Note.

**Zeitleiste.** Waagrechte Achse vom ersten Jahr bis heute. Jede Station ist ein Balken mit Radius 4, proportional zur Dauer, und trägt nur eine Nummer. Dieselbe Nummer steht in der Randspalte vor jeder Station, mit Zeitraum.

**Interessen.** Icons in `text-strong` auf Feldern in `accent-subtle` (Radius 6), das Wort darunter.

**Einzeldateien.** Der Lebenslauf allein beginnt mit einem höheren Band, darin Name und Bezeichnung in `on-accent`, das Foto im hellen Band. Das Anschreiben allein bleibt gleich, denn das Band ist schon der Briefkopf. „Auf einen Blick“ und die Rückseite gibt es nur im Dossier.

**ATS.** Pro Station kommt im Quelltext zuerst die Randspalte (Nummer, Zeitraum), dann der Inhalt. Die Zeitachse enthält nur Jahreszahlen und Nummern, keine Firmennamen; für sehr strenge Software lässt sie sich abschalten (`stil.zeitachse: false`).

**Machbarkeit in Typst.** Machbar, mit etwas mehr eigener Logik.
- Bänder: `place` mit negativem Versatz und `rect(radius: 10pt)`.
- Ausgestanzte Punkte: `circle` in Papierfarbe.
- Zeitachse: Monate aus den Daten, Balkenbreite im Verhältnis zur Gesamtdauer; über 15 Jahre ein Feld „früher“.
- Notenbalken: sechs `rect`.

**Risiko.** Die Bänder sind das Auffälligste im System. Im Dossier müssen sie sparsam bleiben, je Seite höchstens eines. Die Zeitachse braucht Regeln für überlappende Stationen.

---

## Entwurf C: „Register“

**Konzept.** Geordnet wie eine Akte:
- Reiter je Teil am rechten Rand;
- das Deckblatt ist zugleich Inhaltsverzeichnis;
- am Ende die Beilagen.

Das Zeichen ist ein Anhänger mit dem Punkt der Statusmarke. Niveaus stehen als Statusmarken mit Wort. Keine Icons: Wörter tragen die Bedeutung, ganz wie das System es will. Er passt zur Schweizer Gewohnheit eines Dossiers mit Inhalt und Beilagen und zu Lehrstellen mit vielen Zeugnissen.

**Seitenfolge im Dossier**
1. Deckblatt mit Inhalt: Anhänger, Passfoto (Radius 6) und „Bewerbung“ mit Stelle und Firma. Das Inhaltsverzeichnis ist eine Karte mit Tabelle (Radius 10, Linien `line`) mit Teil, Inhalt und Seite, die Beilagen eingerückt. Am Rand alle Reiter in `accent-subtle`.
2. Anschreiben (Reiter 1 in Akzentfarbe): Kasten auf `surface-subtle` mit Stelle (20 pt 700), Pensum, Unternehmen und Referenz.
3. Lebenslauf, zwei Seiten (Reiter 2).
4. *Optional* Beilagen (Reiter 3): Tabelle mit Nummer, Dokument, Datum und Seite. Die App kennt die Beilagen ohnehin.
5. *Optional* Referenzen: nur wenn `references` erfasst ist; sonst steht im Lebenslauf „Auf Anfrage.“

**Typografie.** Nur DM Sans. Tabellen wie im System: Spaltenköpfe 500 in `text-muted`, ohne Grossbuchstaben, Zahlen tabellarisch.

**Farbe.**
- Der Reiter des aktuellen Teils ist in Akzentfarbe, die anderen in `accent-subtle`.
- Der Punkt im Anhänger und die Statusmarken der hohen Niveaus sind akzentfarbig.
- Kästen und Karten liegen auf `surface-subtle` oder `surface` mit Rand `line`.

**Erkennungszeichen.** Ein Anhänger: Karte mit Rand `line-strong` und Radius 10. Statt eines Lochs trägt er den gefüllten Punkt der Statusmarke („jetzt dran“), dazu Initialen 28 pt 700, Name und „Dossier · 11.2026“. Im Kopf von Brief und Einzeldateien erscheint er klein.

**Niveaus.** Statusmarken mit Wort, deren Füllung mit dem Niveau steigt:
- 1–2: Rand und hohler Punkt.
- 3–4: Fläche `accent-subtle`.
- 5–6: Fläche Akzent mit `on-accent`.
- Ohne Angabe: gestrichelt mit dem Text „ohne Angabe“.

Wörter für die Stufen 1 bis 6: Einstieg, Grundlagen, solide, gut, sehr gut, Expertise. Bei Sprachen steht die Stufe mit Text, zum Beispiel „C1 · fliessend“.

**Zeitleiste.** Eine Tabelle pro Abschnitt mit Zeitraum, Dauer und Station. Die Dauer („7 J. 8 M.“) wird aus den Daten berechnet und gibt den schnellen Überblick ohne Grafik.

**Interessen.** Als Wortliste.

**Einzeldateien.** Der Lebenslauf allein trägt den kleinen Anhänger über dem Namen und behält seinen Reiter. Das Anschreiben ebenso, ohne Deckblatt und Inhaltsverzeichnis. Auf Wunsch fallen die Reiter in Einzeldateien weg (`stil.reiter: false`).

**ATS.** Am besten von allen dreien:
- Die Niveaus sind Wörter, kein Bild.
- Zeitraum und Dauer sind Text in Tabellenzellen.
- Das Inhaltsverzeichnis ist Text.

Nur die gedrehten Reiterbeschriftungen könnten als Fremdtext gelesen werden. Sie stehen im Seitenhintergrund und werden mit Typst 0.14 als Artefakt markiert (`pdf.artifact`); sonst bleiben sie in Einzeldateien ohne Schrift.

**Machbarkeit in Typst.** Gut machbar.
- Reiter: in `set page(background: ..)` je Teil, mit `rotate(-90deg)`, 12 pt über den Rand hinaus. Die Beschriftung bleibt mindestens 5 mm innerhalb.
- Inhaltsverzeichnis: `query` auf Marken der Teile mit `location().page()`.
- Dauer: Stichtag `stand` aus `build.py`.
- Statusmarken: `box(radius: 999pt)` mit Punkt und Wort.

**Risiko.** Viele gefüllte Marken nebeneinander werden dunkel und schwer. Darum füllt erst Stufe 5 ganz; bei langen Listen wäre die Fläche erst ab Stufe 6 eine Alternative.

---

## Vergleich

| | A „Siegel“ | B „Raster“ | C „Register“ |
|---|---|---|---|
| Wirkung | persönlich, ruhig | plakativ, datenhaft | geordnet, sachlich |
| Motiv des Systems | Schrittpunkt und Schrittweg | Bänder des Covers, Notenbalken | Tabelle, Statusmarke |
| Erkennungszeichen | Ring mit Initialen | Bänder mit Initialen | Anhänger mit Statuspunkt |
| Niveaus | Weg aus sechs Punkten | Notenbalken aus sechs Feldern | Statusmarke mit Wort |
| Zeitleiste | senkrechte Schrittanzeige | waagrechte Achse, nummeriert | Tabelle mit Dauer |
| Icons | ja, mit Wort | ja, mit Wort | keine |
| Optionale Seiten | „Kurz vorgestellt“, „Danke“ | „Auf einen Blick“, Rückseite | Beilagen, Referenzen |
| ATS | sehr gut | gut, Zeitachse abschaltbar | sehr gut, Reiter prüfen |
| Aufwand in Typst | klein bis mittel | mittel | mittel |
