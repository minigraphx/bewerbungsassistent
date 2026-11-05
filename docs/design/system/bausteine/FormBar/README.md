# FormBar

Leiste der Browser-Erweiterung am Rand eines fremden Formulars: was ausgefüllt ist, was offen bleibt, und dass die Person abschickt.

**Der Verwender liefert:** `form-bar` mit `role="region"` und `aria-label`, eine Zusammenfassung in `form-bar__summary` (Zahlen zuerst, danach immer `form-bar__hand` „Abschicken bleibt bei Ihnen.“, Lehrstelle „bei dir“), die Legende der `FieldMark`-Arten und `form-bar__actions` mit genau einem Hauptknopf.

**Hauptknopf je Lage:** beim Ausfüllen „Abgeschickt? Ja“, im Job-Room „Eingetragen? Ja“, während der Suche „Suche abbrechen“. Weitere Knöpfe: „Nicht mehr ausfüllen“, „Hier ausfüllen“, „Dateien im Ordner zeigen“, „Leiste nach oben“ / „Leiste nach unten“.

**Lage:** unten ist der Normalfall. Mit «Leiste nach oben» wechselt sie an den oberen Rand: Klasse `form-bar--top`, Schatten nach unten, Knopf heisst dann «Leiste nach unten». Die Wahl gilt pro Website und bleibt gespeichert.

**Immer dunkel:** `inverse`, `on-inverse` und `on-inverse-muted` sind in beiden Themen gleich.

**Grenzen:** Shadow DOM, eigene aufgelöste Werte statt `tokens.css`, nimmt eigenen Platz ein (die Seite rückt um die Höhe der Leiste), verdeckt keine Felder und schickt nie etwas ab.

**Nicht:** mehr als eine Zeile Zusammenfassung plus Satz; Farbe der fremden Seite übernehmen.
