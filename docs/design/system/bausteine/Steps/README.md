# Steps

Schrittanzeige für Abläufe mit fester Reihenfolge: eine Bewerbung von der Stelle bis zum Festhalten, die Einrichtung, Meine Angaben.

**Der Verwender liefert:** `<ol class="steps">` mit `aria-label`, je Schritt `steps__item` mit `data-state` `done`, `current` oder `todo`, beim aktuellen zusätzlich `aria-current="step"`. Darin `steps__dot`, `steps__label` (ein bis zwei Wörter) und optional `steps__meta` (Datum, was zu tun ist, Dauer).

**Waagrecht** ab 760px Fensterbreite. Darunter werden alle Schritte von selbst **senkrecht**; in schmalen Spalten auch bei breitem Fenster `steps--vertical` setzen. Erledigte Schritte bleiben anklickbar, wenn man dorthin zurück kann.

**Bewerbung, sechs Schritte:** Stelle, Lebenslauf, Anschreiben, Prüfen, Abschicken, Festhalten. Beim Schritt Abschicken steht „machen Sie selbst“ (Lehrstelle: „machst du selbst“).

**Nicht:** mehr als sieben Schritte (Meine Angaben gruppiert die 16 Reiter zu höchstens sieben); Prozentzahlen.
