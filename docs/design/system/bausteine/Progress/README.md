# Progress

Anzeige für Warten: was gerade geschieht, wie weit es ist und wie lange es meist dauert.

**Läufe mit Anzahl** (Suche, Einschätzung vieler Treffer): `progress__head` mit Tätigkeit und „3 von 10“, `progress__track` mit einem `<span>` pro Einheit (`done`, `now`), `progress__note` mit üblicher Dauer und bisherigen Kosten, Knopf „Anhalten“.

**Einzelne KI-Aufrufe** (10 bis 60 Sekunden): `progress__busy` plus `progress__phases`, die Arbeitsschritte mit `aria-current="step"`. Die Bewegung entfällt bei `prefers-reduced-motion`.

**Der Verwender liefert:** `role="status"` und `aria-live="polite"`, ehrliche Angaben zur Dauer („meist unter einer Minute“). Keine erfundene Restzeit.

**Wo:** direkt an der Stelle des Knopfs, der den Lauf gestartet hat. Bei Suchläufen zusätzlich als Zähler in der Navigation (`app-nav__count`).
