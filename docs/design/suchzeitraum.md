# Suchzeitraum auf «Stellen suchen»

Gehört zu G32 (#208). Gewählt hat Andy am 10.11.2026 Option A, «Ausnahme: nur wenn es zählt», dazu die gemeinsame Karte «Zeitfenster der Suche» unter Erweiterte Einstellungen mit dem zugeklappten Stand pro Portal. Die Zeichenflächen mit allen drei Optionen liegen in Claude Design (Board «Ausnahme»). Umgesetzt in `bewerbungen/search_window.py` (Sätze und Regeln), `bewerbungen/routes_window.py` (Karte) und `seiten/suche-anzeige.js`.

## Wie die Suche rechnet

- **Zeitfenster:** Vorgabe 21 Tage, im Suchprofil 1 bis 60 Tage (`- Zeitfenster: 21 Tage` unter «Portale und Rhythmus»).
- **Pro Portal** sucht die App ab dem Tag seiner letzten erfolgreichen Suche, nie weiter zurück als das Zeitfenster. Ein Portal mit Problem, ein abgebrochenes oder ausgeschaltetes behält seine ältere Marke und holt nach.
- **Im Normalfall sind «letzte Suche» und «ab wann» derselbe Tag.** Sie gehen nur auseinander bei der ersten Suche, bei einem Portal, das nachholt, und nach einer Pause länger als das Zeitfenster.
- **Lehrstellen** (LENA, yousty) und «Weitere Seiten» suchen ohne Datum. Dort erscheint nie ein Ab-Datum, und die Karte fehlt.
- Ein Lauf speichert nur das **Datum**, keine Uhrzeit. Die Texte nennen «heute», «gestern» oder «am 24.10.2026».

## Was die Seite zeigt

Die Zeile unter dem Titel bleibt: «Letzte Suche gestern · 3 Portale · 23 Treffer, 12 neu». Eine zweite Zeile (`search__extra`, 14/20, `text-strong`) kommt nur, wenn das Ab-Datum etwas anderes sagt als die letzte Suche.

| Zustand | Zweite Zeile | Problemzeile |
| --- | --- | --- |
| Erste Suche | Die erste Suche nimmt Inserate der letzten 21 Tage. | – |
| Normal | – | – |
| Ein Portal holt nach | jobscout24 holt ab 03.11.2026 nach. | – |
| Portal mit Problem | – | … **Sobald die Suche dort wieder geht, holt sie die Inserate ab 06.11.2026 nach.** |
| Pause länger als das Zeitfenster | Die nächste Suche nimmt nur die letzten 14 Tage, ab 28.10.2026. [Zeitfenster ändern] | – |

Regeln für die zweite Zeile:

- Ein Portal erscheint, wenn sein Ab-Datum vor dem Tag der letzten Suche liegt.
- Zwei Portale mit demselben Datum: «jobscout24 und ictjobs holen ab 03.11.2026 nach.» Verschiedene Daten: «jobscout24 holt ab 03.11.2026 nach, ictjobs ab 06.11.2026.» Ab drei Portalen: «3 Portale holen nach, ab 03.11.2026.» (das früheste).
- Ein Portal ohne erfolgreiche Suche: «ictjobs sucht zum ersten Mal, die letzten 21 Tage.»
- Holt ein Portal mit Problem nach, steht der Satz in seiner Problemzeile. Liegt seine letzte erfolgreiche Suche weiter zurück als das Zeitfenster oder gab es keine: «… holt sie die Inserate der letzten 21 Tage nach.» Der Satz verspricht nur, was stimmt: «sobald die Suche dort wieder geht», nicht «die nächste Suche».
- Ist die letzte Suche älter als das Zeitfenster, zählt diese Lücke vor dem Nachholen. «Zeitfenster ändern» erscheint nur, wenn ein grösseres Fenster (höchstens 60 Tage) die Lücke schliessen würde. Es ist ein Link auf `/einstellungen#zeitfenster` und setzt den Fokus auf das Feld.
- Die zweite Zeile ist gewöhnlicher Text in der Lesereihenfolge, kein `role=status`; nach einem Lauf lädt die Seite neu.

Bei 760 px bricht die Zeile um; «Zeitfenster ändern» bricht nicht in sich (`white-space: nowrap`).

## Karte «Zeitfenster der Suche»

Unter Erweiterte Einstellungen, vor «Eigener API-Schlüssel» (dort steht «Weitere Seiten durchsuchen»), mit Eintrag im Seitenmenü. Nur bei der Stellensuche.

| Teil | Text |
| --- | --- |
| Titel | Zeitfenster der Suche |
| Erklärung | So weit geht die erste Suche zurück, und die Suche nach einer längeren Pause. Sonst sucht jedes Portal nur, was seit seiner letzten Suche dazugekommen ist. |
| Feld | Inserate der letzten · 7 Tage · 14 Tage · 21 Tage (Vorgabe) · 30 Tage · 45 Tage · 60 Tage. Ein anderer Wert aus dem Suchprofil erscheint als eigene Wahl. |
| Nach dem Ändern | Gespeichert. Gilt ab der nächsten Suche. |
| Fehler | Nicht gespeichert. und der Grund |
| Aufklapper «Stand der Portale» | job-room: zuletzt gestern · nächste Suche ab 09.11.2026 · jobs.ch: Problem bei der letzten Suche · nächste Suche ab 06.11.2026 · ictjobs: noch nie gesucht · nächste Suche ab 21.10.2026 |

Die Karte schreibt die Zeile `- Zeitfenster: … Tage` ins Suchprofil, mit Entwurf davor und danach: Die Zeile wird ersetzt, wo sie steht, sonst in «Portale und Rhythmus» ergänzt.

## Nicht gewählt

- **B, Vorschau beim Knopf:** immer ein Satz unter «Jetzt suchen», ab wann gesucht wird. Im Normalfall zweimal derselbe Tag auf engem Raum, und ein Datum, das immer dasteht, lädt zum Ändern ein.
- **C, Stand der Portale:** beide Daten immer in der Zeile, dazu eine Tabelle pro Portal. Zu lang für einen Blick; den Stand pro Portal gibt es stattdessen zugeklappt in der Karte.

## Offen

- Ein Hinweis eines Portals (etwa «12 weitere neue Inserate kommen bei der nächsten Suche dran.») gilt heute wie ein Fehler als Problem. Die Zusammenfassung pro Portal unterscheidet das noch nicht.
- Nach einem grösseren Zeitfenster sucht ein Portal nach regelmässigen Läufen trotzdem nur seit seiner letzten Suche. Ein einmaliges «ganzes Zeitfenster durchsuchen» wäre eine neue Spec-Zeile zu G32.
