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

## K · Constraints
