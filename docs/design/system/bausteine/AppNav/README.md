# AppNav

Hauptnavigation der App: Schriftzug, die Seiten des Alltags und ein Menü „Mehr“ für Seltenes, nach Gruppen geordnet.

**Der Verwender liefert:** `<nav class="app-nav">` mit `app-nav__brand` (Schriftzug, führt zur Übersicht), `app-nav__list` mit höchstens vier `app-nav__link` (aktuelle Seite mit `aria-current="page"`), und `<details class="app-nav__more">` mit einem `menu` aus `menu__group`s mit `menu__heading`.

**Zähler:** Läuft eine Suche oder Einschätzung, zeigt `app-nav__count` den Stand („3 von 10“) am Link.

**Die Einträge im Beispiel sind ein Vorschlag**, keine beschlossene Struktur: Alltag oben, Unterlagen, Für Geübte und App im Menü. Die Struktur selbst ist Teil der Neugestaltung der Abläufe.

**Nicht:** Alltägliches und Seltenes in einer Liste ohne Gruppen; mehr als vier Einträge in der Leiste.
