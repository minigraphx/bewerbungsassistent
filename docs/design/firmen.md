# Firmen mit kununu-Bewertung: Gestaltungsvorschlag

Stand 09.11.2026, freigegeben vom Inhaber am selben Tag. Das Mockup (hell, erfundene Firmen und Zahlen) liegt nicht im Repo. Baut auf `docs/design/system/` und `docs/design/texte.md` auf; neue Klassen englisch, Texte in Schweizer Schreibweise. Umgesetzt in G35: Seite #188, Lesen über die Erweiterung #189, Marke auf Stellen suchen #190.

## Entscheide des Inhabers (09.11.2026)

Sie gehen dem Vorschlag unten vor:

- **Geprüft wird nur auf Klick der Person, Firma für Firma.** Es gibt keinen Durchgang über alle Firmen, keinen Hauptknopf «2 Firmen bei kununu prüfen» und keinen Schalter in «Suche einstellen». Was unten dazu steht (Entscheid 6, Zustand «Wird geprüft» mit `Progress`, Hauptknopf, Durchgang, Schalter), gilt nicht.
- **Wenige Bewertungen:** Die Schwelle bleibt bei 10.
- **Zuerst kununu.com/ch**, kununu.de nur, wenn die Suche in der Schweiz nichts findet. Die Seite zeigt, woher der Wert kommt.
- **Lehrbetriebe:** Weist kununu die Bewertungen von Lernenden getrennt aus, erscheinen sie zusätzlich.
- Offene Fragen 2 bis 4 sind damit beantwortet. Frage 1 klärt #189 vor dem Lesen der Seiten; Frage 5 (Datenschutzerklärung, Anleitung, Webseite) läuft über Begleit-Items.

## Entscheide zuerst

1. **Hauptort: eine neue Seite «Firmen»** (bei Lehrstellen «Lehrbetriebe»), eine Zeile pro Firma aus allen Treffern und Bewerbungen. Darum gebeten hat der Inhaber, und nur eine eigene Seite hat Platz für die Zustände, die Wahl bei mehreren Treffern und die Prüfung in einem Durchgang. Gruppiert wird nach dem bestehenden Firmen-Schlüssel (`company_key`). Eine Wahl der Person gilt darum für alle Treffer dieser Firma und wird nur einmal gefragt.
2. **Nebenort: Stellen suchen.** In der Trefferzeile steht eine kleine Marke «kununu 3.8» gleich nach dem Firmennamen. In der Detailspalte folgt unter der KI-Karte eine Firmenzeile mit dem Link «Bei kununu ansehen». Dort wird entschieden, ob man einen Treffer übernimmt, also gehört der Wert dorthin.
3. **Nicht auf die Übersicht, kein Block auf der Bewerbung.** Die Tabelle der Übersicht hat schon fünf Spalten und eine Note. Eine zweite Zahl daneben macht sie lauter und lädt dazu ein, laufende Bewerbungen nach dem Ruf der Firma zu ordnen, obwohl der Entscheid längst gefallen ist. Auf der Bewerbung darf der Wert «Firma» in der Seitenspalte zur Zeile auf «Firmen» verlinken, aber ohne Wert dort.
4. **Zugang:** im Menü «Mehr» als erster Eintrag («Firmen») und als leiser Link «Firmen ansehen» in der Leiste von Stellen suchen. Die Hauptnavigation behält drei Punkte, denn sie folgt dem Ablauf.
5. **Nicht mit der Note zu verwechseln** (Details unten): Die Note der App bleibt die einzige Zahl mit Balken, Akzentfarbe und Wort. kununu erscheint nie ohne das Wort «kununu» und den Zusatz «von 5», nie mit Balken oder Sternen und nie in Akzent, Grün oder Rot.
6. **Geprüft wird nur auf Wunsch:** über den Knopf auf «Firmen», über «Prüfen» in einer Zeile oder über einen Schalter in «Suche einstellen», der als Vorgabe aus ist. An kununu geht nur der Firmenname. Das steht in einem Satz direkt beim Knopf.
7. **Keine Rangliste als Vorgabe.** Die Liste sortiert zuerst nach «Treffer und Bewerbungen», nicht nach dem kununu-Wert, und hat keinen Filter «ab 3.5». Ein Schwellenfilter würde Firmen mit wenigen Bewertungen still ausblenden.

## Was pro Firma steht

