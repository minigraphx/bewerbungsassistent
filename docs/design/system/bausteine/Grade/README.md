# Grade

Note der KI für einen Treffer oder eine Bewerbung, mit Zahl, Balken aus sechs Feldern und einem Wort.

**Der Verwender liefert:** die Note (1 bis 6, in Halben) mit Punkt geschrieben (`4.5`), sechs `<i>` im Balken (`on` = voll, `half` = halb), das Wort und ein `aria-label` mit Note, Skala und Wort. `data-uncertain` bei unsicherer Note.

**Wörter:** ab 5.5 „passt sehr gut“, 4.5 und 5 „passt gut“, 4 „passt knapp“, unter 4 „passt wenig“. Bei Lehrstellen zwei Noten nebeneinander: „Beruf“ und „Lehrstelle“, mit `grade-meter--sm`.

**Erklärung:** Einmal pro Liste oder Seite ein `grade-help` neben der Note.

**Klick auf die Note** öffnet die Begründung (`AiResult`). Die Begründung ist nie mehr als einen Klick entfernt.

**Nicht:** Noten rot oder grün färben; `4,5` mit Komma; ein „?“ allein für unsicher.
