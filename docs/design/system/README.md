# Design System Bewerbungsassistent

Ein ruhiger, verlässlicher Begleiter durch eine belastende Lebensphase, kein Verwaltungswerkzeug. Jede Seite beantwortet zuerst eine Frage: **Was ist mein nächster Schritt?** Dieses System gilt für die App, für Meine Angaben mit der Einstiegsvorlage und für die Browser-Erweiterung. Die drei bisherigen Erscheinungsbilder (Schieferblau in `stil.css`, Grün mit Pillen in `onboarding/src/style.css`, GitHub-Blau im Popup) gehen darin auf.

## Grundsätze

1. **Ein nächster Schritt pro Ansicht.** Übersicht und Bewerbung zeigen oben eine `NextStep`-Karte mit genau einem Hauptknopf (`btn--primary`). Alles andere ist Zweitknopf (`btn`) oder leiser Knopf (`btn--quiet`).
2. **Die Person entscheidet und schickt ab.** Texte und Knöpfe sagen das, wo es zählt: „Abschicken bleibt bei Ihnen.“ Kein Knopf der App heisst „Absenden“ oder „Bewerbung abschicken“.
3. **Die KI schätzt ein.** Jede KI-Ausgabe steht in einer `AiResult`-Karte mit dem Satz „Eine Einschätzung, kein Urteil. Die KI kann sich irren.“, dem Modell und den Kosten in `caption`. Noten heissen Einschätzung, Anschreiben heissen Entwurf.
4. **Nichts geht verloren.** Wo etwas überschrieben wird, sagt der Text, wo die alte Fassung bleibt („Die jetzige Fassung bleibt unter Entwürfe erhalten.“). Darum braucht Überschreiben keinen roten Knopf.
5. **Die Daten bleiben auf dem Computer.** Ein Satz am Ort der Handlung genügt, etwa unter „Aus Unterlagen vorbefüllen“: „Ihr Name, Ihre Adresse und Ihre Kontakte werden ersetzt, bevor der Text zur KI geht. Bilder und PDFs bleiben auf Ihrem Computer.“ Keine Schlösser, keine Warnfarbe.
6. **Kosten sichtbar, nicht laut.** Kosten stehen in `caption` und `text-muted` neben dem Knopf oder im Fuss der KI-Karte, nie im Knopftext.

## Sprache und Ton

- Schweizer Schreibweise: ss statt ß („heisst“, „Strasse“). Daten `05.11.2026`, Noten mit Punkt `4.5`, Geld `CHF 0.02`. Nie `4,5`.
- **Stellen: Sie. Lehrstellen: du.** Wo es geht, neutral formulieren, damit nur ein Text nötig ist: „Anschreiben lesen“ statt „Lesen Sie das Anschreiben“.
- Kurz, konkret, in ganzen Sätzen. Sagen, was geschieht und was die Person tun kann.
- Knöpfe nennen die Handlung: „Unterlagen erstellen“, „Anschreiben lesen“, „Im Job-Room eintragen“. Nie „OK“, „Senden“, „Weiter“ ohne Ziel.
- Fehler nennen den Ausweg: „Die KI ist gerade ausgelastet. Bitte in 30 Sekunden nochmals versuchen.“
- Keine Technik in Texten: keine Dateinamen, kein YAML, Git, ID, Skill, Firmen-Schlüssel, Pseudonymisierung. Erlaubt: Datenordner, Entwurf, Fassung, Vorlage.
- Ermutigen ohne zu beschönigen. Absage: „Absage erhalten. Das gehört dazu. Ihre Unterlagen für diese Stelle bleiben gespeichert.“ Keine Ausrufezeichen, keine Emojis.
- Hilfetexte stehen nicht oben auf jeder Seite. Ein Satz beim Feld (`field__hint`) oder ein aufklappbares „Wie funktioniert das?“.

## Farbe

