# AiResult

Karte für jede Ausgabe der KI: Einschätzung einer Stelle, Prüfung des Inhalts oder Belege im Anschreiben, immer mit Hinweis, Modell und Kosten.

**Der Verwender liefert:** `ai-result__kind` (was es ist: „Einschätzung der KI“, „Prüfung des Inhalts“, „Aussagen im Anschreiben“), rechts davon eine `Grade` oder eine Zählung, den Inhalt (Spalten „Was passt“ und „Was fehlt oder unsicher ist“ in `ai-result__cols`, oder `claim`-Zeilen), höchstens einen Hauptknopf und im Fuss `ai-result__foot`: „Eine Einschätzung, kein Urteil. Die KI kann sich irren.“, Modell, Kosten, Datum.

**Belege (`claim`):** jede Aussage des Anschreibens mit Quelle. `data-evidence="gap"` macht eine Lücke sichtbar und nennt den Ausweg.

**Keine KI eingerichtet:** Statt der Karte ein `notice` mit dem Weg zur Einrichtung; die übrigen Knöpfe der Seite bleiben nutzbar.

**Nicht:** KI-Ergebnisse ohne Fuss; Kosten im Knopftext; Begründung hinter mehr als einem Klick.
