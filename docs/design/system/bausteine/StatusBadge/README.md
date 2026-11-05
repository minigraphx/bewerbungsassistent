# StatusBadge

Stand einer Bewerbung als Marke mit Wort und Punkt.

**Der Verwender liefert:** `<span class="status" data-status="…">` mit einem der acht Werte aus dem Register als `data-status` und als Text: Gemerkt, Bewerben, Beworben, Gespräch, Absage, Zusage, Verworfen, Zurückgezogen.

**Bedeutung:** Bewerben ist gefüllt in `accent` („jetzt dran“), Beworben in `accent-subtle` („läuft“). Gespräch ist hellgrün mit grünem Rand (`success-bg`, ein grosser Schritt weiter), Zusage gefüllt grün (`success`, `on-success`). Gespräch und Zusage unterscheiden sich in der Füllung, nicht nur im Wort, damit eine Einladung nicht wie eine Zusage wirkt. Absage, Verworfen und Zurückgezogen sind leise mit hohlem Punkt; die zwei selbst beendeten zusätzlich gestrichelt.

**Nicht:** Absagen rot oder Beworben gelb färben. Die Marke ist keine Warnung. Text nie weglassen; der Punkt allein trägt keine Bedeutung.