- Eine Akzentfarbe: `accent` (Schieferblau `#38495d`, dunkel `#c9d4e2`). Sie markiert den Hauptknopf, den aktuellen Navigationspunkt, Fortschritt und Notenbalken. Pro Bereich höchstens eine `accent`-Fläche.
- Seite auf `bg`, Arbeitsflächen (Karten, Tabellen, Navigation, Dialoge) auf `surface` mit Rand `line`. Nebenflächen (Inseratstext, Details, Kopierwerte) auf `surface-subtle`.
- `accent-subtle` hat genau zwei Bedeutungen: „das ist jetzt dran“ (NextStep, aktueller Schritt, gewählte Zeile) und „läuft“ (Status Beworben).
- Grün steigert sich mit dem Stand: Gespräch hell (`success-bg`), Zusage gefüllt (`success`).
- Text: `text-strong` für Titel, Etiketten, Zahlen; `text` für Fliesstext; `text-muted` für Nebentext. Alle drei sind auf `bg`, `surface`, `surface-subtle` und `accent-subtle` in beiden Themen lesbar (mindestens 4.8:1).
- Text auf `accent` ist immer `on-accent`, nie festes Weiss.
- Signale: `warning` auf `warning-bg` für „bald zu tun“, `danger` auf `danger-bg` für Fehler und Unumkehrbares, `success` auf `success-bg` für erledigt und Zusage. `success` und `danger` sind gleich hell: Sie tragen immer ein Wort („In Ordnung“, „Fehler“), nie nur Farbe.
- **Absagen sind nicht rot.** Absage, Verworfen, Zurückgezogen sind leise (`text-muted`, hohler Punkt), nicht `danger`.
- Felder, Kontrollkästchen und Zweitknöpfe haben den Rand `line-strong` (3:1). `line` nur für Trennlinien.
- Hell und dunkel folgen der Systemeinstellung. In der App wird das zweite Thema über `@media (prefers-color-scheme: dark)` gesetzt; die Werte kommen aus dem Thema `dark`.

## Schrift

- Eine Familie: **DM Sans** in 400, 400 kursiv, 500 und 700, als Dateien in `fonts/` (dieselben wie `lebenslauf/fonts/`, OFL). Die App liefert sie selbst aus, keine Schriften vom CDN (CSP). Rückfall `system-ui`.
- Fliesstext `body` 16/24. Tabellen und Meldungen `body-sm` 14/20. Etiketten und Spaltenköpfe `label` 14/20 in 500, ohne Grossbuchstaben. Kleinste Grösse `caption` 13/18.
- Titel: `title` (22) als Seitentitel, `section` (18) für Abschnitte, `subsection` (16) darunter. `title-lg` (28) nur auf Übersicht und Einrichtung.
- Zahlen in Tabellen, Noten und Kosten mit tabellarischen Ziffern (Klasse `num`). Note in `grade` (20, 700).
- `code` (Monospace) nur im Bereich für Geübte und in kopierbaren Werten.

## Abstände, Raster, Formen

- Abstände nur aus `space-1` (4) bis `space-7` (48). Felder in einer Gruppe `space-3`, Abschnitte `space-6`, Innenabstand von Karten `space-4`, von Dialogen und NextStep `space-5`.
- Breiten: `width-content` (1180) für Übersicht und Listen, `width-reading` (760) für einspaltige Seiten (Bewerbung, Einrichtung, Meine Angaben). 760 ist zugleich der schmale Entwurf: darunter werden Tabellen zu Zeilenkarten (`DataTable`), Schritte senkrecht (`steps--vertical`).
- Radien: `radius-md` (6) für Knöpfe, Felder, Meldungen; `radius-lg` (10) für Karten, Dialoge, Menü, Popup; `radius-full` nur für Statusmarken und Schrittpunkte. Keine Pillen-Knöpfe.
- Schatten nur für das, was schwebt: `shadow-menu`, `shadow-dialog`, `shadow-bar`. Karten haben Rand statt Schatten.
- Mindesthöhe von Knöpfen und Feldern `control-height` (40). `btn--sm` (32) nur in Tabellenzeilen und der Formularleiste.

## Rückmeldung und Warten

- Meldungen erscheinen **dort, wo gehandelt wurde**: die `status-line` direkt unter dem Knopf, mit `aria-live="polite"`. Banner (`notice` über dem Inhalt) nur für Dinge, die die ganze App betreffen: fehlende Erweiterung, neue Version, Erinnerung an Sicherung oder RAV.
- Ein deaktivierter Knopf sagt, warum (`btn-reason`): „Erst eine Lebenslauf-Variante wählen.“ Sonst den Knopf weglassen.
- Bestätigung mit `Dialog` (natives `<dialog>`), nicht mehr durch Textwechsel im Knopf. Der Dialog-Titel ist eine Frage, die Knöpfe nennen die Handlung („Ersetzen“ / „Abbrechen“).
- Warten (10 bis 60 Sekunden pro KI-Antwort, Minuten pro Suchlauf) zeigt `Progress`: was gerade geschieht, wie weit („3 von 10“), wie lange es meist dauert, und „Anhalten“ bei Läufen. Keine Restzeit erfinden.

## Noten