| Teil | Firmen-Seite | Trefferzeile | Detailspalte |
| --- | --- | --- | --- |
| Name, Ort | ja | (steht schon da) | ja |
| kununu-Wert 1–5, eine Stelle nach dem Punkt | «3.8 von 5» | «kununu 3.8» | «3.8 von 5» |
| Anzahl Bewertungen | «214 Bewertungen» | nur für Bildschirmleser | ja |
| Weiterempfehlung | «78 % empfehlen» | nein | ja |
| Geprüft am | «05.11.2026», ab 90 Tagen «Stand …» mit «Neu prüfen» | nein | ja |
| Link | «Bei kununu ansehen», neuer Tab | nein (die Zeile ist ein Knopf) | ja |
| Verknüpft | «3 Treffer, 2 neu» als Link, jede Bewerbung mit Stelle und Statusmarke | nein | «Alle Firmen» |

Zahlen: `3.8` mit Punkt wie die Noten, `1’312` mit Hochkomma, `78 %` mit Leerschlag. Der Wert kommt unverändert von kununu und wird nicht gerundet oder umgerechnet.

### Zustände

| Zustand | Firmen-Seite | Trefferzeile | Detailspalte |
| --- | --- | --- | --- |
| Noch nicht geprüft | «Noch nicht geprüft» + Knopf «Prüfen» | nichts | «Noch nicht bei kununu geprüft.» + «Jetzt prüfen» |
| Wird geprüft | «Wird geprüft …» (`role=status`); läuft ein Durchgang, oben `Progress` «3 von 12» mit «Anhalten» | nichts | «Wird geprüft …» |
| Gefunden, genug Bewertungen (ab 10) | Wert, Anzahl, Empfehlung, Datum, Link | Marke mit durchgezogenem Rand | volle Zeile |
| Wenige Bewertungen (1–9) | Wert in `text`, gestrichelter Rand, «Nur 3 Bewertungen, wenig aussagekräftig.» | «kununu 4.6, wenige Bewertungen», gestrichelt | gleich wie auf der Seite |
| Gefunden, keine Bewertungen | «Noch keine Bewertungen» + Link | nichts | gleich |
| Mehrere Firmen bei kununu | «Mehrere Firmen bei kununu» + «Passende wählen» klappt eine Auswahl auf | «kununu: wählen», leise | Satz + Link zur Zeile auf «Firmen» |
| Nicht gefunden | «Bei kununu nicht gefunden» + «Bei kununu suchen» (neuer Tab) + «Selbst zuordnen» | «nicht bei kununu», leise, ohne Rand | gleich wie auf der Seite |
| Fehler | Status-Zeile `warning`: «Nicht geprüft. kununu war nicht erreichbar. Bitte später nochmals prüfen.» + «Nochmals prüfen» | nichts | gleich |
| Veraltet (über 90 Tage) | Wert bleibt, Datum als «Stand 02.07.2026», Knopf «Neu prüfen» | Marke bleibt | Datum als Stand |

**Wenige Bewertungen:** Der gestrichelte Rand und der Zusatz «· unsicher» sind im System schon das Zeichen für unsichere Noten. Hier tragen gestrichelter Rand und Wort die Bedeutung, nicht die Farbe. Beim Sortieren nach kununu stehen solche Firmen hinter allen Firmen mit genug Bewertungen. Die Schwelle 10 ist ein Vorschlag (offene Frage 2).

**Mehrere Treffer:** Die Auswahl klappt in der Tabelle unter der Zeile auf: ein `fieldset` mit Radioknöpfen, je mit Name, Ort, Anzahl Bewertungen und «Bei kununu ansehen». Dazu kommt die Wahl «Keine davon passt», danach «Zuordnen» oder «Abbrechen». «Keine davon» setzt den Zustand «nicht gefunden».

**Selbst zuordnen:** ein `<dialog>`: «Welche kununu-Seite gehört zu Testlogistik GmbH?», ein Feld für den Link, «Abbrechen» und «Zuordnen». Ein falscher Link ergibt einen Feldfehler.

### Note und kununu sicher unterscheiden

