# Notice

Meldungen: `notice` als Kasten für Dinge, die Aufmerksamkeit brauchen, `status-line` als Zeile direkt unter dem Knopf, der sie ausgelöst hat.

**Varianten:** `notice` (neutral, Information), `notice--warning` (bald zu tun), `notice--danger` (etwas ist schiefgegangen), `notice--success` (erledigt). Aufbau: `notice__title` (zwei bis vier Wörter, sagt die Stufe auch ohne Farbe), `notice__body` (ein Satz), optional `notice__actions` mit einem Knopf.

**`status-line`** mit `data-level` warning, danger oder success und `aria-live="polite"`. Steht immer direkt unter dem auslösenden Knopf, nie oben auf der Seite.

**Banner:** Ein `notice` über dem Seiteninhalt nur für App-weite Dinge (fehlende Erweiterung, neue Version, Sicherung, RAV-Erinnerung). Höchstens einer zugleich.

**Nicht:** linker Farbbalken als Schmuck; „Fehler!“ ohne Ausweg; mehrere Banner gestapelt.
