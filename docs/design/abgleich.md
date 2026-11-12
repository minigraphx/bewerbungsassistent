# Abgleich der App mit dem Design

Stand 7.11.2026, Item #23. Verglichen wurden die Bilder in `entwurf/` und die Quellen in `seiten/` mit `main`, in der laufenden App mit erfundenen Daten. Die nummerierten Punkte sind **nicht geändert** und warten auf einen Entscheid. Was Andy nicht entscheidet, bleibt, wie es ist.

## Behoben, weil klar falsch

Wer die App mit du nutzt, las an einigen Stellen trotzdem Sie:

- Seiten „Erweiterte Einstellungen“ und „Fragen an die KI“.
- Vorschläge für die Suche bei Stellen mit du.
- „Wo suchen Sie?“ bei Stellen mit du.
- Drei einzelne Sätze: Einladungscode, Tab nach dem Update, Fragen aufgebraucht.
- In der Formularleiste stand „Prüf den Eintrag“ statt „Prüfe den Eintrag“.

## Entscheide, die mehrere Seiten betreffen

| # | Thema | Design | App | Vorschlag |
| --- | --- | --- | --- | --- |
| 1 | Noten und Dezimalzahlen | `4.5`, „nie 4,5“ | App `4,5` (bewusst, c50db93), Popup der Erweiterung `4.5`, Foto `4,65 cm` neben `1.20×` | Entschieden (10.11.2026, #221): Punkt überall, wie im Design: Note der KI, kununu („kununu 3.8 von 5“), Foto und Dateigrössen. |
| 2 | Währung der Kosten | CHF | USD, wie Anthropic abrechnet | USD lassen, bis die Vermittlung in CHF abrechnet. |
| 3 | Kosten pro Antwort | „Claude · CHF 0.01“ im Fuss von KI-Karten und Popup | nur die Kostenzeile der Suche und die Summen in den Einstellungen | offen |
| 4 | Seitenrand | 32 px oben, 24 px seitlich | 24 px oben, 16 px seitlich | Design übernehmen; kleine Änderung. |

## Bewerbung

| # | Design | App | Vorschlag |
| --- | --- | --- | --- |
| 5 | Nur die Karte des aktuellen Schritts ist offen. | Alle Abschnitte stehen untereinander, die Seite wird sehr lang. | Am meisten Wirkung; eigenes Item. |
| 6 | Nach dem Versand: grünes Banner zuoberst, nur noch Antwort, versendete Fassung, Inserat und KI-Einschätzung. | Banner steht unten unter „Abschicken“; Lebenslauf, Anschreiben, KI-Knöpfe und Einwilligung bleiben sichtbar. | Design übernehmen. |
| 7 | Anschreiben: „Neu entwerfen“, „Eigenes Anschreiben verwenden“, „Satz streichen“, „In Meine Angaben ergänzen“, Karte „Einschätzung der KI“. „Freigeben“ ist der Hauptknopf. | Diese Knöpfe und die Karte fehlen, „Freigeben“ ist ein Randknopf. | Einzeln ansehen. |
| 8 | Lehrstelle: „Lehrbeginn“ in den Angaben, zwei Noten im Kopf (Beruf und Lehrstelle), Kontakt. | „Pensum“, eine Note, kein Kontakt. | Design übernehmen; Lehrbeginn fehlt dort sonst ganz. |
| 9 | Abschicken: Formular offen seit 10:42, Zählung der Felder, Vorschau der Leiste, „Ja, abgeschickt / Noch nicht“. | Eine Statuszeile und „Versand erfassen“. | offen |
| 10 | Verlauf mit Zwischenschritten („Aus der Suche übernommen“, „Anschreiben entworfen“). Schrittzeile „übernommen 03.11.“. | Nur „Erfasst“, „Beworben“, „Versand erfasst“. Schrittzeile „erfasst 20.10.“. | offen |
| 11 | Kein Knopf bei der Notiz, Schrittnamen nicht unterstrichen. PDF-Titel mit Seitenzahl, „PDFs neu erstellen · Lebenslauf ändern“. | Knopf „Notiz speichern“, Schrittnamen unterstrichen (sind Links). PDF-Titel ohne Zusatz, der Link fehlt. | Knopf und Links lassen. |

## Suche und Übersicht

| # | Design | App | Vorschlag |
| --- | --- | --- | --- |
| 12 | „Deine Berufe“ als drei Chips mit bis zu drei Sternen. | Senkrechte Liste mit fünf Sternen; die Skala stammt aus dem Datenmodell. | offen |
| 13 | Zähler „3 von 10“ am Menüpunkt der Suche. | Fehlt; das CSS ist da, das Markup nicht. | Einbauen oder CSS entfernen. |
| 14 | Datum relativ („heute“, „gestern“). | Datum absolut. | offen |

## Übrige Seiten

| # | Seite | Design | App |
| --- | --- | --- | --- |
| 15 | Meine Dateien | Metazeile pro Datei (Seiten, Grösse, Datum), Entfernen als Textlink; „Wird jetzt verwendet“, „Kein PDF hochgeladen“; eigene Gruppentitel bei Lehrstellen. | Hilfetext und Knöpfe; „Wird verwendet“, „Noch kein PDF hochgeladen“; dieselben Gruppentitel. |
| 16 | Inhalte als Text | Dateiliste links, Reiter „Ansicht / Als Text“. | Auswahlmenü und Umschaltknopf, zusätzlich „Letzte Entwürfe“. |
| 17 | Entwürfe | Karten pro Datei mit Filter, „Mit jetzt vergleichen“, „Zurückholen“. | Tabelle mit „Vergleich mit vorher“, „Wiederherstellen“, „Löschen“. |
| 18 | Entwürfe, Vergleich | Zwei Spalten, durchgestrichen und unterstrichen, Knopf „Fassung zurückholen“. Für Einsteiger lesbar. | Technischer Diff als Text mit `cv.yaml`, `@@`, `+` und `-`. |
| 19 | Foto | „Foto im Lebenslauf zeigen“, „Anderes Foto wählen“, „Foto entfernen“. | „Zoom“, „Ausschnitt waagrecht (x)“ und ein YAML-Block; die drei Knöpfe fehlen. |
| 20 | Fragen | Chat-Karten, Knopf „Fragen“, Zähler „18 von 20“, eigene Beispielfragen für Lehrstellen. | Knopf „Senden“, „Heute noch 30 Fragen“, dieselben Beispiele für alle. |
| 21 | Einstellungen | Eigene Karten „Zugang zur KI“, „Fragen an die KI“ (Schalter, Limit) und „Weitere Seiten durchsuchen“ mit Status; Budget als Balken. | Die zwei ersten Karten fehlen, „Weitere Seiten“ erscheint nur mit eigenem Schlüssel, Kosten ohne Budget. |
| 27 | Meine Angaben | Ein Block zum Vorbefüllen mit Dateiliste und Knopf „Vorbefüllen“, darunter „Alles wird laufend gespeichert, zuletzt um 10:42“. | Vier Gruppen zum Hochladen (Lebenslauf, Zeugnisse, Zertifikate, frühere Anschreiben), keine Zeile zum Speichern. |
| 22 | Einrichtung | Link und Knöpfe nicht vorgesehen. | Zusätzlich „Anleitung mit Bildern“, „In Chrome/Edge öffnen“, „Ordner zeigen“, Mac-Hinweis. Vorschlag: lassen, sie helfen beim Einstieg. |

## Erweiterung

| # | Design | App |
| --- | --- | --- |
| 23 | Feldmarken mit Etikett („ausgefüllt“, „offen, bitte selbst ausfüllen“). | Nur ein farbiger Rahmen, kein Etikett. |
| 24 | Dieselben Farben in Leiste und Formular. | Legende `#4caf50`, `#ff9800`; Formular `#2e7d32`, `#ef6c00`. |
| 25 | Leistenzustand „Dateien hochladen“ mit Satz zum Formular. | Knopf „Dateien im Ordner zeigen“. |
| 26 | Erlaubnis-Seite nennt die Domain. | Nennt keine Domain, weil die Erlaubnis alle Seiten betrifft. |
| 28 | Kürzere Texte in Job-Room- und Such-Leiste. | Längere Texte, in der Such-Leiste mit „Bitte nichts anklicken und nicht schliessen, sonst endet sie“. Vorschlag: lassen, der Satz erklärt das Verhalten. |

## Absichtlich, bleibt

- Name „Bewerbungsbegleiter“, „die App“ statt „der Assistent“ (0684dd8, c50db93). Die Bilder in `entwurf/` zeigen noch den alten Namen.
- Sortierpfeile in der Liste der Übersicht (a578c1b).
- „Bewerten“, „Neu bewerten“, „Inserat hier lesen“, automatisches Bewerten in der Suche (61d7db2, 5bf430e).
- Einwilligung vor dem ersten KI-Aufruf, in Einrichtung, Bewerbung und Einstellungen (2069cd5, 6a5c58b).
- Einfache Einrichtung ohne Desktop-Teil zeigt nur den ersten Schritt (e8c20e1).
- Die Lücke unter „Lebenslauf-Variante“ aus dem Item liess sich nicht nachstellen, weder bei 1280 noch bei 760 px.

## Abdeckung

Jede Datei in `seiten/`. „Bild“ heisst: Bild des Designs und Aufnahme der App verglichen. „Code“ heisst: nur gegen den Code verglichen, nicht gerendert.

| Seite | Geprüft | Ergebnis |
| --- | --- | --- |
| Main | Bild | #4, sonst stimmt sie |
| Uebersicht-760 | Bild | stimmt |
| Uebersicht-Dunkel | Bild, Dialog nur Code | stimmt |
| Uebersicht-Erststart | Bild | #4, sonst stimmt sie |
| Nav | Bild | #13 |
| Suche | Bild | #2, #3, #14 |
| Suche-760 | Bild | wie Suche |
| Suche-Lehrstellen | Bild | #12, #13 |
| Bewerbung | Bild | #1, #5, #7, #10, #11 |
| Bewerbung-760 | Bild | wie Bewerbung |
| Bewerbung-Abschicken | Bild ohne offenes Formular, sonst Code | #9 |
| Bewerbung-Versendet | Bild nur als Lehrstelle, Stelle mit Code | #6 |
| Bewerbung-Lehrstelle | Bild | #5, #7, #8 |
| Bewerbung-Lehrstelle-Versendet | Bild | #6, #8 |
| Einrichtung-Wahl | Bild | #22 |
| Einrichtung | Bild | #22, Einwilligung absichtlich |
| Einrichtung-Erweiterung | Bild | #22 |
| Angaben | Bild | #27 |
| Dateien | Bild | #15 |
| Inhalte | Bild | #16 |
| Entwuerfe | Bild | #17 |
| Entwuerfe-Vergleich | Bild | #18 |
| Foto | Bild ohne Foto, Editor nur Code | #1, #19 |
| Fragen | Bild | #3, #20 |
| Einstellungen | Bild | #2, #21 |
| Erweiterung-Popups | Code | #1, #3 |
| Popup | Code, Baustein von Erweiterung-Popups | wie Erweiterung-Popups |
| Erweiterung-Formular | Code | #23, #24 |
| Erweiterung-Formular-Oben | Code | Leiste lässt sich nach oben setzen, sonst wie Erweiterung-Formular |
| Erweiterung-Leisten | Code | #25, #28 |
| Leiste | Code, Baustein von Erweiterung-Leisten | wie Erweiterung-Leisten |
| Erweiterung-JobRoom | Code | #28 |
| Erweiterung-Erlauben | Code | #26 |

## Nicht geprüft

- Die Erweiterung lief nicht: Popup, Formularleiste und Erlaubnis-Seite sind nur im Code verglichen.
- Nicht gerendert: laufende Suche, Editor auf der Seite Foto, Bewerbung mit offenem Formular, Dialog „Läuft schon eine Bewerbung“.
- Texte: Der Abgleich mit `texte.md` lief stichprobenweise, nicht Satz für Satz.

## Neugestaltung ab 0.3

Stand 12.11.2026, Item #258. Verglichen wurden die Quellen in `seiten/redesign/` mit `main`. Die Spec-Zeilen G54 bis G58 sind Entwürfe (Pull Request #202) und warten auf Andys Freigabe. Bis dahin wird keine dieser Änderungen umgesetzt. Die Umsetzung ist in die Items #259 bis #266 aufgeteilt.

| Bild | Heute in der App | Im Entwurf | Spec-Zeilen | Item |
| --- | --- | --- | --- | --- |
| Alle, Baustein Seitenleiste, A11 | Kopfzeile mit Übersicht, Stellen suchen, Meine Angaben und „Mehr“ | Seitenleiste mit Heute, Stellen, Bewerbungen, Meine Angaben, Lebenslauf und Dateien, Fragen an die KI und Einstellungen; unten KI-Budget und Zustand der Erweiterung, Marken nur, wo etwas wartet. Unter 900 px eine Kopfzeile mit vier Zielen und „Menü“ (A11). Das AS-Logo wandert unter Einstellungen, Über die App. | G54 (ersetzt den Ort in G4) | #259 |
| A1, A2 | Seite „Übersicht“ | „Heute“: nächster Schritt, Danach, Termine und Fristen, RAV-Hinweis nur bei RAV ja, Ihr Stand. Beim ersten Start vier Schritte bis zur ersten Bewerbung. | G55 (Name); G38 bleibt | #260 |
| A5 | Liste der Bewerbungen auf der Übersicht | Eigene Seite „Bewerbungen“ mit den Filtern, Verwerfen mehrerer, Stelle selbst erfassen und dem Durchgang durch gemerkte Stellen | G55 (Name); G27, G29, G38 bleiben | #261 |
| A3 | „Stellen suchen“ und Treffer, Firmen auf eigener Seite | „Stellen“ mit den Reitern Neu, Gemerkt, Verworfen und Firmen; pro Treffer „Bewerbung vorbereiten“ als Hauptknopf, „Merken“, „Verwerfen“; Alle prüfen und Sterne bleiben | G55 (Name), G56 (Firmen als Reiter), G58 (Hauptknopf); G22, G35, G44 bleiben | #262 |
| A4 | Suchbegriffe auf eigener Seite, Zeitfenster und weitere Seiten in den Einstellungen | Eine Seite „Suche einstellen“ in vier Karten und Erweitert, mit Zeitfenster und „Weitere Seiten durchsuchen“ | G57 (Umzug); G32, G45 bleiben | #263 |
| A9 | „Meine Dateien“ und „Foto“ getrennt, Rangliste der Lebensläufe | Eine Seite „Lebenslauf und Dateien“: Wahl zwischen dem Lebenslauf der App und einem eigenen PDF, Zeugnisse in einer Liste, mehrere Fotos mit einem aktiven, Einstieg zu früheren Fassungen | G55 (Name); G21 bleibt | #264 |
| A10 | Erweiterte Einstellungen als eine lange Seite | Abschnitte links: Zugang zur KI als Wahl, Budget, Sprache, Erweitert und Über die App mit dem Logo | G54 (Logo); G4, G41, G42, G46, G47, G51 bleiben | #265 |
| A6, A7, A8 | Bewerbung in Schritten, Meine Angaben | Gleiche Inhalte im neuen Rahmen; im Schritt Lebenslauf (A6) Inhalt und Aussehen getrennt | keine neue Zeile | mit #259, sonst später |

Die Anleitung, ihre Bilder in `docs/bilder/` und die Begleit-Items für die Webseite folgen mit #266, wenn die Seiten umgesetzt sind.
