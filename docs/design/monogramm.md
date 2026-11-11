# Monogramm und Logo im Dossier: Gestaltung

Stand 11.11.2026. **Entschieden: Option B, «Zeichen und Farbe» unter «Erweitert».** Gehört zum Board-Item #124 und zur Spec-Zeile G18. Berührt G16, G39, G41 und G42. Baut auf `docs/design/system/`, `docs/design/dossier.md` und `docs/design/texte.md` auf; neue Klassen englisch, Texte in Schweizer Schreibweise.

Die Zeichenflächen liegen in Claude Design, mit dem Designsystem Bewerbungsassistent: «Zeichen» (Varianten, Logo und Farben), «Erweitert» (die gewählte Option B) sowie «Direkt» und «Eigene Seite» (A und C, nicht gewählt).

**Umgesetzt** (#124): Regeln in `lebenslauf/mark.py`, Zeichen in `lebenslauf/themes/zeichen.typ`, aufgerufen von allen drei Designs; Speichern in `bewerbungen/mark_settings.py`, `bewerbungen/logo_file.py` und `bewerbungen/routes_mark.py`; Seite in `bewerbungen/seiten/zeichen.js` und `zeichen-logik.js`. Abweichungen und Wahl bei der Umsetzung stehen unten unter «Umsetzung».

Person, Initialen, Logos, Firma und Adresse sind erfunden (Lea Brunner, LB, Muster AG).

## Frage

G18: «Im Dossier wählt die Person das Monogramm aus mehreren Varianten aus ihren Initialen oder lädt ein eigenes Logo hoch, und sie wählt die Akzentfarbe; voreingestellt ist eine Akzentfarbe passend zur Hauptfarbe des Designs.»

## Entscheide (10.11.2026)

| Frage | Entscheid |
|---|---|
| Wo wählt die Person? | **B:** unter «Erweitert» in der Karte «Unterlagen prüfen», mit einem Satz unter dem Design, was gilt |
| Pro Person oder pro Bewerbung? | Pro Person: «Gilt für alle Dossiers» |
| Hauptfarbe pro Design | Ja, jedes Design hat seine eigene. «Passend zum Design» heisst: diese Farbe. |
| Zeichen in Raster im Fuss | Ja, klein auf den Folgeseiten, vor dem Namen |
| Varianten | Alle fünf: Ring, Block, Verschränkt, Linie, Punkt |
| Feld «Initialen» | Unter «Erweitert», im Abschnitt «Zeichen und Farbe» |
| «Aus dem Logo» | Ja, als Angebot bei den Farben; nie von selbst gewählt |

## Kurz

- **Zeichen:** Es gibt fünf Varianten aus den Initialen, alle passen in alle drei Designs. Voreingestellt ist «Passend zum Design»: Siegel zeigt den Ring, Raster die Initialen im Band, Register den Punkt im Anhänger.
- **Logo:** PNG, JPG oder SVG bis 5 MB statt der Initialen, auf dem Deckblatt und klein auf den Folgeseiten. Es wird eingepasst, nie verzerrt, beschnitten oder umgefärbt.
- **Farbe:** Voreingestellt ist die Hauptfarbe des Designs: Siegel Schieferblau, Raster Weinrot, Register Tannengrün. Dazu kommen vier weitere geprüfte Farben, «Eigene Farbe» mit Prüfung und, mit Logo, «Aus dem Logo».
- **Ort:** Unter «Erweitert» in der Karte «Unterlagen prüfen», mit einer Vorschau von Deckblatt und Folgeseite. Gespeichert wird pro Person, sofort bei jeder Wahl.

## Wie es heute ist

- **Designs:** Siegel, Raster und Register sind gebaut (#109, #201, #202). Die Wahl von Dossier oder Anschreiben und Lebenslauf pro Bewerbung ist auf `main` (#203). Die Wahl des Designs, auch pro Seite unter «Erweitert», steht auf dem Branch `feat/204-dossier-design-per-page` (#204), noch nicht auf `main`. Jede Wahl speichert dort sofort.
- **Zeichen:** Jedes Design hat ein festes Zeichen aus den Initialen:
  - Siegel: Ring auf dem Schrittweg, klein im Fuss jeder Folgeseite.
  - Raster: Initialen in 96 pt im Akzentband. Auf Folgeseiten bisher nur die Leiste aus drei Bändern.
  - Register: Anhänger mit Punkt und Initialen, klein im Kopf von Brief und Einzeldateien.
- **Initialen:** `basics.x-monogramm` (1 bis 3 Buchstaben), sonst aus dem Namen. In der App lässt sich das Feld nicht ändern.
- **Farbe:** `dossier.py --akzent` gibt es, die App übergibt aber nichts. Darum gilt überall Schieferblau `#38495d`. Das Theme wählt die Schrift auf der Farbe schon nach Kontrast (`on-accent`, `accent-text` in `themes/tokens.typ`).
- **Logo:** Einen Parameter dafür gibt es nicht.

## Zeichen


| Variante | Aussehen | Voreinstellung bei |
|---|---|---|
| Ring | Initialen in einem Ring in Akzentfarbe, wie der Schrittpunkt «jetzt» des Systems | Siegel |
| Block | Initialen ausgespart in einer Fläche in Akzentfarbe, Radius 13 % | Raster (dort ist das Band die Fläche) |
| Verschränkt | Der erste Buchstabe voll, der zweite als Umriss in Akzentfarbe darüber, wo sie sich treffen. Nur mit genau zwei Buchstaben. | – |
| Linie | Initialen auf einer Linie in Akzentfarbe, die mit einem Punkt endet | – |
| Punkt | Punkt der Statusmarke vor den Initialen | Register |

So kommen die Varianten in die Designs:
- **Siegel:** Die Variante sitzt auf dem Schrittweg. Ring und Block sind selbst der Knoten. Die übrigen stehen auf einer Fläche in Papierfarbe, an der die Linie endet. Klein im Fuss mit 16 pt.
- **Raster:** Die Variante steht einfarbig in `on-accent` unten links im Akzentband. **Neu** steht das Zeichen in den Farben des Designs auch klein im Fuss der Folgeseiten (14 pt), vor «Lea Brunner · 10.11.2026». Die Leiste oben bleibt.
- **Register:** Die Variante ersetzt Punkt und Initialen im Anhänger. Klein im kleinen Anhänger.

Regeln:
- Eine gewählte Variante gilt für alle Seiten, auch bei verschiedenen Designs pro Seite (G39). «Passend zum Design» nimmt pro Seite das Zeichen ihres Designs.
- Bei drei Buchstaben verkleinern Ring und Block die Schrift auf 80 %.
- Verschränkt ist bei einem oder drei Buchstaben gesperrt, mit dem Grund «Nur mit zwei Buchstaben».
- Die Initialen bleiben im PDF echter Text. Der Name steht auf jeder ersten Seite als Text (ATS).

## Eigenes Logo

| Regel | Wert |
|---|---|
| Formate | PNG, JPG, SVG. Anderes lehnt die App mit dem Grund ab. |
| Grösse der Datei | höchstens 5 MB |
| Pixel | ab 1000 Pixel Breite empfohlen; darunter ein Hinweis, keine Sperre |
| Form | 1 : 1 bis 4 : 1 passt gut. Breiter oder höher als 1 : 1.5: Hinweis «Sehr breit» oder «Sehr hoch». |
| Platz Deckblatt | Siegel 150 × 76 pt auf dem Schrittweg; Raster 190 × 90 pt auf weisser Fläche im Band; Register 140 × 44 pt im Anhänger |
| Platz Folgeseiten | Siegel 48 × 16 pt im Fuss; Raster 44 × 14 pt im Fuss; Register 72 × 22 pt im kleinen Anhänger |
| Einpassen | ganz sichtbar, so gross wie der Platz es erlaubt; nie verzerrt, beschnitten oder umgefärbt |
| Durchsichtig | steht direkt auf dem Papier (Siegel, Register) oder auf der weissen Fläche (Raster) |
| Weisser Hintergrund | Auf dem Papier `#fdfcfa` kaum sichtbar, in Raster ohnehin auf Weiss. Nur ein Satz Information. |
| Farbige Fläche | bleibt eine Fläche; die App entfernt keinen Hintergrund |
| SVG | Ohne Skript und ohne Verweise nach aussen, sonst abgelehnt |
| Fehlt beim Erstellen | Das Dossier entsteht mit den Initialen im Zeichen des Designs, dazu ein Hinweis in der Prüfung. |
| Datenschutz | Das Logo liegt im Datenordner, bleibt auf dem Computer und geht nie an die KI. |
| Ein eigenes Zeichen | Der Hinweis sagt «kein Firmenlogo». |

## Akzentfarbe

### Hauptfarbe pro Design

| Design | Farbe | Wert | Warum | Weisse Schrift darauf | Farbe auf Papier |
|---|---|---|---|---|---|
| Siegel | Schieferblau | `#38495d` | ruhig und persönlich; bleibt bei der Farbe des Systems | 9.2 : 1 | 9.0 : 1 |
| Raster | Weinrot | `#7a2e3a` | plakativ und datenhaft; ein kräftiges Rot trägt die grossen Bänder | 9.2 : 1 | 9.0 : 1 |
| Register | Tannengrün | `#2f5d50` | geordnet wie eine Akte; sachlich wie ein Ordnerrücken | 7.5 : 1 | 7.3 : 1 |

Alle drei halten die Regeln: Schrift auf der Farbe mindestens 4.5 : 1, die Farbe auf dem Papier mindestens 3 : 1. Die helle Fläche `accent-subtle` leitet das Theme ab, wie heute (12 % Farbe auf Weiss):
- Weinrot `#efe6e7`;
- Tannengrün `#e6ecea`;
- Schieferblau behält `#e8edf3` aus den Tokens.

`text-strong` steht auf allen drei Flächen mit mindestens 10.5 : 1.

### Was mit Schieferblau geschieht

- Schieferblau bleibt die Farbe von Siegel und die Akzentfarbe der App. An der Oberfläche ändert sich nichts.
- Raster und Register zeigen ab dieser Änderung «Passend zum Design» in Weinrot und Tannengrün. Schon erstellte PDFs bleiben, wie sie sind. Ein neues «Unterlagen erstellen» baut sie in der neuen Farbe.
- Wer Raster oder Register wie bisher will, wählt «Schieferblau». Es steht als benannte Farbe in der Liste.

### Farben zur Wahl

Die Liste ändert sich gegenüber dem ersten Vorschlag: Die drei Farben der Designs stehen vorn, Schieferblau ist jetzt eine eigene benannte Farbe.

| Farbe | Wert | Schrift darauf | Kontrast Schrift | Kontrast Papier |
|---|---|---|---|---|
| Passend zum Design | Farbe des Designs | weiss | wie oben | wie oben |
| Schieferblau | `#38495d` | weiss | 9.2 : 1 | 9.0 : 1 |
| Weinrot | `#7a2e3a` | weiss | 9.2 : 1 | 9.0 : 1 |
| Tannengrün | `#2f5d50` | weiss | 7.5 : 1 | 7.3 : 1 |
| Petrol | `#1d5c6b` | weiss | 7.5 : 1 | 7.3 : 1 |
| Aubergine | `#5b3f6b` | weiss | 8.9 : 1 | 8.6 : 1 |
| Bronze | `#7a5418` | weiss | 6.8 : 1 | 6.6 : 1 |
| Graphit | `#3a3d42` | weiss | 10.9 : 1 | 10.6 : 1 |
| Aus dem Logo | aus dem Logo | weiss oder dunkel | mind. 4.5 : 1 | mind. 3 : 1 |
| Eigene Farbe | Wert oder Farbwahl | weiss oder dunkel | mind. 4.5 : 1 | mind. 3 : 1 |

Alle sechs bisherigen Farben bleiben. Neu ist nur, dass Schieferblau als benannte Farbe dazukommt; damit sind es sieben.

Wie die Wahl wirkt:
- **«Passend zum Design»** wechselt mit dem Design. Bei verschiedenen Designs pro Seite gilt die Farbe des Deckblatts, eine Farbe für alle Seiten.
- **Eine benannte Farbe** bleibt, auch wenn das Design wechselt. In Siegel stehen «Passend zum Design» und «Schieferblau» beide da: Ersteres wechselt mit, Letzteres nicht.
- **Eigene Farbe:**
  - Die App rechnet die Schrift auf der Farbe, weiss oder `text-strong`, mindestens 4.5 : 1.
  - Die Farbe muss auf dem Papier mindestens 3 : 1 erreichen.
  - Geht eines nicht, speichert die App die Farbe nicht und schlägt dieselbe Farbe dunkler vor: `#e0b84a` → `#927119`, `#7f7f7f` → `#757575`.
- **Aus dem Logo** erscheint nur mit Logo. Die App nimmt die häufigste kräftige Farbe, abgedunkelt bis zu den Regeln. Diese Farbe wird nie von selbst gewählt.

## Die gewählte Option B · Unter «Erweitert»


### Unter dem Design: ein Satz

Ein kleines Deckblatt und ein Satz, was gilt, in der Farbe des gewählten Designs. Er wechselt mit dem Design, solange «Passend zum Design» gilt.

| Fall | Satz |
|---|---|
| Siegel | Zeichen: Ring mit LB · Akzentfarbe: Schieferblau · beides passend zu Siegel · Ändern unter «Erweitert». |
| Raster | Zeichen: Initialen im Band · Akzentfarbe: Weinrot · beides passend zu Raster · … |
| Register | Zeichen: Punkt mit LB im Anhänger · Akzentfarbe: Tannengrün · beides passend zu Register · … |
| Seiten gemischt | Zeichen: passend zum Design jeder Seite · Akzentfarbe: Weinrot, passend zum Deckblatt in Raster · … |
| Eigene Wahl | Zeichen: Ring mit LB · Akzentfarbe: Schieferblau · … |
| Logo | Zeichen: Ihr Logo · Akzentfarbe: Aus dem Logo (#a35a2b) · … |

### In «Erweitert»

Zuerst kommt «Zeichen und Farbe», danach «Design pro Seite» (#204).

1. **Zeichen:** eine Liste in zwei Spalten mit Zeichen, Name und einem Satz. Das Zeichen ist echt gezeichnet, in der Farbe des Designs. «Passend zum Design» nennt, was das Design zeigt, etwa «Ring bei Siegel, wie das Design es vorsieht». Der letzte Eintrag ist «Eigenes Logo» mit «Logo wählen».
2. **Initialen:** Feld mit 1 bis 3 Buchstaben, leer heisst aus dem Namen.
3. **Akzentfarbe:** zuerst «Passend zum Design» mit der Farbe des Designs und ihrem Namen, etwa «Schieferblau, Farbe von Siegel». Dann folgen die sieben Farben, «Aus dem Logo» und «Eigene Farbe».
4. «Gilt für alle Dossiers. Schon erstellte bleiben, wie sie sind; mit «Unterlagen erstellen» entsteht dieses neu.» und «Zurück zur Voreinstellung».
5. **Vorschau** rechts, beim Scrollen stehend: Deckblatt und Folgeseite des gewählten Designs. So ist auch das kleine Zeichen im Fuss sichtbar, in Raster neu. Bei 760 px steht die Vorschau über den Feldern.

Jede Wahl speichert sofort, wie das Design (#204). Die Meldung steht in der `status-line`.

### Warum B

1. **G41 wörtlich.** Wer wenig Zeit hat, sieht einen Satz und muss nichts tun. Wer gestalten will, findet alles am selben Ort wie das Design pro Seite.
2. **Nah am Ergebnis.** Die Wahl steht eine Zeile über «Unterlagen erstellen», und die Vorschau zeigt das Design dieser Bewerbung.
3. **Gleiches Verhalten wie #204.** Sofort gespeichert, dieselbe Art Meldung, keine neue Seite.
4. **Pro Person gespeichert,** mit dem Satz am Ort der Wahl.

## Texte

Die meisten Texte sind neutral und gelten für Stellen und Lehrstellen.

| Ort | Sie | du |
|---|---|---|
| Abschnitt | Zeichen und Farbe | gleich |
| Satz unter dem Design | siehe Tabelle oben · Ändern unter «Erweitert». | gleich, beim Logo «Dein Logo» |
| Legenden | Zeichen · Akzentfarbe · Initialen | gleich |
| Zeichen | Passend zum Design · Ring · Block · Verschränkt · Linie · Punkt · Eigenes Logo | gleich |
| Sätze in der Liste | Ring bei Siegel, wie das Design es vorsieht (Block bei Raster …, Punkt bei Register …) · Initialen im Ring · Initialen in einer Fläche · Zwei Buchstaben ineinander · Initialen auf einer Linie · Punkt vor den Initialen · Ihr Logo statt der Initialen | … · Dein Logo statt der Initialen |
| Gesperrt | Nur mit zwei Buchstaben | gleich |
| Initialen | 1 bis 3 Buchstaben. Leer: aus dem Namen. | gleich |
| Logo, Hinweis | PNG, JPG oder SVG, höchstens 5 MB. Am besten quer und mit durchsichtigem Hintergrund. Ein eigenes Zeichen, kein Firmenlogo. Das Logo bleibt auf diesem Computer und geht nie an die KI. | gleich |
| Logo, Knöpfe | Logo wählen · Anderes Logo wählen · Logo entfernen | gleich |
| Logo geladen | Ihr Logo · 1200 × 330 Pixel, durchsichtig | Dein Logo · … |
| Logo sehr breit | Sehr breit: Auf dem Deckblatt wird das Logo nur etwa 7 mm hoch. Ein kompakteres Zeichen wirkt besser. | gleich |
| Logo sehr hoch | Sehr hoch: Das Logo wird auf dem Deckblatt schmal und wirkt klein. Eine quere Fassung passt besser. | gleich |
| Wenig Pixel | Das Bild hat nur 300 × 82 Pixel und wird im Druck unscharf. Besser mindestens 1000 Pixel breit. | gleich |
| Weisser Hintergrund | Das Logo hat einen weissen Hintergrund. Auf dem Papier fällt das kaum auf; in Raster steht es ohnehin auf einer weissen Fläche. | gleich |
| Abgelehnt | Diese Datei ist kein Bild in PNG, JPG oder SVG. · Die Datei ist grösser als 5 MB. Bitte ein kleineres Bild wählen. · Dieses SVG lädt Inhalte aus dem Internet. Bitte das Logo als PNG speichern und nochmals wählen. | gleich |
| Logo fehlt (Prüfung) | Das Logo fehlt. Das Dossier zeigt darum Ihre Initialen im Zeichen des Designs. Logo wählen unter «Erweitert». | … zeigt darum deine Initialen … |
| Farben | Passend zum Design · Schieferblau, Farbe von Siegel (Weinrot, Farbe von Raster · Tannengrün, Farbe von Register) · Schieferblau · Weinrot · Tannengrün · Petrol · Aubergine · Bronze · Graphit · Aus dem Logo · Eigene Farbe | gleich |
| Farbe, Hinweis | «Passend zum Design» ist die Farbe des Designs: Siegel Schieferblau, Raster Weinrot, Register Tannengrün. Sie wechselt mit dem Design; eine benannte Farbe bleibt. Schrift auf der Farbe wählt die App selbst, weiss oder dunkel. | gleich |
| Eigene Farbe, gut | Gut lesbar: weisse Schrift auf der Farbe, Linien gut sichtbar auf dem Papier. (oder: dunkle Schrift) | gleich |
| Eigene Farbe, zu hell | Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht. · Vorschlag #927119 · Vorschlag übernehmen | gleich |
| Eigene Farbe, Mittelton | Weder weisse noch dunkle Schrift ist auf dieser Farbe gut lesbar. Gespeichert wird sie nicht. · Vorschlag … · Vorschlag übernehmen | gleich |
| Eigene Farbe, ungültig | Bitte eine Farbe wie #38495d eingeben. | gleich |
| Gilt für | Gilt für alle Dossiers. Schon erstellte bleiben, wie sie sind; mit «Unterlagen erstellen» entsteht dieses neu. | gleich |
| Gespeichert | Zeichen gespeichert. Mit «Unterlagen erstellen» entsteht das Dossier im neuen Zeichen. · Akzentfarbe gespeichert. Mit «Unterlagen erstellen» entsteht das Dossier in der neuen Farbe. · Logo gespeichert. Mit «Unterlagen erstellen» entsteht das Dossier mit dem Logo. | gleich |
| Zurücksetzen | Zurück zur Voreinstellung · Zeichen und Farbe stehen wieder auf «Passend zum Design». | gleich |
| Vorschau | Deckblatt und Folgeseite in Siegel. Vereinfacht; das PDF entsteht mit «Unterlagen erstellen». | gleich |
| Bildschirmleser | Vorschau Deckblatt: Raster, Initialen im Band, Weinrot | gleich |

## Zugänglichkeit

- **Gruppen.**
  - Zeichen und Farbe sind je ein `fieldset` mit `legend` und echten Radioknöpfen. Die Kachel ist das `label`.
  - Das Zeichen in der Kachel ist `aria-hidden`; der Name steht immer als Text.
  - Gewählt heisst: Rand 2 px `accent`, Fläche `accent-subtle` der App, also Schieferblau, unabhängig von der Farbe des Dossiers.
- **Farbe nie allein.** Jedes Farbfeld trägt seinen Namen. «Passend zum Design» nennt auch die Farbe und das Design.
- **Gesperrt.** Verschränkt bei 1 oder 3 Buchstaben ist `disabled`, mit dem Grund als Text, verbunden über `aria-describedby`.
- **Meldungen** stehen in der `status-line` mit `aria-live="polite"`. Das gilt für Gespeichert, die Hinweise zum Logo und die Prüfung der Farbe.
- **Vorschau.** `role="img"`, das `aria-label` nennt Design, Zeichen und Farbe.
- **Tastatur und Grösse.** Pfeiltasten in der Gruppe, Fokusring `focus` 2 px. Listeneinträge mindestens 72 px hoch, Farbfelder 40 px.
- **Datei.** «Logo wählen» ist ein echtes `input type="file"` mit `accept`. Fehler stehen beim Feld.

## Hinweise für die Umsetzung

- **Daten pro Person,** neben dem Foto in den Grundlagen:
  - `basics.x-zeichen`: `passend` (Voreinstellung), `ring`, `block`, `verschraenkt`, `linie`, `punkt` oder `logo`;
  - `basics.x-logo`: Pfad im Datenordner, wie `basics.image`;
  - `basics.x-akzent`: `passend` oder `#rrggbb`;
  - `basics.x-monogramm` gibt es schon.
  - Prüfen in `dossier_data.py`.
- **Hauptfarbe pro Design.**
  - Eine Konstante pro Theme: Siegel `#38495d`, Raster `#7a2e3a`, Register `#2f5d50`. `default-accent` in `themes/dossier.typ` wird pro Design.
  - `colours-for(d)` nimmt `style.farbe-akzent`, sonst die Hauptfarbe des Deckblatts. Im gemischten Dossier (`themes/dossier-mix.typ`, #204) gilt sie für alle Seiten.
  - Die Tests auf Schieferblau als Standard (`test_dossier_siegel.py` vergleicht `tokens.typ`) bleiben für Siegel gültig. Für Raster und Register kommen Tests der neuen Farbe dazu.
- **Typst.**
  - Neue Datei `themes/zeichen.typ` mit `mark(variant, monogram, size, c, mono: false)` und `logo-fit(path, max-w, max-h)`.
  - Jedes Design ruft sie an seinem Platz auf. Raster bekommt das Zeichen in `footer`.
  - `dossier.py` bekommt `--zeichen` und `--logo`; `--akzent` gibt es.
  - Ein Marker `<dossier-mark>` mit Variante und Logo für Tests, wie `<dossier-level>`.
- **Logo prüfen.**
  - Beim Hochladen in `bewerbungen/`: Format nach Inhalt, nicht nach Endung; Grösse; Pixel; Durchsichtigkeit.
  - SVG ohne `script`, `foreignObject` und Verweise mit `http`/`file`.
  - Die App zeigt das Logo nur als `<img>`.
  - «Aus dem Logo»: die häufigste Farbe mit Sättigung über 25 %, abgedunkelt bis zu den Regeln.
- **Vorschau.** Am genauesten rendert Typst das Deckblatt als PNG, wie auf der Seite «Foto» (`fotoausschnitt.py`). Fallback ist eine vereinfachte SVG-Vorschau wie auf den Boards.
- **Kontrast.** Dieselbe Rechnung in JS und Python, Fälle in einer gemeinsamen Datei wie `onboarding/tests/cases.json`.
- **Anleitung und Webseite.** «Zeichen und Farbe» ist neu sichtbar, und Raster und Register sehen in neuer Farbe anders aus. Darum `docs/installation.md` nachführen, die Bilder in `docs/bilder/` neu machen und ein Begleit-Item auf dem Board von `minigraphx/bewerbungsbegleiter-webseite` anlegen.
- **Datenschutz.** Das Logo geht nicht an die KI, die Vermittlung oder den Update-Server. Keine Änderung der Datenschutzerklärung nötig.
- **`docs/design/dossier.md`** nachführen: Hauptfarbe pro Design statt «Standard ist Schieferblau» und das Zeichen von Raster im Fuss.

## Nicht gewählt: A und C

- **A · Direkt beim Design**: Zeichen, Logo und Farbe offen unter «Design des Dossiers», mit kleiner Vorschau. Am leichtesten zu finden, aber gegen G41, und die Karte wird doppelt so lang. Die Boards zeigen noch die erste Farbliste mit Schieferblau für alle Designs.
- **C · Eigene Seite**: eine Seite «Zeichen und Farbe» unter Meine Angaben neben «Foto», mit allen drei Designs in der Vorschau und einem Knopf «Speichern». Klar pro Person, aber eine Seite mehr, weg von der Bewerbung, und ein zweiter Ort für Feines. Auch hier gilt noch die erste Farbliste.

## Umsetzung

- **Vorschau:** vereinfachte SVG-Zeichnung von Deckblatt und Folgeseite auf der Seite, wie auf den Boards, mit dem echten Zeichen und der wirksamen Farbe. Das PDF entsteht mit «Unterlagen erstellen».
- **Gespeichert** in `cv.yaml` unter `basics`: `x-zeichen` (fehlt = `passend`), `x-akzent` (fehlt = `passend`, sonst `#rrggbb`), `x-logo` (Pfad unter `logos/` im Datenordner, mit Hash im Namen, nie überschrieben) und `x-monogramm`. Jede Wahl legt Entwürfe von `cv.yaml` davor und danach an. «Logo entfernen» lässt die Datei liegen, für Entwürfe und Versionen, die sie nennen.
- **Raster im Fuss:** Das Zeichen steht im Fuss der Folgeseiten, sobald die Person ein Zeichen oder ein Logo gewählt hat. Ohne Wahl bleibt Raster, wie es war, bis auf die Hauptfarbe.
- **«Aus dem Logo»:** Typst rendert das Logo klein als PNG; die häufigste Farbe mit Sättigung über 25 % wird gemittelt und abgedunkelt bis zu den Regeln. Statt eines Farbnamens wie «Kupfer» nennt die App den Wert, etwa «Aus dem Logo (#a35a2b)». Eine andere eigene Farbe heisst «Eigene Farbe (#…)».
- **Fehlt das Logo** oder ist ein SVG später verändert worden, zeichnet das Dossier das Zeichen des Designs, und die Prüfung meldet «Das Logo fehlt. Das Dossier zeigt darum die Initialen im Zeichen des Designs. Logo wählen unter «Erweitert».» in neutraler Form.
- **Verschränkt** mit einem oder drei Buchstaben: gesperrt auf der Seite; steht es trotzdem in `cv.yaml`, zeichnet das Dossier das Zeichen des Designs.
- **Kontrast:** dieselbe Rechnung in `mark.py` und `zeichen-logik.js`, Fälle in `lebenslauf/tests/accent_cases.json`. Abgedunkelt wird in Schritten von 1 % Helligkeit (HSL), so entstehen die Vorschläge `#927119` und `#757575`.
- **Befehlszeile:** `dossier.py --zeichen <variante>` und `--logo <datei>` gehen vor `cv.yaml`; `--akzent` geht vor `basics.x-akzent`.

