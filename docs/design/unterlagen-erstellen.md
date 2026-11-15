# Wo Anschreiben und Lebenslauf entstehen

Gehört zu #238. Vorschlag zur Wahl durch Andy, entschieden am 15.11.2026 (Abschnitt «Entscheid»). Die Zeichenflächen liegen in Claude Design (Original privat: [Zeichenfläche](https://claude.ai/artifact/KxQLkEiqTsQe69wJwePzEa), Designsystem Bewerbungsassistent): ein Board mit dem heutigen Stand, drei Boards pro Option. Sie bauen auf A6 und A7 der Neugestaltung auf (`README.md`, Abschnitt «Neugestaltung der App ab 0.3»). Alle Personen, Firmen und Daten sind erfunden.

**Frage:** Der Schritt, der die Unterlagen erstellt, wirkt auch mit «Erweitert» sehr lang. Gehört das Erstellen von Anschreiben und Lebenslauf dorthin oder an getrennte Orte?

**Kurz:** Zwei Optionen. A lässt das Erstellen im Schritt Prüfen und kürzt ihn. B lässt jedes Dokument in seinem Schritt entstehen und legt, was für alle Bewerbungen gilt, auf «Lebenslauf und Dateien». **Empfehlung: B.**

## Befund heute

Gemessen auf `main` vom 14.11.2026, 1280 px breit, eine Bewerbung mit Dossier, «Erweitert» offen:

| Teil der Karte «Unterlagen prüfen» | Höhe |
| --- | --- |
| Titel, Erklärung, Form (Anschreiben und Lebenslauf oder Dossier) | 250 px |
| Design des Dossiers mit Zeile zu Zeichen und Farbe | 230 px |
| Erweitert: Zeichen, Logo, Initialen, Akzentfarbe, Design pro Seite | 1700 px |
| Begrüssung und Dank | 440 px |
| «Unterlagen erstellen» und Befunde | 160 px |
| PDF eingebettet (pro Dokument) | 675 px |
| Beilagen | 120 px |
| **Ganze Karte** | **3800 px** |

- Die Karte trägt fünf Aufgaben: Form wählen, Dossier gestalten, Begrüssung und Dank schreiben, erstellen und prüfen, Beilagen wählen. Vor dem Knopf «Unterlagen erstellen» liegen rund 2600 px Gestaltung.
- Zeichen und Farbe gelten für alle Dossiers, stehen aber in einer einzelnen Bewerbung. Das Aussehen des Lebenslaufs wählt die Person dagegen auf «Lebenslauf und Dateien» (G61). Zwei Orte für dieselbe Art Wahl.
- Der Titel sagt «prüfen», die Karte erstellt. Begrüssung und Dank sind Texte wie das Anschreiben, stehen aber beim Prüfen.
- Die Kacheln für Zeichen sind in der Spalte zusammengedrückt; die PDF-Vorschau ist eingebettet.
- Gut und zu behalten: Die Vorgabe (Anschreiben und Lebenslauf) braucht keine Wahl, «Erweitert» bleibt zu, bis die Person es öffnet, die Befunde stehen direkt unter dem Knopf.

## Option A · Im Schritt Prüfen, aber kürzer

Boards A1 bis A3. Erstellt wird weiter im Schritt Prüfen.

- **Vor dem Erstellen (A1):** Form als zwei Kacheln. Mit Dossier eine graue Zeile mit Miniatur des Deckblatts, Design, Zeichen und Stand von Begrüssung und Dank, daneben «Dossier gestalten». Darunter «Unterlagen erstellen» und die Beilagen als eine Zeile mit «ändern». Etwa 700 px statt 3800.
- **Dossier gestalten (A2):** ein Dialog mit Design (drei Kacheln), Zeichen und Farbe in voller Breite, Begrüssung und Dank, Vorschau des Deckblatts; «Design pro Seite» zugeklappt. Der Dialog sagt, dass Zeichen und Farbe für alle Dossiers gelten.
- **Nach dem Erstellen (A3):** Befunde wie A7, «In Ordnung» zugeklappt; je Dokument eine Miniatur mit «Gross ansehen» statt eingebetteter PDF; Form und Beilagen als Zeilen am Ende.
- **Bauen:** ein Item für den Schritt (Kacheln, Zusammenfassung, Ergebnis, Miniaturen), ein Item für den Dialog. Keine neue Spec-Zeile; G18, G19, G39, G40 und G41 bleiben.
- **Schwäche:** Zeichen und Farbe, die für alle Dossiers gelten, bleiben in einer einzelnen Bewerbung, nur eine Ebene tiefer.

