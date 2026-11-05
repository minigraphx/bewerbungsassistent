# Field

Eingabefelder mit Etikett, Hilfe und Fehler: Textfeld, Auswahl, Textbereich, Kontrollkästchen und Schalter.

**Aufbau:** `field` umschliesst `field__label` (immer sichtbar, kein Platzhalter als Etikett), `input` (auch auf `<select>` und `<textarea>`), optional `field__hint` und `field__error`. Freiwillige Felder bekommen `field__optional` „(freiwillig)“; Pflicht ist der Normalfall und wird nicht markiert.

**Der Verwender liefert:** `id`/`for`, bei Fehlern `aria-invalid="true"` und `aria-describedby` auf den Fehlertext.

**Fehlertexte** nennen den Ausweg: „Bitte eine Zahl zwischen 10 und 100 eingeben.“, nicht „Ungültige Eingabe“. Sie erscheinen beim Verlassen des Feldes, nicht beim Tippen.

**Kontrollkästchen** (`check`) für Auswahl, **Schalter** (`switch`, `role="switch"`) für Einstellungen, die sofort wirken.

**Nicht:** Fachbegriffe als Etikett („Firmen-Schlüssel“, „ID“). Felder, die selten geändert werden, gehören in einen aufklappbaren Bereich „Angaben zur Stelle“, nicht an den Anfang der Seite.
