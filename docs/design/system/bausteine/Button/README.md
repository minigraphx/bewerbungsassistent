# Button

Knöpfe für Handlungen: ein Hauptknopf pro Bereich, alles andere Zweitknopf oder leiser Knopf.

**Varianten:** `btn btn--primary` (Hauptknopf, `accent`), `btn` (Zweitknopf, Rand `line-strong`), `btn btn--quiet` (unterstrichen, für Später, Abbrechen in Zeilen), `btn btn--danger` (nur für Unumkehrbares wie Löschen). `btn--sm` (32px) nur in Tabellenzeilen. Mehrere Knöpfe in `btn-row`.

**Der Verwender liefert:** ein `<button type="button">` oder `<a class="btn">` mit einem Verb als Text („Anschreiben lesen“, „Im Job-Room eintragen“).

**Zustände:**
- Warten: `aria-busy="true"` und `disabled`, Text sagt, was geschieht („Anschreiben wird entworfen …“). Den Fortschritt zeigt `Progress` daneben.
- Nicht möglich: `aria-disabled="true"` plus `btn-reason` darunter mit dem Grund. Ohne Grund lieber den Knopf weglassen.

**Nicht:**
- Zwei Hauptknöpfe nebeneinander. In der Trefferliste ist „Übernehmen“ ein `btn--sm`, kein Hauptknopf.
- `btn--danger` für Überschreiben, das sich zurückholen lässt.
- „OK“, „Senden“, „Absenden“. Abschicken macht die Person auf der Seite der Firma.