- Schweizer Skala: 6 beste, 1 schlechteste, halbe Noten möglich. Die Note erscheint immer mit Balken aus sechs Feldern und einem Wort: ab 5.5 „passt sehr gut“, 4.5–5 „passt gut“, 4 „passt knapp“, unter 4 „passt wenig“ (`Grade`).
- Neben jeder Notenspalte ein aufklappbares „Wie lese ich die Note?“ (`grade-help`) für Lesende ohne Schweizer Schulerfahrung.
- Unsichere Noten: gestrichelter Balken und „· unsicher“, keine Fragezeichen allein.
- Noten sind nie rot oder grün. Sie sind Einschätzung, kein Urteil.

## Bewerbungsstand

| Status | Darstellung | Bedeutung |
| --- | --- | --- |
| Gemerkt | neutral | gesehen, noch nichts zu tun |
| Bewerben | `accent`, gefüllt | jetzt dran |
| Beworben | `accent-subtle` | läuft, warten auf Antwort |
| Gespräch | `success` auf `success-bg`, Rand `success` | ein grosser Schritt weiter, Gespräch vorbereiten |
| Zusage | gefüllt `success`, Text `on-success` | Ziel erreicht |
| Absage | leise, hohler Punkt | abgeschlossen |
| Verworfen, Zurückgezogen | leise, gestrichelt | selbst beendet |

## Browser-Erweiterung

- Popup (`width-popup`, 320) und Formularleiste nutzen dieselben Tokens. Die Formularleiste liegt in einem Shadow DOM auf fremden Seiten und kann `tokens.css` nicht laden: Sie bekommt die aufgelösten Werte als eigenes Stylesheet.
- Formularleiste auf `inverse` mit `on-inverse`, **immer dunkel**, auch wenn das System hell oder dunkel eingestellt ist: so ist sie auf jeder fremden Seite gleich erkennbar. Das Popup folgt dagegen der Systemeinstellung. Die Leiste verdeckt nichts (eigener Platz am unteren Rand, auf Wunsch oben mit `form-bar--top` und `shadow-bar-top`) und schickt nichts ab. Ihr erster Satz zählt, ihr zweiter heisst immer „Abschicken bleibt bei Ihnen.“ (Lehrstelle: „bei dir“).
- Feldmarkierungen tragen Farbe **und** Linienart **und** Etikett: ausgefüllt `mark-filled` durchgezogen, offen `mark-open` gestrichelt, selbst bestätigen `mark-consent` doppelt, Entwurf der KI `mark-ai` gepunktet. Ein Halo `mark-halo` hält sie auf dunklen Seiten sichtbar.

## Zugänglichkeit

- WCAG 2.1 AA in beiden Themen. Text mindestens 4.5:1 auf seinen Flächen, Ränder von Bedienelementen und Fokusring mindestens 3:1.
- Fokus: `outline: 2px solid var(--focus)` mit 2px Abstand, auf jeder Fläche über 7:1. Nie entfernen.
- Alles mit Tastatur: Menü als `<details>`, Dialoge als `<dialog>` mit Fokus auf dem sicheren Knopf, Tabellenköpfe zum Sortieren als `<button>`.
- Ausnahme mit Begründung: `mark-open` erreicht auf Weiss nur 3.1:1, `mark-consent` und `mark-ai` auf dunklen Seiten unter 3:1. Die Werte bleiben wie in `erweiterung/form/filler.js`; Linienart, Etikett und Halo tragen die Bedeutung.

## Ikonografie

- Es gibt noch keine Symbolsammlung und kein Logo, nur den Schriftzug „Bewerbungsassistent“ in DM Sans 700. In der App steht der Schriftzug in `text-strong`, nie in einer Farbe.
- Bedeutung tragen Wörter, nicht Symbole. Formen aus CSS (Punkt der Statusmarke, Haken im Schritt) sind erlaubt. Keine Emojis, keine Sterne als Schmuck (die Sterne der Berufswahl bei Lehrstellen sind eine Eingabe und bleiben).
- Das Symbol der Erweiterung (`assets/Symbole/`) ist nur Programmsymbol im Browser, kein Markenzeichen.

## Umsetzung

- Einfaches HTML, CSS und JavaScript, ohne Framework und Build. Die Bausteine sind CSS-Klassen in `components/bundle.css`; jedes `preview.html` zeigt das Markup. Klassennamen englisch (neuer Code), `data-status`-Werte deutsch wie im Register.
- Strenge CSP: keine Inline-Skripte, keine fremden Server. Schriften aus `fonts/` mit der App ausliefern.
