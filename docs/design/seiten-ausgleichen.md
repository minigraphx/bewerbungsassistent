# Seiten ausgleichen

Gehört zu #239. Vorschlag zur Wahl durch Andy, entschieden am 15.11.2026 (Abschnitt «Entscheid»). Die Zeichenflächen liegen in Claude Design (Original privat: [Zeichenfläche](https://claude.ai/artifact/NvC1i9e973R7Kn74ir4bvc), Designsystem Bewerbungsassistent): ein Board mit dem heutigen Stand, zwei Boards pro Option. Sie bauen auf A6 und A7 der Neugestaltung auf (`README.md`, Abschnitt «Neugestaltung der App ab 0.3»). Alle Personen, Firmen und Daten sind erfunden.

**Frage:** Was kann jedes Design tun, damit seine Seiten ausgeglichen sind (enger setzen, weiter setzen, Inhalt verschieben oder kürzen)? Was sieht die Person davon, was wählt sie, und was gehört unter «Erweitert»?

**Kurz:** Drei Optionen. A lässt die App wie heute selbst ausgleichen und macht aus dem Hinweis über der Grenze eine Wahl mit einem Klick. B zeigt nach dem Erstellen mehrere Fassungen als Seitenbilder zur Wahl. C zeigt die Länge schon beim Zusammenstellen von Lebenslauf und Anschreiben. **Empfehlung: A.**

## Befund heute

Gemessen auf `main` vom 14.11.2026 mit den erfundenen Lebensläufen und Anschreiben aus `lebenslauf/tests/page_fill_samples.py`: Lebensläufe mit 0 bis 60 Zeilen Berufserfahrung über dem Beispiel, Anschreiben mit 0 bis 13 zusätzlichen Absätzen, in allen fünf Designs. Jedes Dokument einmal so gebaut, wie das Design es zeichnet, und einmal mit dem Ausgleich von #236, gemessen mit `pdftotext -bbox-layout` und `bewerbungen/layout_check.py`. Dazu die App mit einem erfundenen Datenordner bei 1280 und 375 px.

| | Dokumente |
| --- | --- |
| gebaut und gemessen | 118 |
| fast leere letzte Seite, wie gezeichnet | 34 |
| fast leere letzte Seite, nach dem Ausgleich | 0 (letzte Seite mindestens 42 % voll) |
| enger gesetzt | 24 (bis Stufe 5) |
| weiter gesetzt | 19 (bis Stufe 4) |
| nach dem Ausgleich über der Seitengrenze | 50 |

| Design | Lebenslauf über 2 Seiten ab | durch Enger auf 2 Seiten gebracht | Anschreiben über 1 Seite ab |
| --- | --- | --- | --- |
| Zweispaltig | 36 Zeilen | 28 und 32 Zeilen | 9 Absätzen |
| Einspaltig | nie bis 60 Zeilen | nicht nötig | 9 Absätzen |
| Siegel | 32 Zeilen | 24 und 28 Zeilen | 7 Absätzen |
| Raster | 28 Zeilen | 20 und 24 Zeilen | 7 Absätzen |
| Register | 32 Zeilen | 20 bis 28 Zeilen | 7 Absätzen |

