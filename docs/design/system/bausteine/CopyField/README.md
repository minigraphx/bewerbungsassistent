# CopyField

Liste von Werten mit eigenem Kopierknopf, für das Eintragen im Job-Room und für Pfade.

**Der Verwender liefert:** `<dl class="copy-list">` mit `copy-row`s: Etikett in `<dt>`, Wert in `copy-row__value`, Knopf `btn btn--sm` „Kopieren“. Nach dem Kopieren wird der Knopf zu „Kopiert“ mit `data-copied` (zwei Sekunden) und eine `status-line` mit `aria-live` sagt, was kopiert wurde.

**Leere Werte** zeigen „leer“ kursiv, der Knopf ist dann `disabled`.

**Nicht:** Pfade zeigen, wo ein Knopf „Ordner öffnen“ möglich ist; technische Feldnamen als Etikett.