## Option B · Jedes an seinem Ort

Boards B1 bis B3.

- **Schritt Lebenslauf:** wie A6, unverändert. Dort entsteht der Lebenslauf.
- **Schritt Anschreiben (B1):** Entwurf lesen und freigeben. Darunter die Form als zwei Kacheln; mit Dossier stehen dort Begrüssung und Dank, von der KI zusammen mit dem Anschreiben entworfen. In der Seitenspalte die Vorschau des Deckblatts mit «Für diese Bewerbung ändern». Mit der Freigabe erstellt die App die PDF.
- **Schritt Prüfen (B2):** nur noch das Ergebnis, wie A7: Befunde, Miniaturen, Form und Beilagen je als eine Zeile mit Link an den Ort, wo sie entstehen. Hier wird nichts mehr gewählt.
- **Lebenslauf und Dateien, Abschnitt «Aussehen» (B3):** Lebenslauf (Zweispaltig oder Einspaltig, mit Foto; gibt es schon nach G61 und G62) neben dem Dossier: Design, Zeichen, Akzentfarbe, Vorschau; unter «Erweitert» Initialen, eigenes Logo und Design pro Seite. Gilt für neue Bewerbungen, Versendetes bleibt.
- **Bauen:** drei Items: Abschnitt «Aussehen» auf Lebenslauf und Dateien, Schritt Anschreiben mit Form und Begrüssung und Dank, Schritt Prüfen als reines Ergebnis.
- **Spec:** braucht eine neue Zeile für das Design des Dossiers als Vorgabe pro Person auf «Lebenslauf und Dateien», analog G61. G18, G19, G39, G40 und G41 bleiben.

## Empfehlung

**B.** Ein Ort pro Art Wahl: Was für alle Bewerbungen gilt, steht dort, wo heute schon das Aussehen des Lebenslaufs steht, und eine Bewerbung bleibt auch mit Dossier kurz. Jeder Schritt tut, was sein Name sagt; Prüfen prüft. A ist schneller gebaut und eine gute Zwischenstufe, lässt aber die Wahl, die für alle Dossiers gilt, in jeder Bewerbung stehen.

## Offen

- Bei B ist zu entscheiden, ob die Form (Dossier oder zwei PDF) wie heute pro Bewerbung mit der Vorgabe «Anschreiben und Lebenslauf» beginnt (G40) oder ob die Person auf «Lebenslauf und Dateien» auch die Form als eigene Vorgabe setzen kann. Das wäre eine Änderung an G40.
- Die Anleitung (`docs/installation.md`) und ihre Bilder ändern sich erst mit dem Bau; dann braucht es ein Begleit-Item für die Webseite.

## Entscheid

Andy hat am 15.11.2026 **Option A** gewählt. Der Lebenslauf entsteht getrennt vom Anschreiben, weil meist mehrere Stellen denselben Lebenslauf teilen. Aus dem Schritt der Bewerbung führt deshalb ein Klick an den Ort, wo der Lebenslauf angepasst wird.

Umgesetzt wird das in zwei Items:

- **#321:** kürzerer Schritt «Unterlagen erstellen und prüfen» mit Kacheln für die Form, einer Zeile zum Dossier und pro Dokument einer Kachel mit Link an den Ort, wo es angepasst wird (G40, G41).
- **#322:** Dialog «Dossier gestalten» mit den Gruppen «Für diese Bewerbung» und «Für alle Dossiers» (G18, G19, G39).

Eine neue Spec-Zeile braucht es nicht; die offene Frage zu G40 betraf nur Option B.