| | Note der App | kununu |
| --- | --- | --- |
| Skala | 1–6, Schweizer Note | 1–5, «von 5» steht immer da |
| Ort in der Trefferzeile | eigene Spalte links | im Text, direkt hinter dem Firmennamen |
| Form | Zahl 16–20 px fett, sechs Balken in `accent`, Wort «passt gut» | Marke mit Rand `line-strong`, `radius-sm` (eckiger als Statusmarken), Wort «kununu» in `text-muted`, Zahl in 500 |
| Farbe | `accent` | nur Grautöne, nie `accent`, Grün oder Rot, auch nicht bei tiefen Werten |
| Bedeutung | wie gut die Stelle zu den Angaben passt | wie Mitarbeitende die Firma bewerten |

Ein Satz in «Wie lese ich kununu?» sagt den Unterschied ausdrücklich.

## Sortieren und Filtern (Firmen)

- Sortierbare Spaltenköpfe als `<button>` mit `aria-sort`, wie auf der Übersicht: **Firma** (A–Z), **kununu** (Wert, absteigend; Firmen mit wenigen Bewertungen danach, dann ohne Bewertungen, nicht gefunden und ungeprüft; die ohne Wert bleiben in beiden Richtungen unten), **Treffer und Bewerbungen** (Vorgabe, absteigend, neue Treffer zuerst), **Geprüft** (Datum).
- Filtergruppe mit `aria-pressed`, wie bei den Treffern: **Alle 11 · Mit neuen Treffern 5 · Mit Bewerbung 4 · Zu klären 3**. «Zu klären» umfasst mehrere Treffer, nicht gefunden und Fehler.
- Suchfeld «Firma suchen». Passt nichts: «Keine Firma passt zu dieser Suche.»
- Firmen, zu denen es nur verworfene Treffer oder abgeschlossene Bewerbungen gibt, erscheinen nur unter «Alle».

## Texte

Neutral, wo es geht. Die Spalte «Stellen mit du» entspricht der Spalte du, nur mit Firma und Firmen statt Lehrbetrieb.

| Ort | Sie (Stellen) | du (Lehrstellen) |
| --- | --- | --- |
| Menü Mehr, Titel | Firmen | Lehrbetriebe |
| Link auf Stellen suchen | Firmen ansehen | Lehrbetriebe ansehen |
| Zeile unter dem Titel | 11 Firmen aus Treffern und Bewerbungen · 7 bei kununu gefunden · zuletzt geprüft heute, 08:20 | 11 Lehrbetriebe aus Treffern und Bewerbungen · … |
| Hauptknopf | 2 Firmen bei kununu prüfen · Alle neu prüfen | 2 Lehrbetriebe bei kununu prüfen · Alle neu prüfen |
| Unter dem Knopf | Nur der Firmenname geht an kununu. Ihre Angaben bleiben auf diesem Computer. | Nur der Name des Lehrbetriebs geht an kununu. Deine Angaben bleiben auf diesem Computer. |
| Durchgang | kununu wird geprüft · 3 von 12 · Anhalten · Meist wenige Sekunden pro Firma. | … pro Lehrbetrieb. |
| Schalter in Suche einstellen | Firmen nach der Suche bei kununu prüfen | Lehrbetriebe nach der Suche bei kununu prüfen |
| Spalten | Firma · kununu · Treffer und Bewerbungen · Geprüft | Lehrbetrieb · kununu · Treffer und Bewerbungen · Geprüft |
| Filter, Suchfeld | Alle · Mit neuen Treffern · Mit Bewerbung · Zu klären · Firma suchen | … · Lehrbetrieb suchen |
| Werte | 3.8 von 5 · 214 Bewertungen · 78 % empfehlen · Stand 02.07.2026 | gleich |
| Zustände | Noch nicht geprüft · Wird geprüft … · Noch keine Bewertungen · Nur 3 Bewertungen, wenig aussagekräftig. · Bei kununu nicht gefunden · Mehrere Firmen bei kununu | … · Mehrere Lehrbetriebe bei kununu |
| Fehler | Nicht geprüft. kununu war nicht erreichbar. Bitte später nochmals prüfen. | gleich |
| Knöpfe, Links | Prüfen · Neu prüfen · Nochmals prüfen · Bei kununu ansehen · Bei kununu suchen · Selbst zuordnen · Passende wählen · Zuordnen · Abbrechen | gleich |
| Auswahl | Welche ist Beispiel Holding AG, Zürich? · Keine davon passt · Ort und Branche helfen beim Wählen. | gleich |
| Dialog | Welche kununu-Seite gehört zu Testlogistik GmbH? · Link zur Firma bei kununu · Bei kununu die Firma öffnen und den Link aus der Adresszeile kopieren. · Das ist kein Link zu einer Firma bei kununu. | … · Link zum Lehrbetrieb bei kununu · Bei kununu den Lehrbetrieb öffnen … · … zu einem Lehrbetrieb bei kununu. |
| Trefferzeile | kununu 3.8 · kununu 4.6, wenige Bewertungen · kununu: wählen · nicht bei kununu | gleich |
| Detailspalte | Muster Industrie AG bei kununu · Geprüft am 05.11.2026 · Alle Firmen · Noch nicht bei kununu geprüft. · Jetzt prüfen | … · Alle Lehrbetriebe |
| Hilfe, Titel | Wie lese ich kununu? | gleich |
| Hilfe, Text | Auf kununu bewerten heutige und frühere Mitarbeitende ihre Firma: 5 ist der beste Wert, 1 der schlechteste. Unter 10 Bewertungen sagt der Wert wenig. Die Note der App sagt dagegen, wie gut eine Stelle zu Ihren Angaben passt. | … ihren Lehrbetrieb … wie gut eine Lehrstelle zu deinen Angaben passt. |
| Leer | Noch keine Firmen. Die Liste füllt sich mit der Suche und mit Stellen, die Sie von Hand erfassen. | Noch keine Lehrbetriebe. Die Liste füllt sich mit der Suche und mit Lehrstellen, die du von Hand erfasst. |
| Quelle (Fuss) | Bewertungen: kununu.com, Stand am angegebenen Tag. Sie stammen von Mitarbeitenden, nicht von der App. | gleich |
| Bildschirmleser | kununu 3.8 von 5, 214 Bewertungen · kununu 4.6 von 5, nur 3 Bewertungen · bei kununu nicht gefunden · Muster Industrie AG bei kununu ansehen, öffnet neuen Tab | gleich |