- Der Ausgleich wirkt: Keine gebaute Seite ist mehr fast leer, und kein Inhalt fällt weg.
- Die Person sieht davon nichts. Weder steht irgendwo, dass enger gesetzt wurde (bis zu 40 % kleinere Abstände), noch dass dasselbe in einem anderen Design auf weniger Seiten käme.
- Reicht es nicht, steht unter «Unterlagen erstellen» ein Hinweis von fünf Zeilen (bei 375 px zehn): «Lebenslauf: 3 Seiten, erlaubt sind höchstens 2. Auch enger gesetzt passt er nicht. Kürzen lässt sich: …» (seit #333: «Auch so eng wie möglich gesetzt …»). Der einzige Knopf ist «So lassen». Kürzen muss die Person in Meine Angaben oder im Schritt Lebenslauf, drei Seiten erlaubt sie unter Einstellungen, Erweitert.
- Ein Anschreiben über einer Seite setzt die App weiter, damit die zweite Seite gefüllt aussieht (Stufe −3 bis −4). Die Prüfung nennt es trotzdem als Fehler.
- Gut und zu behalten: Der Ausgleich braucht keine Einstellung (G41), Inhalt fällt nur durch die Person weg (G49), und die Kürzungen nennen konkrete Stationen.

## Hebel pro Design

| Design | Enger, weiter | Verschieben | Weglassen ohne Kürzen |
| --- | --- | --- | --- |
| Alle | Abstände, Zeilenhöhe, Schrift bis 10 pt (G53); weiter nur Abstände | – | Foto (G62), drei Seiten erlauben (G51) |
| Zweispaltig | ja | zwei Spalten laufen getrennt; ab Seite 2 wechselt die Hauptspalte nach links | – |
| Einspaltig | ja | – | – |
| Siegel | ja | – | «Kurz vorgestellt» und «Danke» ohne Text (G19) |
| Raster | ja | – | Zeitachse (`--ohne-zeitachse`, in der App nicht wählbar), «Auf einen Blick», Rückseite |
| Register | ja | – | Seiten Beilagen und Referenzen |

Kürzen (`lebenslauf/cuts.py`): Stichpunkte der Stationen mit den meisten, ältere zuerst, dann die Abschnitte Weitere Projekte, Interessen, Engagement, Auszeichnungen; beim Anschreiben der längste Absatz. Verschieben bringt wenig: Die Designs halten Überschrift und ersten Eintrag schon zusammen (G50), und eine andere Reihenfolge ändert die Aussage des Lebenslaufs. Keine Option verschiebt darum von selbst.

## Option A · Automatisch, Kürzen mit einem Klick

Boards A1 und A2.

- **Prüfen (A1):** Jede Dokumentkachel sagt in einem Wort, was die App getan hat: «1 Seite · etwas enger gesetzt», «3 Seiten · so eng wie möglich». Über der Grenze wird der Hinweis zur Wahl: die Kürzungen aus `cuts.py` zum Anhaken, die erste vorgewählt, mit «Gekürzt neu erstellen» als Hauptknopf, «Drei Seiten für diese Bewerbung» und «So lassen». Der Satz darunter: «Meine Angaben bleiben, wie sie sind. Weggelassenes holen Sie im Schritt Lebenslauf zurück.»
- **Anschreiben zu lang:** Fehler mit «Im Anschreiben kürzen»; der Knopf führt in den Schritt Anschreiben, der längste Absatz ist markiert.
- **Erweitert (A2, Einstellungen):** Länge des Lebenslaufs (gibt es, G51) und neu «Wenn eine Seite fast leer bliebe»: Automatisch (Vorgabe), Lieber eine Seite weniger, Lieber mit mehr Luft. Beide Wahlen halten G49 ein; «nie ausgleichen» gibt es nicht.
- **Bauen:** drei Items.
  1. Kürzungen anhaken und anwenden: Der Zuschnitt der Bewerbung (`jobs/<variante>.yaml`) bekommt Stichpunkte pro Station und verborgene Abschnitte; `lebenslauf/tailor.py` kennt heute nur `max_highlights` für alle Stationen und braucht eine Grenze pro Station. Dazu «Drei Seiten für diese Bewerbung» im Register, vor der Einstellung von G51.
  2. Kachel nennt den Ausgleich: Der Bau gibt die gewählte Stufe zurück (`dossier.py` hat sie schon in `Result.inputs`, `build.py` und `anschreiben.py` noch nicht).
  3. Richtung des Ausgleichs unter Erweitert: eine Vorliebe für `page_fill.choose`, gespeichert wie die Seitengrenze in `unterlagen.yaml`.
- **Spec:** braucht eine neue Zeile für 1 und 2 (Kürzen und drei Seiten pro Bewerbung, Anzeige des Ausgleichs) und eine für 3. G49, G51, G52 und G53 bleiben.

## Option B · Fassungen zur Wahl

Boards B1 und B2.

- **Prüfen (B1):** Musste die App ausgleichen, baut sie zwei bis vier Fassungen und zeigt sie als Seitenbilder mit der Füllung jeder Seite: Vorschlag der App, mit mehr Luft, in einem anderen Design, gekürzt. Vorgewählt ist der Vorschlag; «Diese Fassung verwenden». Sonst bleibt der Schritt wie A7.
- **Erweitert (B2, im Ergebnis):** «Satz von Hand» pro Dokument, ein Regler von enger bis weiter mit Seitenzahl und Füllung, dazu die Hebel des Designs (bei Raster Zeitachse und «Auf einen Blick»). Gilt nur für diese Bewerbung.
- **Bauen:** vier Items: Fassungen bauen und als Bilder zeigen (Typst rendert PNG), Wahl speichern, Regler, Hebel pro Design.
- **Spec:** zwei neue Zeilen (Fassungen zur Wahl, Satz von Hand pro Bewerbung).
- **Schwäche:** Jedes Erstellen dauert zwei- bis viermal so lang, und die Person muss wählen, wo heute nichts zu tun ist. Das widerspricht «schnell nutzbar» (G41) für alle, die wenig Zeit haben.

## Option C · Schon beim Zusammenstellen

Boards C1 und C2.

- **Schritt Lebenslauf (C1):** Neben der Wahl der Stationen eine Anzeige «Länge» mit Seitenbildern; jede Station nennt ihre Zeilen. Über der Grenze: «3 Seiten, erlaubt sind 2. Etwa 9 Zeilen zu viel, auch enger gesetzt.» und ein Vorschlag mit «So übernehmen». Gemessen ohne PDF über die Marken der Seitenfüllung (`typst query`).
- **Schritt Anschreiben (C2):** Dieselbe Anzeige beim Entwurf; der längste Absatz ist markiert. Die App kürzt nicht selbst und schickt dafür nichts an die KI.
- **Erweitert:** nichts Neues.
- **Bauen:** drei Items: Messung ohne PDF als Route, Anzeige im Schritt Lebenslauf, Anzeige im Schritt Anschreiben.
- **Spec:** eine neue Zeile (Länge beim Zusammenstellen anzeigen).
- **Schwäche:** Hilft nur, wo die Person zuschneidet. Ein Lebenslauf ohne Zuschnitt und ein Dossier kommen weiter erst in der Prüfung an die Grenze; dort bleibt der Hinweis von heute.

## Empfehlung

**A.** Die Person mit wenig Zeit muss nichts tun, solange der Ausgleich reicht, und das ist bei den gemessenen Längen meistens so. Wo er nicht reicht, entscheidet sie dort, wo die Meldung steht, mit einem Klick und ohne Meine Angaben zu ändern. Die Kachel macht sichtbar, was die App getan hat, ohne eine Wahl zu verlangen. B gibt mehr Kontrolle, kostet aber bei jedem Erstellen Zeit und eine Entscheidung. C ist ein guter Zusatz für später, ersetzt die Wahl in der Prüfung aber nicht.

## Offen

- Unabhängig von der Option: Soll ein Anschreiben über einer Seite weiter weiter gesetzt werden? Heute füllt die App die zweite Seite, die Prüfung nennt sie trotzdem als Fehler. Vorschlag: so eng wie möglich lassen, damit der Fehler sichtbar bleibt. Das wäre eine Änderung an `page_fill.choose` und braucht Andys Entscheid zu G49 und G51.
- Ob «Lieber eine Seite weniger» und «Lieber mit mehr Luft» unter Erweitert nötig sind, zeigt sich erst mit echten Lebensläufen im Pilot. Option A geht auch ohne Item 3.
- Die Anleitung (`docs/installation.md`) und ihre Bilder ändern sich erst mit dem Bau; dann braucht es ein Begleit-Item für die Webseite.

## Entscheid

Andy hat am 15.11.2026 **Option A** gewählt. Dazu die offene Frage zum Anschreiben: Ein Anschreiben über einer Seite setzt die App eng und nie weiter, damit die Person sieht, wie wenig zu viel ist.

Festgehalten in den freigegebenen Spec-Zeilen G92, G93 und G94 (`SPEC.md`), umgesetzt in drei Items:

- **#323:** Kürzungen zum Anhaken oder drei Seiten erlauben, beides nur für diese Bewerbung (G92).
- **#324:** Jedes Dokument nennt seine Seitenzahl und, nur wenn die App den Satz verändert hat, kurz wie (G93).
- **#325:** Anschreiben über einer Seite eng gesetzt; die Prüfung nennt die Zeilen zu viel, mit «Im Anschreiben kürzen» und «So lassen» (G94).

Die Richtung des Ausgleichs unter Erweitert (Bauen, Punkt 3) ist nicht beauftragt; Option A geht auch ohne sie.
