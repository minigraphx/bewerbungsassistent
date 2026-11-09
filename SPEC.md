# bewerbungsassistent spec

Every requirement is a row with an id. Agents build against approved rows; commits cite the ids they serve. `pullboard spec check` lints this file.

Statuses: approved = decided · draft = proposed · pending = open question · fact = true today · wont = won't build, decided and kept · retired = no longer applies, kept. Ids are permanent: never delete or renumber a row. Tiers: must · aim.

Write each requirement as one row under its section, in this format. The fence keeps the example out of the spec, so no placeholder id is ever committed; your own rows go below, outside it.

```text
- G1 [draft, must] The first thing the client needs, in one line. | gate: pytest
- K1 [draft, must] A constraint, e.g. runs locally with no account. | gate: review
```

## G · Goals: what the client asked for
- G3 [approved, must] In Edge führt der Einrichtungsschritt Erweiterung zum Store-Eintrag; das Laden von Hand bleibt als zweiter Weg. | gate: review
- G4 [approved, must] Das AS-Logo erscheint einfarbig unter Mehr, Über die App; Schriftzug und Programmsymbol bleiben. | gate: review
- G5 [approved, must] Die App läuft unter Linux als AppImage; zugesagt ist Ubuntu LTS. | gate: review
- G6 [approved, must] Die Windows-App gibt es als MSIX-Paket für den Microsoft Store. | gate: review
- G7 [approved, must] Die Webseite stellt die App vor, führt zum Download und zeigt die Anleitung; Sprache vorerst Deutsch. | gate: review
- G8 [approved, must] Gibt es beim Start der App ein Update, erscheint es zuerst in einem Dialog, der bis Installieren oder Später offen bleibt; nach Später fragt die App beim nächsten Start wieder. | gate: review
- G9 [approved, must] In Chrome führt der Einrichtungsschritt Erweiterung zum Eintrag im Chrome Web Store; das Laden von Hand bleibt als zweiter Weg. | gate: review
- G10 [approved, must] Die Oberfläche von App und Erweiterung gibt es auf Deutsch, Französisch und Englisch; die Person wählt die Sprache in den Einstellungen. Italienisch und Spanisch folgen später. | gate: review
- G11 [approved, must] Die KI schreibt der Person in der Sprache der Oberfläche; Inserate und Portale bleiben in ihrer Originalsprache. | gate: review
- G12 [approved, must] Lebenslauf und Anschreiben lassen sich unabhängig von der Sprache der Oberfläche in jeder Bewerbungssprache erstellen; die Person wählt ihre Bewerbungssprachen, die App schlägt sie aus dem Lebenslauf vor. | gate: review
- G13 [approved, must] Webseite und Anleitung gibt es auf Deutsch, Französisch und Englisch, mit Wahl der Sprache auf der Seite; das ersetzt den Teil von G7, nach dem die Webseite vorerst Deutsch ist. | gate: review
- G14 [approved, must] Wo die Person Name, Adresse und Kontaktdaten erfasst, und vor der Einwilligung, erklärt die App kurz, dass sie diese Angaben vor dem Senden an die KI durch Platzhalter ersetzt, welche Angaben nicht ersetzt werden, und dass sie nur ersetzen kann, was korrekt eingetragen ist. | gate: review
- G15 [approved, must] Die Person kann vor einem KI-Aufruf sehen, welcher Text mit Platzhaltern an die KI geht. | gate: review
- G16 [approved, must] Neben den bestehenden Designs gibt es ein Design als Bewerbungsdossier: Titelseite, Anschreiben und Lebenslauf in einem gestalteten PDF. Aus demselben Design entstehen Lebenslauf und Anschreiben auch als einzelne Dateien für Portale, die getrennte Uploads verlangen. Bewertungen wie Balken oder Ringe für Können und Programme zeigt es nur, wenn die Person sie angegeben hat. | gate: review
- G17 [approved, must] Bei einer Bewerbung kann die Person einen Lebenslauf nicht nur wählen, sondern auch erstellen: Inhalt aus Meine Angaben, für die Stelle zugeschnitten (Auswahl, Reihenfolge, Kurzprofil), und Layout (Design) getrennt davon wählbar. Der neue Lebenslauf steht danach wie eine Variante zur Wahl. | gate: review
- G18 [approved, must] Im Dossier wählt die Person das Monogramm aus mehreren Varianten aus ihren Initialen oder lädt ein eigenes Logo hoch, und sie wählt die Akzentfarbe; voreingestellt ist eine Akzentfarbe passend zur Hauptfarbe des Designs. | gate: review
- G19 [approved, must] Begrüssung und Dank im Dossier entwirft die KI aus den Bausteinen der Person; die Person passt die Texte an wie bei den anderen Vorlagen, und ohne Text entfällt die Seite. | gate: review
- G20 [approved, must] Die Person kann in der Oberfläche für Fähigkeiten, Sprachen und Programme eine Stufe angeben oder offen lassen; ohne Angaben bleibt die Darstellung einheitlich ohne Bewertungen. | gate: review
- G21 [approved, must] Auf der Seite Foto kann die Person jederzeit ein Foto hochladen, auch wenn sie bei der Einrichtung keines angegeben hat. Sie kann mehrere Fotos speichern und eines als aktiv kennzeichnen; neu erstellte Unterlagen nutzen das aktive Foto, bestehende Versionen bleiben unverändert. | gate: review
- G22 [draft, must] Die Person kann jedem gefundenen Treffer eine eigene Bewertung von 1 bis 5 Sternen geben, ändern oder wieder entfernen. Die Trefferliste lässt sich nach eigener Bewertung, Note der KI oder Datum sortieren; die Wahl bleibt erhalten. Die eigene Bewertung geht nie an die KI und ändert deren Note nicht. | gate: review
- G23 [approved, must] Die Seite Meine Angaben lädt einen bestehenden Lebenslauf (cv.yaml) vollständig ins Formular. Beim Speichern führt sie die Angaben mit der Datei zusammen, statt sie neu zu schreiben: Felder und Abschnitte, die das Formular nicht kennt, bleiben unverändert, das Foto (x-image) wird nie überschrieben, und ein ohne Änderung gespeicherter Lebenslauf ergibt dieselben Unterlagen wie vorher. | gate: review
- G24 [approved, must] Die Person kann Stellen, Highlights, Fähigkeiten, Projekten, Lehrtätigkeiten und Zertifikaten auf der Seite Meine Angaben wahlweise Tags geben. Vorgeschlagen werden die Tags, die schon in cv.yaml, varianten.yaml und den Stellen unter jobs/ stehen; neue Tags kann sie frei eingeben. | gate: review
- G25 [approved, must] Die Seite Meine Angaben kennt auch Projekte (mit Gruppe Haupt- oder weitere Projekte), Lehrtätigkeiten (mit Anzeige), einen Freitext bei Ausbildungen und Zertifikaten sowie eine eigene Webseite der Person. | gate: review
- G26 [approved, must] Gibt es Suchprofil, Stilprofil oder Bausteine schon im Datenordner, wählt die Person auf der Seite Meine Angaben pro Datei, ob sie ersetzt wird; vorgewählt ist Behalten. Vor dem Ersetzen zeigt die Seite die Unterschiede zwischen altem und neuem Stand. | gate: review
- G27 [approved, must] In der Liste der Bewerbungen filtert die Person nach Stand, jeweils mit Anzahl: Gemerkt (Gemerkt, Bewerben), Beworben (Beworben, Gespräch), Abgeschlossen (Absage, Zusage, Verworfen, Zurückgezogen) und Alle. Eine Absage zählt immer als abgeschlossen; ein noch offener Eintrag im Job-Room steht weiter unter Das steht an. Die Wahl bleibt erhalten. | gate: review
- G28 [approved, must] Die Liste der Bewerbungen lässt sich auch nach dem Datum der Erfassung sortieren, in beide Richtungen; Einträge ohne Datum stehen am Ende. | gate: review
- G29 [approved, must] Die Person kann den Stand einer Bewerbung jederzeit ändern, auch nach Ablauf der Frist: auf der Seite der Bewerbung mit einem sichtbaren Knopf (Verwerfen vor dem Versand, Zurückziehen danach) und in der Übersicht für eine oder mehrere ausgewählte Bewerbungen in einem Schritt. | gate: review

## K · Constraints