«Sie» als Fürwort für Firmen ist vermieden («Die Liste füllt sich …»), weil es in der Sie-Form doppeldeutig wäre.

## Zugänglichkeit und Telefon

- Bedeutung nie nur über Farbe: Wörter («wenige Bewertungen», «nicht bei kununu») und Linienart (gestrichelt) tragen sie. Alle Marken bleiben in Grautönen, die 4.5:1 einhalten (`text-strong` und `text-muted` auf `surface`).
- Die Trefferzeile ist ein `<button>`. Darin darf kein Link stehen. Die Marke ist darum nur Text, und ihr Wortlaut für Bildschirmleser gehört zum Namen des Knopfs. Der Link steht in der Detailspalte.
- Jeder externe Link nennt die Firma und sagt «öffnet neuen Tab» (`visually-hidden`), mit `target="_blank" rel="noopener noreferrer"`. Symbole gibt es keine, wie im System vorgesehen.
- Prüfen meldet sich über `role=status` / `aria-live="polite"` in der Zeile, ein Durchgang über `Progress`. «Passende wählen» trägt `aria-expanded`. Beim Aufklappen springt der Fokus auf die Legende, nach «Zuordnen» zurück auf die Zeile, wo eine Status-Zeile das Ergebnis meldet.
- Die Tabelle ist eine `table` mit `th scope`. Unter 760 px wird jede Zeile zur Karte (vorhandene Container-Abfrage von `DataTable`, `data-label`). Die Knöpfe sind dann 40 px hoch und brechen um. Die Marke in der Trefferzeile darf umbrechen, aber nie mitten in «kununu 3.8» (`white-space: nowrap`).

## Offene Fragen an Andy

1. **Rechtliches und Technik:** Die Nutzungsbedingungen von kununu verbieten das automatische Auslesen womöglich. Zu klären ist, ob das zulässig ist und ob es über die Erweiterung im Browser der Person oder über die App läuft. Die Gestaltung passt zu beidem.
2. Bleibt die Schwelle für «wenige Bewertungen» bei 10?
3. Gilt immer kununu.com/ch, oder auch kununu.de für Firmen in Grenznähe?
4. Sollen bei Lehrbetrieben die Bewertungen von Lernenden erscheinen, falls kununu sie getrennt ausweist?
5. Die Datenschutzerklärung (auf dem Hosting) muss nachgeführt werden, weil Firmennamen an kununu gehen. Die Anleitung und die Webseite bekommen ein Begleit-Item.
