# Suchbegriffe prüfen lassen

Gehört zu G45 (#210) und berührt G15, G31, G41 und G43. Gewählt hat Andy am 10.11.2026 Option B, «Prüfliste mit Belegen», dazu aus Option C den Endstand «So sucht die App danach» als zugeklappten Block. Die Zeichenflächen mit allen drei Optionen liegen in Claude Design (Board «Pruefliste»). Gilt vorerst nur für Stellen, nicht für Lehrstellen.

## Worum es geht

Ein günstiger KI-Schritt schlägt Suchbegriffe und Titelfilter vor, positiv und ausgeschlossen, und markiert zu allgemeine Begriffe. Grundlage sind Suchprofil, Lebenslauf und die eingeschätzten Treffer mit ihren Noten. Die Person übernimmt alles, einen Teil oder schreibt, was anders sein soll. Ohne ihre Zustimmung ändert sich am Suchprofil nichts.

## Zahlen rechnet die App, die KI begründet

- Ein Treffer «kam nur über X herein», wenn X der einzige Begriff aus «Titel enthält eines davon» ist, der in seinem Titel als ganzes Wort steht (dieselbe Prüfung wie G31).
- Für X zählt die App diese Treffer, wie viele davon unter Note 4 liegen, und nennt die drei häufigsten Titel darunter als Beispiele.
- Gezählt wird gegen die Begriffe, die das Suchprofil jetzt hat. Ändert die Person einen Begriff, gibt es keine veralteten Zahlen.
- Die KI bekommt die Zahlen schon gezählt. Sie entscheidet, was sich ändern soll, und schreibt den Grund. Jede Zahl in der Oberfläche stammt von der App (`bewerbungen/term_evidence.py`).

## Hinweis nach dem Lauf

Über der Trefferliste, nur wenn die App ohne KI einen auffälligen Begriff findet:

- mindestens 30 eingeschätzte Treffer;
- der Begriff bringt allein mindestens 10 Treffer und mindestens 20 % aller eingeschätzten;
- davon liegen mindestens 70 % unter Note 4;
- es erscheint nur der stärkste Fall.

«Ausblenden» gilt für diesen Begriff (`begriffe_ausgeblendet` in `suche/einstellungen.yaml`). Ein neuer oder geänderter Begriff bekommt wieder einen Hinweis.

## Der Vorschlag ist eine Liste von Änderungen

Jede Änderung hat einen Bereich (Suchbegriffe, Titel enthält eines davon, Titel enthält keines davon), die Begriffe, die wegfallen, die Begriffe, die dazukommen, und einen Grund. Ersetzen ist Wegfallen und Dazukommen in derselben Änderung, also ein Entscheid. Nischen, Orte, Portale, Zeitfenster und die festen Ausschlüsse (G33) bleiben, wie sie sind.

Die App prüft jede Änderung, bevor die Person sie sieht (`bewerbungen/term_changes.py`). Ist ein Teil ungültig, fällt die ganze Änderung weg, damit ein Ersatz nie halb übernommen wird:

- Was wegfallen soll, muss im Bereich stehen.
- Was dazukommt, ist ein kurzer Begriff, steht noch nicht im Bereich und nicht schon in einer anderen Änderung.
- Ausschlüsse der Person gehen vor: Ein neuer Suchbegriff oder positiver Titelbegriff mit einem Wort aus «Ausschlüsse» oder aus «Titel enthält keines davon» kommt nicht durch.
- Höchstens 10 Änderungen. Geordnet nach Wirkung: zuerst die mit dem grössten Beleg.

## Regeln für das Übernehmen

- **Nichts ohne Zustimmung.** Erst «Übernehmen» schreibt, und nur die angehakten Änderungen.
- **Nichts geht verloren.** Vor dem Schreiben sichert die App das Suchprofil als Entwurf. Danach gibt es «Rückgängig machen», solange niemand sonst das Suchprofil geändert hat; sonst liegt der frühere Stand unter «Entwürfe und Versionen».
- **Grenzen der Suche (G43).** Die Zeile «Danach: 6 von 15 Suchbegriffen · bis 12 von 30 Suchen pro Portal» steht immer da. Geht eine Auswahl über 15 Suchbegriffe, 30 Begriffe pro Titelfilter oder 30 Suchen pro Portal und wird es mehr als heute, ist der Knopf gesperrt und sagt warum. Ein Profil, das heute schon darüber liegt, bleibt bedienbar, solange die Auswahl es nicht verschlimmert.
- **Veraltet.** Ändert die Person ihre Begriffe, während ein Vorschlag offen ist, gilt er nicht mehr: «Vorschlag veraltet» mit «Neu vorschlagen».
- Ein Vorschlag lebt nur, solange die App läuft. Die Seite nennt eine Änderung nur über ihre Stelle im Vorschlag; was die Seite schickt, kann keine eigene Änderung werden.

## Kosten und was an die KI geht

- Neben dem Knopf steht die Schätzung, «Etwa 0.01 USD», aus der Länge des Texts und dem Preis des günstigen Modells, auf den Cent aufgerundet, mindestens ein Cent. Währung wie sonst in der App: USD, bis ein eigener Entscheid etwas anderes sagt.
- Im Fuss der Karte steht, was der Aufruf gekostet hat, ab dem zweiten Vorschlag auch «bisher».
- «Was geht an die KI?» klappt einen Satz auf. «Text ansehen» öffnet den Text mit Platzhaltern, so wie er gesendet würde (G15). Ansehen sendet nichts.
- An die KI gehen: Suchprofil und Lebenslauf mit Platzhaltern, die drei Bereiche mit ihren Begriffen, die Belege der App und Titel und Note der eingeschätzten Treffer (höchstens 150, die neuesten zuerst), nie Inseratstexte. Stilprofil und Bausteine nicht. Bei «Neu vorschlagen» dazu der letzte Vorschlag und der Text der Person. Die Datenschutzerklärung auf dem Hosting nennt das.

## Ablauf

1. **Einstieg.** «Suchbegriffe prüfen lassen» im Hinweis nach dem Lauf und immer unter «Suche einstellen», vor «Welche Stellen passen zu Ihnen?». Ein Klick öffnet die Ansicht und holt den Vorschlag; fehlt die Einwilligung, fragt die Seite zuerst danach.
2. **Warten.** `progress` mit «KI prüft Ihre Suchbegriffe», «Meist unter 30 Sekunden. Am Suchprofil ändert sich nichts, bis Sie etwas übernehmen.» und «Abbrechen».
3. **Vorschlag.** Eigene Ansicht `/suchbegriffe` in Lesebreite (760) mit «Zurück zu den Treffern». Eine KI-Karte mit einer Karte pro Änderung, alle angehakt.
4. **Entscheiden.** «Alle 3 übernehmen», «2 von 3 übernehmen», ohne Häkchen gesperrt mit «Mindestens eine Änderung anhaken.» Dazu «Verwerfen».
5. **Überarbeiten.** «Was soll anders sein?» steht unter der Karte. Vorschlag 2 ersetzt die Liste und sagt, was sich geändert hat. «Vorschlag 1 zeigen» holt den alten zurück.
6. **Übernommen.** Meldung mit «Rückgängig machen», daneben «Jetzt suchen».

## Eine Änderung

- Bereich und, falls die App einen Beleg hat, die Marke «zu allgemein»;
- der Satz der Änderung als Etikett des Häkchens, etwa «Engineer» ersetzen durch Backend, Frontend und Full Stack;
- die Begriffsmarken: Engineer entfällt, Backend neu, Frontend neu, Full Stack neu;
- der Grund der KI;
- der Beleg der App: Balken, «56 von 130 Treffern kamen nur über «Engineer» herein, 47 davon unter Note 4.», die Beispiele und «Diese 56 Treffer ansehen». Der Link öffnet die Trefferliste mit genau diesen Treffern (`/treffer#beleg=Engineer`), in jedem Zustand, mit «Alle Treffer zeigen».

Darunter klappt «So sucht die App danach» den Endstand der angehakten Änderungen auf, neue Begriffe mit «neu», dazu «Fällt weg: …».

## Bausteine

| Baustein | Aussehen |
| --- | --- |
| `term` | Rand `line-strong`, `radius-md`. `term--new`: `accent-subtle`, Rand `accent`, Wort «neu». `term--gone`: gestrichelt, durchgestrichen, Wort «entfällt». |
| `term--flag` | Fläche `warning-bg`, Rand und Wort «zu allgemein» in `warning`. Abweichung: `warning` heisst sonst «bald zu tun»; ein zu allgemeiner Begriff ist eine Aufgabe für die Person. Das Wort trägt die Bedeutung. |
| `share` | Balken in Grautönen, schraffiert für «unter Note 4», ohne `accent`, damit er nicht wie eine Note aussieht. `aria-hidden`, die Zahl steht im Satz daneben. |

## Texte

| Ort | Sie | du |
| --- | --- | --- |
| Satz beim Knopf | Die KI schlägt vor, Sie entscheiden. Am Suchprofil ändert sich erst etwas, wenn Sie übernehmen. | Die KI schlägt vor, du entscheidest. Am Suchprofil ändert sich erst etwas, wenn du übernimmst. |
| Was geht an die KI? | An die KI gehen Ihr Suchprofil und Ihr Lebenslauf mit Platzhaltern für Name, Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, ohne Inseratstexte. | An die KI gehen dein Suchprofil und dein Lebenslauf … |
| Hinweis | Ein Begriff lässt viel Unpassendes durch · «Engineer» im Titelfilter: 56 von 130 Treffern, 47 davon unter Note 4, zum Beispiel EMSR-Engineer, Process Engineer. · Die KI kann bessere Begriffe vorschlagen. Geändert wird nur, was Sie übernehmen. Etwa 0.01 USD. · Suchbegriffe prüfen lassen · Ausblenden | … was du übernimmst. |
| Ansicht, Kopf | Die KI hat Ihr Suchprofil, Ihren Lebenslauf und 130 Treffer seit dem 20.10.2026 angesehen. Geändert wird nur, was angehakt ist. | … dein Suchprofil, deinen Lebenslauf … |
| Karte | Vorschlag der KI · 5 Änderungen | gleich |
| Fuss | Ein Vorschlag, kein Urteil. Die KI kann sich irren. Geändert wird nur, was Sie übernehmen. · Claude · 0.01 USD · 10.11.2026 | … was du übernimmst. |
| Überarbeiten | Was soll anders sein? · Die KI überarbeitet den Vorschlag. Ihr Text geht mit dem Vorschlag an die KI. · Neu vorschlagen | … Dein Text … |
| Vorschlag 2 | Vorschlag 2 · nach Ihrem Hinweis · Geändert gegenüber Vorschlag 1: … · Ihr Hinweis: «…» · Vorschlag 1 zeigen | … nach deinem Hinweis · Dein Hinweis … |
| Nichts zu verbessern | Ihre Suchbegriffe passen. Die KI schlägt keine Änderung vor. | Deine Suchbegriffe passen. … |
| Fehler | Kein Vorschlag. «Meldung der KI» Nichts berechnet. Am Suchprofil hat sich nichts geändert. · Nochmals versuchen; wurde der Aufruf berechnet: «Berechnet: 0.01 USD.» | gleich |
| Veraltet | Vorschlag veraltet · Die Suchbegriffe haben sich seit dem Vorschlag geändert. Bitte neu vorschlagen lassen. · Neu vorschlagen | gleich |
| Übernommen | Übernommen: 5 Änderungen. Die nächste Suche sucht danach. Der bisherige Stand bleibt unter Entwürfe erhalten. · Rückgängig machen | gleich |
| Rückgängig | Rückgängig gemacht. Es gilt wieder der Stand vor dem Vorschlag. | gleich |
| Einwilligung fehlt | Bevor die KI Suchbegriffe vorschlägt, braucht es Ihre Einwilligung. | … deine Einwilligung. |

## Zugänglichkeit

- Bedeutung nie nur über Farbe: Jede Marke trägt ein Wort, dazu die Linienart.
- Die Änderungen sind ein `fieldset` mit der Legende «Änderungen zum Übernehmen» (`visually-hidden`). Jedes Häkchen hat den Satz der Änderung als `label`, der Grund hängt über `aria-describedby` daran.
- Warten mit `role="status"`; danach springt der Fokus auf «Vorschlag der KI» (`tabindex="-1"`).
- Der gesperrte Knopf nennt den Grund in `btn-reason` über `aria-describedby`.
- «Text an die KI» ist ein `<dialog>` mit Fokus auf «Schliessen».
- Treffertitel kommen von den Portalen: als Text eingesetzt, nie als HTML.

## Später

- Lehrstellen: Dort gibt es keinen Titelfilter, «Welcher Beruf passt zu dir?» deckt die Berufe ab.
- «Titel enthält eines davon» von Hand ändern ist #217 (0.3).
- Ob «Welche Stellen passen zu Ihnen?» und «Suchbegriffe prüfen lassen» ein Einstieg werden, ist offen.
