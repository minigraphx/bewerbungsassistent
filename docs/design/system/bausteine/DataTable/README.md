# DataTable

Tabelle für Bewerbungen und Treffer, die bei schmalem Platz zu Zeilenkarten wird.

**Der Verwender liefert:** `<div class="table-wrap">` um `<table class="table">`, je Zelle ein `data-label` mit dem Spaltennamen (leer für die erste Zelle). Bis 760px Breite des Behälters (Container Query) werden die Zeilen zu Karten mit Etiketten; nichts läuft mehr aus dem Bild.

**Spalten:** höchstens sechs. Stelle und Firma in einer Zelle (`table__main`, `table__sub`). Die Spalte „Nächster Schritt“ (`table__next`) sagt, was zu tun ist, mit höchstens einem `btn--sm`. Selten gebrauchte Angaben (Variante, Formular, Inserat, RAV) gehören in die Bewerbung, nicht in die Liste.

**Sortieren:** Kopf als `<button>` in `<th aria-sort>`. Gewählte Zeile `aria-selected="true"`. Zahlen und Daten rechtsbündig mit `num`.

**Details:** In der Trefferliste öffnen Details in einer Spalte rechts neben der Liste (ab 1180px) oder darunter, damit die Zeilen nicht springen.

**Nicht:** Wahlfelder, die ohne Grund inaktiv sind; Knopfleisten über der Tabelle, die erst nach einer Wahl wirken.
