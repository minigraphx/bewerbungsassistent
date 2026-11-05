# FieldMark

Markierung der Felder, die die Erweiterung auf fremden Bewerbungsformularen ausgefüllt oder offen gelassen hat.

**Vier Arten**, je mit Farbe, Linienart und Etikett, damit Farbe nie allein steht:
- `filled`: ausgefüllt, `mark-filled`, durchgezogen.
- `open`: offen, `mark-open`, gestrichelt. Die Person füllt aus.
- `consent`: selbst bestätigen, `mark-consent`, doppelt. Einwilligungen, Bedingungen, CAPTCHAs.
- `ai`: Entwurf der KI, `mark-ai`, gepunktet. Freitext, den die Person lesen muss.

**Der Verwender liefert:** das Feld der fremden Seite in `mark` mit `data-mark` und einem `mark__tag` mit dem Wort direkt beim Feld. Auf fremden Seiten setzt die Erweiterung Rand, Halo und Etikett per Shadow DOM, ohne das Layout der Seite zu verschieben.

**Werte** stammen aus `erweiterung/form/filler.js` und bleiben gleich. `mark-open` hat auf Weiss nur 3.1:1, `mark-consent` und `mark-ai` auf dunklen Seiten unter 3:1: Halo (`mark-halo`), Linienart und Etikett mit `mark-ink` tragen die Bedeutung.

**Nicht:** ein Einwilligungsfeld ankreuzen; ein Formular absenden.
