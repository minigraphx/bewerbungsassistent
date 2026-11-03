# Konzept: Bewerbungsassistent als App und Onlinedienst (MIN-305)

Stand 3.11.2026 (freigegeben; Pilot als lokale App entschieden am 2.11.2026; Bewerben im Browser, RAV-Einträge und eigener API-Schlüssel ergänzt am 3.11.2026). Ersetzt den Entwurf vom 26.10.2026. Grundlage für die Meilensteine „Pilot: lokale App“ und „Onlinedienst: Release (Abo, EU)“ im Linear-Projekt.

## Entscheide

| Frage | Entscheid (2.11. und 3.11.2026) |
|---|---|
| Zielgruppe | Zuerst ein **Pilot mit 5–10 Personen aus dem Bekanntenkreis**, betreut vom Projektinhaber. Nach dem Pilot wird über einen öffentlichen Dienst entschieden. |
| Form im Pilot | Eine **lokale App** auf dem Rechner der Person (macOS, Windows), dazu eine **Browser-Erweiterung** für die Suche. Die Daten bleiben auf dem Rechner; auf einem Server liegt nur die kleine **KI-Vermittlung**. Der **gehostete Onlinedienst** folgt erst nach dem Pilot. |
| Kernstück | Die **Stellensuche**: Sie dauert heute am längsten und gehört darum in den Pilot. |
| KI | Die App ruft die KI über eine **Vermittlung** des Projektinhabers auf. Auf den Rechnern liegt **kein API-Schlüssel**: Jede Person meldet die App einmal per Einladungslink an und erhält einen **Zugang mit Budget**. Der Projektinhaber trägt die Kosten. Wer will, gibt stattdessen einen **eigenen API-Schlüssel** an (siehe [Eigener API-Schlüssel](#eigener-api-schlüssel)). In der **Testphase** (Pilot, eventuell kostenlose Konten) läuft die KI über die **Claude API von Anthropic**, auch in den USA. Im **Release** gibt es **keine Verarbeitung in den USA** mehr, nur noch in der EU. |
| Modell | Für die Anschreiben werden Sonnet 5.5 und Opus 5.5 im Pilot verglichen. |
| Personendaten an die KI | Sie werden **von Anfang an**, schon vor dem ersten KI-Aufruf im Pilot, **durch Platzhalter ersetzt** (Pseudonymisierung). So gehen auch in der Testphase nicht alle Daten in die USA. |
| Automatische Suche | Nur auf den **erlaubten Portalen** (job-room, jobs.ch, jobscout24, ictjobs). Auf allen anderen Seiten, z.B. LinkedIn oder Karriereseiten von Firmen, gibt es in der Erweiterung die Knöpfe **„Stelle prüfen“** (Passung bewerten) und **„Stelle speichern“** (in die App übernehmen). |
| Bewerben im Browser | In der **Übersicht der App** setzt die Person Häkchen und klickt auf **„Bewerben“**. Die Erweiterung öffnet **einen Tab pro Bewerbung**, füllt das Formular aus und lädt die Unterlagen hoch, auf jeder Seite. Die Person prüft, bestätigt Datenschutz und Einwilligungen, füllt unklare Felder selbst aus und **schickt selbst ab**. |
| RAV | Gleicher Ablauf mit **„Im RAV eintragen“**: Die Erweiterung trägt die **Arbeitsbemühungen im Job-Room** aus dem Register ein; die Person prüft und schickt ab. |
| Eigener API-Schlüssel | In den **erweiterten Einstellungen** kann die Person einen eigenen Schlüssel angeben. Dann fällt die Beschränkung auf die erlaubten Portale weg, auch für LinkedIn; beim Einschalten erscheint eine Warnung. Die Person trägt Kosten und Risiko selbst. |
| Einstieg | Der Einstieg geht auf drei Wegen: Unterlagen hochladen, ein **Interview mit Claude** in der App oder eine **HTML-Vorlage**, die mit Daten ausgefüllt wird. |
| Ausbildungssuche | Damit auch Schulabgängerinnen und Schulabgänger den Assistenten nutzen können. **2 Lehrstellensuchende**, die aktuell suchen, **machen im Pilot mit**; die Grundlagen kommen darum schon in den Pilot, ausgebaut wird in der fertigen Version. |
| Hosting | Im Pilot nur die KI-Vermittlung, auf dem bestehenden Hosting des Projektinhabers in der Schweiz. Für den Onlinedienst wird es später entschieden. |
| Google Sheets | **Optional, nur als Kopie** (Entscheid 3.11.2026). Führend und einzige Quelle ist das Register in der App. Will die Person eine Jobliste in Google Sheets, legt die App sie auf Wunsch an, zusätzlich zum Register. Ist sie aktiviert, kommt jeder Eintrag und jede Änderung ins Register **und** in die Liste. Gelesen wird die Liste nicht als Quelle. Ohne Liste braucht die App kein Google-Konto. |
| Finanzierung | **Kleines Abo** ab dem öffentlichen Dienst. Der Pilot ist gratis und dient dazu, die Kosten pro Person zu messen. **Schülerinnen und Schüler** (Lehrstellensuche) nutzen den Assistenten **generell kostenlos**, auch nach dem Pilot. |

Die App enthält denselben Code wie das Repo; wer technisch versiert ist, arbeitet weiter mit Repo und Claude Code. Der spätere Onlinedienst ist dieselbe App in einem Container pro Person.

## Zielgruppen und Nutzen

- **Stellensuchende ohne technische Kenntnisse:** Sie brauchen kein Python, kein Git und keine Kommandozeile. Sie installieren die App per Doppelklick und arbeiten im Browser nach demselben Ablauf wie mit dem Repo: Suche → Stelle → Unterlagen → Prüfung → Versand.
  - Nutzen: Passende Stellen finden sie schneller. Pro Stelle entstehen ein passender Lebenslauf und ein Anschreiben im eigenen Stil, in dem jede Aussage belegt ist. Dazu kommen eine Übersicht über alle Bewerbungen und die Angaben für den Job-Room.
- **Schulabgängerinnen und Schulabgänger** (2 im Pilot, ausgebaut in der fertigen Version): Sie suchen Lehrstellen und Schnupperlehren und erstellen ihr erstes Bewerbungsdossier (siehe [Ausbildungssuche](#ausbildungssuche)).

## Phasen

1. **Pilot = Testphase mit der lokalen App** (etwa 3 Monate, gratis, auf Einladung, KI über die Claude API). Er soll vier Fragen klären: Spart die Suche wirklich Zeit? Kommen nicht versierte Personen mit Installation und Ablauf zurecht? Was kostet eine aktive Person pro Monat? Braucht es danach einen gehosteten Dienst?
2. **Release: öffentliches Angebot mit Abo**, KI-Verarbeitung nur in der EU, Ausbildungssuche ausgebaut. Es kommt nur, wenn der Pilot die Erfolgskriterien erfüllt. Ob es ein gehosteter Onlinedienst wird oder die App mit einem Abo-Zugang zur Vermittlung reicht, wird nach dem Pilot entschieden.

Erfolgskriterien des Pilots:

- Mindestens 8 von 10 Personen installieren die App und richten sie ohne Hilfe vor Ort ein.
- Eine wöchentliche Suche samt Bewertung der Treffer dauert für die Person unter 15 Minuten.
- Mindestens 5 Personen schicken je mindestens 3 Bewerbungen ab, die mit der App erstellt wurden.
- Beide Lehrstellensuchenden schicken Bewerbungen mit Lebenslauf und Motivationsschreiben aus dem Assistenten ab.
- Eine Bewerbung dauert von der Stelle bis zu den fertigen PDFs unter 30 Minuten.
- Die KI-Kosten liegen unter CHF 10 pro aktive Person und Monat (gemessen, nicht geschätzt).
- Kein Datenschutzvorfall.
- Die Rückmeldungen zeigen, welche Schritte ohne Hilfe nicht klappen.

## Umfang im Pilot

| Enthalten | Nicht im Pilot |
|---|---|
| **App** für macOS und Windows: Installation per Doppelklick, Ersteinrichtung (Datenordner, Erweiterung, Einladung), Hinweis auf Updates | Daten auf einem Server (kommen erst mit dem Onlinedienst) |
| **Lehrstellensuche, Grundlagen:** Art der Ausschreibung, Suchprofil nach Berufen, Schülerlebenslauf, Motivationsschreiben; Lehrstellen per Text einfügen | Lehrstellenportale in der Erweiterung, Lesezugang für Begleitpersonen |
| **Einstieg** auf drei Wegen (siehe unten): Lebenslauf, Suchprofil, Stilprofil, Bausteine | Erinnerungen per E-Mail, Job-Abos per E-Mail |
| **Stellensuche** über die Browser-Erweiterung auf job-room, jobs.ch, jobscout24 und ictjobs nach dem Suchprofil; die Treffer gehen an die App | Versand durch die App (die Person schickt selbst ab) |
| Knöpfe **„Stelle prüfen“** und **„Stelle speichern“** auf jeder Seite, z.B. LinkedIn und Karriereseiten | |
| **Bewerben aus der Übersicht:** Häkchen setzen, „Bewerben“ öffnet einen Tab pro Bewerbung, füllt das Formular aus und lädt Lebenslauf, Anschreiben, Zeugnisse und die passenden Zertifikate (als ZIP) hoch | |
| **RAV-Arbeitsbemühungen** aus der Übersicht im Job-Room eintragen lassen | |
| **Erweiterte Einstellungen:** eigener API-Schlüssel, damit auch automatische Suche auf weiteren Seiten | |
| **Jobliste in Google Sheets** auf Wunsch: App legt sie an und trägt zusätzlich zum Register ein | |
| KI-Bewertung jedes Treffers (Note 1–6 mit Begründung), Abgleich gegen Doppelbewerbungen | Handy, Tablet, Chromebook |
| Stelle erfassen: übernehmen aus Suche oder offenem Inserat, oder Text einfügen | Französisch, Englisch |
| Lebenslauf, Themes, Foto (Metadaten werden entfernt), Lebenslauf-Variante vorschlagen (regelbasiert wie heute) | Coaches und Begleitpersonen |
| Anschreiben-Entwurf im eigenen Stil (KI) mit Überarbeitung | |
| Formale Prüfung (wie heute) und inhaltliche Prüfung (KI) | |
| Register, Versand festhalten, Job-Room-Angaben zum Kopieren | |
| Entwürfe und Versionen; alle Daten in einem Ordner der Person (sichern, mitnehmen, löschen) | |

## Einstieg: drei Wege, ein Ergebnis

Der Einstieg ist die grösste Hürde für nicht versierte Personen. Mit dem Repo entstehen Lebenslauf, Stilprofil und Bausteine heute in einer Sitzung mit Claude Code. Für alle drei Wege gilt: Das Ergebnis ist immer gleich, nämlich `cv.yaml`, das Suchprofil, das Stilprofil und die Bausteine. Die Person bestätigt jede Angabe, bevor sie gilt.

| Weg | Wie | Geeignet für |
|---|---|---|
| **Unterlagen hochladen** | Bisherigen Lebenslauf (PDF oder Text) und 2–3 frühere Anschreiben hochladen. Die KI liest daraus die Angaben und den Stil heraus. | Personen mit bestehenden Unterlagen |
| **Interview mit Claude** | Claude fragt Schritt für Schritt nach: Ausbildung, Stationen, Stärken, Ziele, Region, Pensum, Ton (Du/Sie). Fehlende Belege fragt es gezielt nach. In der App ist das ein geführtes Gespräch über `ki.py`. Mit Claude Code geht es über den Skill `einstieg`; so führt der Projektinhaber die ersten Interviews, bevor die App fertig ist. | Personen ohne Unterlagen, Schulabgängerinnen und Schulabgänger |
| **HTML-Vorlage** | Eine einzelne HTML-Datei mit Formular für Lebenslauf, Suchprofil und Stil. Sie läuft ohne Server im Browser und ist über einen Link erreichbar (z.B. GitHub Pages), ohne Installation. Die Daten bleiben lokal. Man füllt sie von Hand aus, oder Claude füllt sie aus dem Interview vor. Sie speichert eine Datei, die die App importiert. | Wer lieber selbst ausfüllt, offline arbeitet oder mit Begleitung (Eltern, Beratung) ausfüllt |

Die HTML-Vorlage prüft die Eingaben mit denselben Regeln wie das Register und der Lebenslauf. Beim Import prüft die App nochmals, denn die Datei ist eine Eingabe von aussen. Ohne frühere Anschreiben entsteht das Stilprofil aus dem Interview und aus 2–3 Beispielsätzen, die die Person auswählt oder anpasst.

## Stellensuche über den Browser der Person

Die Suche ist das Kernstück. Stellenportale und Bewertungsseiten (job-room, LinkedIn, kununu, viele Karriereseiten) sperren aber Adressen von Rechenzentren und KI-Anbietern häufig. Ein Server oder die Web-Abfrage der KI kämen dort nicht zuverlässig durch. Der Skill `jobsuche` funktioniert heute nur, weil er im eingeloggten Browser der Person abfragt.

**Grundsatz:** Die KI ruft selbst keine fremden Websites ab. Abfragen bei Portalen laufen auf dem Rechner der Person, mit ihrer IP und ihren Logins, und nur, solange sie am Rechner ist und die Suche gestartet hat. Die App erhält nur das Ergebnis, zum Beispiel eine Trefferliste oder einen Inseratstext. Bewertung, Abgleich und Eintrag ins Register laufen danach in der App.

Weil die App auf dem Rechner der Person läuft, hat sie deren IP. Einfache Portale ohne Login kann sie darum auch selbst abfragen. Portale mit Login oder viel JavaScript bleiben bei der Erweiterung.

| Weg | Wie | Einschätzung |
|---|---|---|
| **Browser-Erweiterung** (Empfehlung) | Die Erweiterung (Chrome, Edge, danach Firefox) sucht in Portal-Tabs nach dem Suchprofil, gleich wie der Skill `jobsuche` mit `fetch` auf derselben Seite, und holt die Volltexte. Die Treffer gehen an die App. | Nutzt die IP und die Logins der Person. Muss einmal installiert und bei Änderungen der Portale nachgeführt werden. Auf dem Handy nur eingeschränkt (Firefox Android, Safari iOS). |
| **Text einfügen** | Inseratstext kopieren und einfügen | Geht immer, ohne Installation; der Ersatz, wenn die Erweiterung fehlt |
| **Job-Abos per E-Mail** (erst mit dem Onlinedienst) | Job-Abos der Portale an eine persönliche Adresse des Dienstes weiterleiten; der Dienst liest Titel, Firma und Link | Stellenvorschläge ganz ohne Abfragen bei den Portalen. Den Volltext holt die Erweiterung, oder die Person fügt ihn ein. |
| **Offizielle Schnittstellen** | Partnerzugänge, z.B. für job-room oder JobCloud | Stabil und rechtlich sauber, aber wohl nur mit Vertrag; zu prüfen |
| ~~Eingebauter Browser in der App~~ (z.B. pywebview) | Portale in einem Fenster der App öffnen, ganz ohne Erweiterung | **Abgelehnt:** Google sperrt „Mit Google anmelden“ in eingebetteten Browsern, und viele melden sich so bei LinkedIn oder jobs.ch an. Im normalen Browser gehen alle Anmeldungen. |
| ~~Proxys mit Privatanschlüssen oder ein VPN~~ | Server-Abfragen über fremde Privatanschlüsse leiten | **Abgelehnt:** umgeht die Sperren bewusst, verletzt die Nutzungsbedingungen und ist rechtlich riskant |

**Regeln für die Erweiterung:**

- **Berechtigungen** (Chrome und Edge):
  - Fest für die erlaubten Portale, für Native Messaging und für die Seite der App auf `127.0.0.1`.
  - **Zugriff auf alle Seiten** als optionale Berechtigung, um die die Erweiterung bei der Einrichtung einmal fragt: Bewerbungsformulare liegen auf beliebigen Seiten, oft in eingebetteten Rahmen der Bewerbungssysteme.
  - Ohne diese Erlaubnis gehen die Knöpfe „Stelle prüfen“ und „Stelle speichern“ trotzdem (`activeTab`); „Bewerben“ fragt dann zuerst danach.
  - Die Erweiterung liest und füllt trotz der Berechtigung nur, wenn die Person es auslöst: Suche starten, Knopf in der Erweiterung, „Bewerben“ oder „Im RAV eintragen“ in der App.
- **App und Erweiterung erkennen sich selbst**, ohne Kopplungscode (wie bei Password-Managern):
  - **Erweiterung → App über Native Messaging:** Die App meldet sich bei der Installation als Native-Messaging-Host bei Chrome und Edge an (Datei im Benutzerordner, unter Windows ein Eintrag in der Registry). Die Erweiterung schickt Treffer direkt an die App, ohne Port und ohne Netz. Chrome lässt nur die Erweiterung mit unserer ID mit der App sprechen. Fehlt die App, meldet Chrome einen Fehler, und die Erweiterung zeigt „App herunterladen“.
  - **App → Erweiterung über die eigene Oberfläche:** Die Oberfläche der App läuft im selben Browser. Die Erweiterung meldet sich auf dieser Seite mit einem Zeichen. Fehlt es, zeigt die App den Schritt „Erweiterung hinzufügen“ mit einem Knopf zum Store; sobald die Erweiterung da ist, verschwindet er.
- **Auslöser:** Sie sucht nur, wenn die Person die Suche startet, und hält die Grenzen aus dem Skill ein (z.B. höchstens 3 Seiten pro Suchbegriff und Ort). Im Hintergrund sucht sie nicht.
- **Automatische Suche nur auf den erlaubten Portalen:** job-room, jobs.ch, jobscout24 und ictjobs. Für jedes gibt es eine eigene Anpassung in der Erweiterung.
- **Knöpfe auf allen anderen Seiten**, z.B. LinkedIn und Karriereseiten der Firmen:
  - **„Stelle prüfen“:** Die Erweiterung liest das offene Inserat und schickt es an die App. Die App bewertet die Passung (Note 1–6 mit Begründung, wie bei den Treffern der Suche) und prüft auf Doppelbewerbungen. Das Ergebnis erscheint in der Erweiterung, ohne dass die Stelle gespeichert wird.
  - **„Stelle speichern“:** übernimmt das Inserat mit Text, Firma, Titel und Link als neue Bewerbung ins Register der App, samt Bewertung.
  - Auf LinkedIn liest die Erweiterung so nur die Seite, die die Person selbst geöffnet hat. Sie navigiert nicht selbständig.
- **Mit eigenem API-Schlüssel** fällt die Beschränkung weg ([Eigener API-Schlüssel](#eigener-api-schlüssel)): Die Person kann weitere Seiten für die automatische Suche angeben, auch LinkedIn. Auf Seiten ohne eigene Anpassung liest die KI die Trefferliste aus dem Seitentext. Die Grenzen der Suche (Seiten pro Suchbegriff, nur bei gestarteter Suche) bleiben.
- **LinkedIn:** Die Nutzungsbedingungen verbieten Automatisierung ausdrücklich, und LinkedIn kann Konten dafür einschränken oder sperren. Die automatische Suche dort gibt es darum nur mit eigenem Schlüssel und erst nach einer Warnung, die die Person bestätigt.
- **CAPTCHAs** bleiben immer bei der Person; die Erweiterung löst und umgeht sie nicht.
- **Wartung:** Sie wird über den Store der Erweiterungen aktualisiert. Ändert ein Portal seine Seiten, ist das ein Update für alle.

## Bewerben im Browser: Formulare, Unterlagen, RAV

Viele Firmen nehmen nur Bewerbungen über ihr Formular an, oft in einem Bewerbungssystem wie Workday, SuccessFactors, Refline, Personio oder rexx. Dazu kommen die Arbeitsbemühungen für das RAV. Beides kostet heute viel Abtippen. Die App füllt diese Formulare darum über die Erweiterung aus, auf jeder Seite, für mehrere Bewerbungen auf einmal (Entscheid 3.11.2026).

**Grundsatz: Das Tool füllt aus, die Person entscheidet und schickt ab.** Diese Regeln gelten immer, auch mit eigenem API-Schlüssel:

- Ausgefüllt wird nur, was die Person in der App mit „Bewerben“ oder „Im RAV eintragen“ ausgelöst hat.
- Den Knopf zum Absenden klickt immer die Person.
- Einwilligungen setzt die Person selbst: Datenschutz, Nutzungsbedingungen, Weitergabe an Dritte, Talent-Pool.
- Unklare Felder füllt die Person selbst aus; das Tool lässt sie leer und markiert sie.
- Die Erweiterung meldet sich nirgends an, legt keine Konten an und gibt keine Passwörter ein. CAPTCHAs löst die Person selbst.
- Hochgeladen werden nur die Dateien, die zu genau dieser Bewerbung gehören.

**Ablauf „Bewerben“:**

1. **Auswahl in der App:** In der Übersicht der Bewerbungen setzt die Person Häkchen bei den Bewerbungen, die sie abschicken will, und klickt auf „Bewerben“.
   - Wählbar sind nur Bewerbungen mit fertigen und freigegebenen Unterlagen (Prüfung ohne Fehler) und einem Link zum Bewerbungsformular.
   - Vorher prüft die App auf Doppelbewerbungen (dieselbe Firma direkt oder über Vermittler) und zeigt Treffer an.
   - Pro Durchgang höchstens einige Bewerbungen, z.B. 5 (Vorschlag, im Pilot anpassen): Jede braucht eine sorgfältige Prüfung, und ein Massenversand soll nicht entstehen.
2. **Ein Tab pro Bewerbung:** Die Erweiterung öffnet für jede gewählte Bewerbung einen Tab mit dem Bewerbungsformular. Führt der Link nur zum Inserat, folgt sie dem Knopf „Jetzt bewerben“; findet sie keinen, markiert sie den Tab, und die Person öffnet das Formular selbst.
3. **Ausfüllen:** In jedem Tab liest die Erweiterung die Felder samt Beschriftungen und Auswahlwerten. Die App ordnet sie den Angaben zu: Name, Adresse, Kontakt, Lohnvorstellung, Eintritt, Kündigungsfrist, Sprachen, Ausbildung, Stationen.
   - Zuerst nach Regeln, z.B. über das Attribut `autocomplete` und bekannte Beschriftungen, für die verbreiteten Bewerbungssysteme mit eigener Anpassung.
   - Was offen bleibt, ordnet die KI zu. Sie sieht dabei nur Beschriftungen und Auswahlwerte, nie die Angaben der Person; die Werte setzt die App lokal ein.
   - Freitextfragen wie „Warum möchten Sie bei uns arbeiten?“ entwirft die KI aus Bausteinen und Anschreiben, pseudonymisiert und belegt wie ein Anschreiben. Sie sind als Entwurf markiert.
   - Kann die App ein Feld nicht sicher zuordnen, bleibt es leer.
4. **Hochladen:** Die Dateien kommen über Native Messaging von der App:
   - Lebenslauf und Anschreiben als PDF der Bewerbung.
   - Arbeitszeugnisse aus dem Datenordner.
   - **Zertifikate, wenn vorhanden, nur die zur Stelle passenden**, zusammen in einer ZIP-Datei (siehe unten).
5. **Mehrseitige Formulare:** Klickt die Person auf „Weiter“, füllt die Erweiterung die nächste Seite selbst aus. Verlangt ein Bewerbungssystem eine Anmeldung oder ein Konto, hält der Tab dort an; nach der Anmeldung durch die Person geht es weiter.
6. **Prüfen und absenden durch die Person:** Oben im Tab zeigt ein Balken den Stand, z.B. „14 Felder ausgefüllt, 3 offen, Datenschutz bitte selbst bestätigen“. Ausgefüllte, offene und als Entwurf markierte Felder sind farbig hervorgehoben. Die Person ergänzt, bestätigt die Einwilligungen und schickt ab.
7. **Stand in der App:** Die Übersicht zeigt pro Bewerbung „geöffnet“, „ausgefüllt“ oder „abgeschickt“. Nach dem Absenden fragt der Balken „Abgeschickt?“; bei Ja erfasst die App den Versand wie heute („Versand erfassen“).

Wie gut das Ausfüllen auf den verbreiteten Bewerbungssystemen klappt, wird im Pilot gemessen.

**Zertifikate pro Bewerbung:**

- Die App schlägt pro Bewerbung die passenden Zertifikate vor, mit Begründung aus dem Inserat (z.B. „Scrum Master: Inserat verlangt agile Erfahrung“). Unpassende bleiben weg, damit das Dossier schlank bleibt.
- Die Person bestätigt oder ändert die Auswahl, bevor sie die Bewerbung freigibt. Die Auswahl gilt für Formular und E-Mail gleichermassen und steht im Register.
- Die App packt die gewählten Zertifikate in eine ZIP-Datei, z.B. `Zertifikate_<Name>.zip`, mit lesbaren Dateinamen darin. Die Datei liegt bei den Unterlagen der Bewerbung und kommt beim Versand mit nach `versendet/`.
- Nimmt ein Formular keine ZIP-Dateien an, fügt die App die gewählten Zertifikate zu einem PDF zusammen (Vorschlag, im Pilot zu prüfen).
- Ohne passende Zertifikate entfällt die Datei.

**RAV-Arbeitsbemühungen** (gleicher Ablauf):

- Die App kennt die nötigen Angaben schon aus dem Register (Abschnitt Job-Room): Datum, Firma, Adresse, Stelle, Pensum, Art der Bewerbung und Ergebnis.
- In der Übersicht setzt die Person Häkchen bei den abgeschickten Bewerbungen, die noch nicht eingetragen sind, und klickt auf „Im RAV eintragen“.
- Die Erweiterung öffnet das Formular für die Arbeitsbemühungen im Job-Room. Ist die Person nicht angemeldet, hält der Tab bei der Anmeldung an; danach füllt die Erweiterung pro Bewerbung einen Eintrag aus.
- Die Person prüft und schickt ab; danach markiert die App die Bewerbung als „im RAV eingetragen“.
- Die App erinnert gegen Monatsende, wenn Bewerbungen des Monats noch nicht eingetragen sind.
- Für RAV, die den Nachweis auf Papier verlangen, ist eine Liste zum Ausdrucken als Ersatz zu prüfen.

## KI-Funktionen und Kosten

### Annahmen

- Der Kontext eines Anschreibens umfasst Stilprofil, Bausteine, Lebenslauf und Inserat. Gemessen an echten Daten sind das rund 20'000 Zeichen oder etwa 7'000 Tokens. Mit Anweisungen sind es etwa **10'000 Tokens Eingabe**.
- Die Ausgabe eines Anschreibens samt Denken umfasst **5'000–10'000 Tokens**.
- Bei der Suche wird nach einem Vorfilter wie im Skill (Region, Titel, Sprache, Alter des Inserats) nur der Rest bewertet. Angenommen sind etwa 300 Bewertungen pro Monat.
- Preise der Claude API (Stand Oktober 2026, pro Million Tokens):

| Modell | Eingabe | Ausgabe |
|---|---|---|
| Claude Opus 5.5 | USD 4 | USD 20 |
| Claude Sonnet 5.5 | USD 2 | USD 10 |
| Claude Haiku 5.5 | USD 0.10 | USD 0.50 |

- Die Beträge sind in USD gerechnet. Für eine Grobschätzung entsprechen sie in etwa Franken.

### Kosten pro Aufruf (Schätzung)

| Funktion | Modell (Vorschlag) | Tokens Eingabe / Ausgabe | Kosten |
|---|---|---|---|
| Treffer bewerten (Passung 1–6), auch „Stelle prüfen“ | Haiku 5.5 | 5'000 / 1'000 | ca. 0.1 Rappen |
| Formularfelder zuordnen (nur Beschriftungen) | Haiku 5.5 | 3'000 / 1'000 | ca. 0.1 Rappen |
| Freitextantwort im Formular | Sonnet 5.5 | 10'000 / 2'000 | ca. 4 Rappen |
| Anschreiben-Entwurf | Sonnet 5.5 | 10'000 / 8'000 | ca. 10 Rappen |
| Überarbeitung (je Runde) | Sonnet 5.5 | 12'000 / 6'000 | ca. 8 Rappen |
| Inhaltliche Prüfung | Sonnet 5.5 | 15'000 / 3'000 | ca. 6 Rappen |
| Einstieg aus Unterlagen (einmalig) | Opus 5.5 | 30'000 / 15'000 | ca. 40 Rappen |
| Einstieg als Interview (einmalig, etwa 20 Fragen) | Opus 5.5 | 200'000 / 20'000, mit Caching | ca. CHF 0.50–1.50 |

Daraus ergibt sich:

- **Eine Bewerbung** (Entwurf, 2 Überarbeitungen, Prüfung) kostet etwa **30–35 Rappen** mit Sonnet 5.5 und etwa das Doppelte mit Opus 5.5.
- **Eine aktive Person pro Monat** (15 Bewerbungen, 300 bewertete Treffer) kostet etwa **CHF 5–6** mit Sonnet 5.5 und **CHF 10–12** mit Opus 5.5.
- **Prompt-Caching** senkt den Eingabe-Anteil: Suchprofil, Stilprofil, Bausteine und Lebenslauf bleiben pro Person gleich. Der grössere Teil der Kosten ist aber die Ausgabe.

Im Pilot protokolliert die App die echten Werte pro Aufruf lokal, ohne Inhalte. Die Vermittlung zählt Tokens und Kosten pro Person, ohne Inhalte. Für die Anschreiben werden Sonnet 5.5 und Opus 5.5 an denselben Stellen verglichen.

### Datenstandort und Datenminimierung

**Testphase (Pilot, eventuell kostenlose Konten): Claude API von Anthropic.** Bei ihr lässt sich die Region nur auf „global“ oder „us“ festlegen; eine Region in der EU oder der Schweiz gibt es nicht. Die Daten gehen damit auch in die USA. Daraus folgt:

- **Rechtsgrundlage:** Nach Art. 16 DSG ist das zulässig, wenn ein angemessener Schutz besteht. Zu prüfen ist, ob Anthropic unter dem Swiss-U.S. Data Privacy Framework zertifiziert ist; sonst braucht es Standardvertragsklauseln.
- **Information:** Die Datenschutzerklärung und die Einwilligung nennen das ausdrücklich, bei Minderjährigen auch gegenüber den Eltern.

**Release: nur EU, keine Verarbeitung in den USA.**

- Die aktuellen Claude-Modelle laufen auf Amazon Bedrock in Zürich (eu-central-2) nicht direkt in der Region. Mit der Geo-Inferenz „EU“ bleibt die Verarbeitung aber in EU-Regionen und Zürich.
- Google Vertex AI mit der Multi-Region „eu“ wäre eine Alternative.
- Der Code nutzt das Anthropic SDK, ein Wechsel ist darum vor allem Konfiguration. Die Preise weichen ab.
- Ob kostenlose Konten weiter über die USA laufen dürfen, ist offen (MIN-337).

**Datenminimierung von Anfang an (MIN-334):**

- Name, Adresse, Geburtsdatum, Telefon, E-Mail, Profil-Links sowie Namen von Referenz- und Ansprechpersonen werden vor jedem KI-Aufruf durch Platzhalter ersetzt und danach wieder eingesetzt.
- Bei Minderjährigen gehen Schule und Wohnort nur so genau wie nötig mit.
- Das Foto geht nie an die KI.
- Inseratstexte bleiben Daten: Anweisungsartige Zeilen werden wie im Skill `bewerbung` erkannt und gemeldet.

## Architektur im Pilot: lokale App

Der Grundsatz lautet: so viel vom heutigen Code wie möglich unverändert nutzen. Die App ist die bestehende Oberfläche (`bewerbungen/app.py`) als installierbares Paket. Jede Person hat ihren Datenordner wie heute (YAML, `versendet/`, `.entwuerfe/`) auf dem eigenen Rechner.

```
Rechner der Person
  Browser ── Portal-Tabs (job-room, jobs.ch …) ◀── Erweiterung sucht mit IP und Login der Person
     │                                               │ Treffer, Inseratstexte
     └── http://127.0.0.1 ──▶ App: app.py + Typst ◀──┘ Native Messaging
                                 ├─▶ Datenordner (z.B. in Dokumente)
                                 ├─▶ Schlüsselbund des Systems (Zugang zur Vermittlung)
                                 └─▶ KI-Aufrufe (pseudonymisiert)
                                        │ HTTPS
Hosting des Projektinhabers (Schweiz)    ▼
  KI-Vermittlung: Zugang prüfen, Budget, Kosten zählen ──▶ Testphase: Claude API · Release: nur EU
  (Anthropic-Schlüssel nur hier; Inhalte nur durchgereicht)
```

- **Paket:** Python, Typst und Schriften als App für macOS (.app in .dmg) und Windows (.exe), z.B. mit PyInstaller oder Briefcase, gebaut in der CI (MIN-342). Ein Doppelklick startet den Server auf `127.0.0.1` und öffnet den Browser. Python, Terminal und Repo braucht die Person nicht.
- **Ersteinrichtung** in drei Schritten in der Oberfläche:
  1. Datenordner wählen oder anlegen.
  2. Erweiterung hinzufügen: ein Klick zum Store, die Seite erkennt die Erweiterung selbst. Danach erlaubt die Person das Ausfüllen von Formularen auf allen Seiten.
  3. Einladungslink anklicken (oder Code eintippen); die App meldet sich bei der Vermittlung an.
- **Zugang statt API-Schlüssel:** Die App legt den Zugang zur Vermittlung im Schlüsselbund des Systems ab (macOS-Schlüsselbund, Windows-Anmeldeinformationen), nie im Datenordner, nie in Protokollen und nie im Installationspaket. Einen Anthropic-Schlüssel sieht die Person nie (siehe [KI-Vermittlung](#ki-vermittlung)), ausser sie gibt einen eigenen an (siehe [Eigener API-Schlüssel](#eigener-api-schlüssel)).
- **KI-Modul:** Ein neues Modul `bewerbungen/ki.py` (MIN-338) erhält eine schmale Schnittstelle für Treffer bewerten, Anschreiben entwerfen, Inhalt prüfen, Einstieg aus Unterlagen und Interview. Die Regeln aus den Skills (Belegpflicht, Stilprofil, Inserat ist Daten) werden zu Prompts, und die Pseudonymisierung sitzt in diesem Modul.
- **Versionen:** Die eigene Ablage reicht: versendete PDFs unter `versendet/`, die Daten dazu als genutzte Entwürfe (MIN-303, MIN-304). Git braucht die App nicht und bringt es nicht mit; ist es installiert, hält es jeden Versand zusätzlich fest (Entscheid 3.11.2026).
- **Jobliste in Google Sheets (optional):** In den Einstellungen „Jobliste in Google Sheets führen“. Die App meldet sich einmal bei Google an (Anmeldung im Browser, Berechtigung nur `drive.file`), legt die Tabelle an, überträgt den Bestand und trägt danach jede neue Stelle und jede Änderung ins Register und in die Liste ein. Die Liste ist nie Quelle: Was dort von Hand geändert wird, übernimmt die App nicht. Ausschalten lässt die Tabelle bestehen. Das Zugangszeichen von Google liegt im Schlüsselbund des Systems.
- **Sicherung:** Knopf „Sicherung erstellen“ in der App. Sie packt den Datenordner als ZIP mit Datum an einen Ort, den die Person wählt (z.B. USB-Stick), und erinnert nach einigen Versänden daran (MIN-359). Ein Konto oder eine Cloud braucht es dafür nicht (Entscheid 3.11.2026).
- **Updates:** Die App prüft beim Start, ob es eine neue Version gibt, und verweist auf den Download.
- **Signatur:** macOS blockiert unsignierte Apps, Windows warnt. Für den Pilot braucht es ein Apple-Entwicklerkonto zum Signieren und Beglaubigen; für Windows eine Signatur oder eine Anleitung zur Warnung.
- **Plattformen:** macOS und Windows. Chromebooks, Tablets und Handys gehen nicht; vor dem Pilot klären, welchen Rechner die Teilnehmenden haben.
- **Anpassungen an der Oberfläche:** Ersteinrichtung, Import der HTML-Vorlage, Empfang der Treffer über Native Messaging, KI-Knöpfe, Antworten für „Stelle prüfen“ und „Stelle speichern“, Häkchen und die Knöpfe „Bewerben“ und „Im RAV eintragen“ in der Übersicht, Link zum Bewerbungsformular und Stand des Ausfüllens pro Bewerbung, Status „im RAV eingetragen“, erweiterte Einstellungen. Host-Prüfung, Token pro Start und CSP bleiben.

### KI-Vermittlung

Ein kleiner Dienst auf dem bestehenden Hosting des Projektinhabers in der Schweiz (MIN-344). Er hält den Anthropic-Schlüssel, damit keiner auf den Rechnern liegt.

- **Schnittstelle:** gleich wie die Messages API von Anthropic. `ki.py` nutzt das Anthropic SDK mit der Adresse der Vermittlung und dem Zugang der Person.
- **Einladung:** Der Projektinhaber erstellt pro Person einen Link mit Einmal-Code. Die App löst ihn ein und erhält einen Zugang. Der Code verfällt nach Gebrauch oder nach 7 Tagen.
- **Grenzen:** Budget pro Person und Monat, Anfragen pro Minute, nur freigegebene Modelle, keine Server-Tools. So taugt die Vermittlung nicht als allgemeiner Zugang zu Claude.
- **Kosten:** pro Aufruf Person, Modell, Tokens und Kosten, ohne Inhalte. Daraus kommen die gemessenen Kosten des Pilots.
- **Inhalte:** werden nur durchgereicht, nie gespeichert oder protokolliert. Sie sind schon in der App pseudonymisiert.
- **Sperren:** Am Ende des Pilots oder bei Verlust eines Rechners wird der Zugang gesperrt; die App meldet das verständlich.
- **Release:** Die Vermittlung wechselt auf einen EU-Anbieter (MIN-337), ohne Update der App. Ein Abo wird ein Zugang mit Budget.

### Eigener API-Schlüssel

Für Personen, die selbst ein Konto bei Anthropic haben, in den **erweiterten Einstellungen** der App.

- **Ablage:** Die App legt den Schlüssel im Schlüsselbund des Systems ab, wie den Zugang zur Vermittlung, nie im Datenordner und nie in der Erweiterung. Er erscheint nie in Protokollen oder Fehlermeldungen. Die App prüft ihn beim Speichern mit einem kleinen Aufruf.
- **Aufrufe:** gehen direkt an die Claude API, nicht über die Vermittlung. Budget und Kostenzählung der Vermittlung entfallen; die App zeigt die Kosten lokal an. Die Pseudonymisierung bleibt.
- **Freigeschaltet:** automatische Suche auf weiteren Seiten, auch LinkedIn (siehe [Regeln für die Erweiterung](#stellensuche-über-den-browser-der-person)). Beim Einschalten erscheint eine Warnung: Die Person trägt Kosten und das Risiko einer Kontosperre selbst, und für die Verarbeitung gilt ihr eigener Vertrag mit Anthropic, auch in den USA.
- **Gleich bleiben:** Absenden und Einwilligungen nur durch die Person, keine Anmeldungen, CAPTCHAs bei der Person, Suche nur auf Start durch die Person.
- **Entfernen:** Löscht die Person den Schlüssel, läuft die App wieder über die Vermittlung, und die automatische Suche ist wieder auf die erlaubten Portale beschränkt.

## Onlinedienst nach dem Pilot

Braucht es nach dem Pilot einen gehosteten Dienst (z.B. für Personen ohne eigenen Rechner oder für Begleitpersonen), läuft dieselbe App in einem Container pro Person (MIN-343). Die Trennung der Daten macht der Container, nicht neuer Mandanten-Code.

```
Browser der Person ──── Portal-Tabs ◀── Erweiterung
   │                          │ Treffer, Inseratstexte
   └──HTTPS──▶ Reverse Proxy (Caddy) ◀──┘
                     │──▶ Anmeldung (z.B. Authelia: Passkey, Einladung)
                     ├─▶ Container Person A: app.py + Typst ──▶ Volume A (Datenordner, verschlüsselt)
                     ├─▶ Container Person B: …
                     └─▶ KI-Aufrufe (pseudonymisiert) ──▶ nur EU
```

- **Server:** 1 virtueller Server mit Docker. 10 Personen brauchen je etwa 100–200 MB RAM; Typst rendert einen Lebenslauf in rund 300 ms.
- **Anmeldung:** über ein bewährtes Werkzeug vor dem Proxy, nicht selbst gebaut. Der Proxy leitet jede Anmeldung fest zum Container dieser Person.
- **Anpassungen:** Die Host-Prüfung erlaubt den öffentlichen Namen, der Server vertraut der Anmeldung des Proxys nur im internen Netz, Uploads sind begrenzt.
- **Sicherung:** täglich, verschlüsselt, an einem zweiten Standort.

Für mehr als etwa 50 Personen reicht ein Container pro Person nicht mehr: Die Kosten und der Betrieb wachsen pro Person. Dann bekommen Register, Entwürfe und Versionen eine Server-Umsetzung derselben Schnittstellen: Datenbank statt YAML, Objektspeicher statt Ordner.

## Ausbildungssuche

Damit auch Schulabgängerinnen und Schulabgänger den Assistenten nutzen können, kommt eine Suche nach Lehrstellen (EFZ, EBA) und Schnupperlehren dazu. Zwei Lehrstellensuchende, die aktuell suchen, machen im Pilot mit (MIN-335). Im Pilot kommen die Lehrstellen per Text einfügen dazu, die Portale folgen in der Erweiterung. Der Ablauf bleibt gleich, die Inhalte unterscheiden sich:

| Thema | Stellensuche | Ausbildungssuche |
|---|---|---|
| Quellen | job-room, jobs.ch, jobscout24, ictjobs, LinkedIn, Karriereseiten | Lehrstellennachweis LENA auf berufsberatung.ch, yousty.ch, Lehrstellenseiten der Betriebe (Quellen und Zugriff zu prüfen, Abfragen wie bei der Stellensuche über die Erweiterung) |
| Suchprofil | Rollen, Keywords, Region, Pensum | Berufe (Berufswahl), Region und Schulweg, Lehrbeginn, Schulniveau |
| Passung | Erfahrung und Fähigkeiten gegen Anforderungen | Interessen, Stärken, Schulniveau, Ergebnisse von Eignungstests (z.B. Multicheck, Basic-Check), Schnuppererfahrung |
| Unterlagen | Lebenslauf, Anschreiben, Arbeitszeugnisse, Zertifikate | Lebenslauf für Schülerinnen und Schüler (Schule, Sprachen, Hobbys, Schnupperlehren), Motivationsschreiben, Schulzeugnisse, Testergebnisse, Schnupperberichte |
| Einstieg | Unterlagen hochladen oder Interview | Fast immer Interview oder HTML-Vorlage, weil es noch keine Unterlagen gibt |
| Job-Room | Angaben für die Arbeitsbemühungen | Entfällt |
| Begleitung | Selten | Eltern, Lehrperson oder Berufsberatung lesen oft mit: Ein Lesezugang für Begleitpersonen wird mit dem Onlinedienst wichtig; im Pilot sitzen sie dabei. |

**Besonderheiten:**

- **Minderjährige:**
  - In die Bearbeitung ihrer Daten willigen sie selbst ein, sofern sie urteilsfähig sind. Im Pilot werden die Eltern zusätzlich informiert und stimmen zu, weil die KI in der Testphase auch in den USA verarbeitet.
  - Die Lehrstellensuche ist kostenlos; eine Zahlung und damit die Zustimmung der Eltern zu einem Abo entfallen.
- **Zeitpunkt:** Lehrstellen werden oft schon im Herbst und Winter vor dem Lehrbeginn vergeben, und die zwei suchen jetzt. Darum beginnen sie mit dem Einstieg (MIN-332, MIN-333), bevor die App fertig ist: Die Interviews führt der Projektinhaber mit ihnen in Claude Code.
- **Technik:**
  - Das Register unterscheidet die Art einer Ausschreibung (Stelle, Lehrstelle, Schnupperlehre).
  - Es braucht ein Theme für Lebensläufe von Schülerinnen und Schülern und Vorlagen für Motivationsschreiben (in der Regel Sie-Form).

## Datenschutz und Recht

**Besonders schützenswerte Daten:**

- Lebensläufe enthalten Foto, Geburtsdatum, Adresse, Bewerbungsstände und Absagen.
- Job-Room-Angaben verraten die Arbeitslosigkeit. Sie können als Daten über Massnahmen der sozialen Hilfe besonders schützenswert sein (Art. 5 DSG).
- Bei der Ausbildungssuche kommen Daten von Minderjährigen dazu (Schulzeugnisse, Testergebnisse).
- Massgeblich ist das DSG, bei Personen in der EU zusätzlich die DSGVO.

**Schon im Pilot nötig:**

- **Datenschutzerklärung und Einwilligung:** Sie sagen, dass die Daten auf dem Rechner der Person liegen, was an die KI geht (pseudonymisiert, Verarbeitung auch in den USA) und dass die Aufrufe über die Vermittlung des Projektinhabers (Hosting in der Schweiz) und sein Konto bei Anthropic laufen. Die Vermittlung reicht Inhalte nur durch und protokolliert nur Kosten.
- **Auftragsverarbeitung:** Vertrag mit Anthropic und mit dem Anbieter des Hostings der Vermittlung, im Release mit dem EU-Anbieter. Zu bestätigen ist, dass API-Daten nicht für das Training verwendet werden, und wie lange sie aufbewahrt werden.
- **Ende des Pilots:** Der Zugang der Person wird gesperrt, ihre Kostenprotokolle nach der Auswertung gelöscht. Ihre Daten bleiben bei ihr; löschen kann sie sie selbst.
- **Datensparsam:** keine Tracker und keine Telemetrie; die App protokolliert lokal und ohne Inhalte.
- **Jobliste in Google Sheets (optional):** Nur wenn die Person sie einschaltet. Die App meldet sich dafür mit Google an und erhält nur Zugriff auf Dateien, die sie selbst angelegt hat (Berechtigung `drive.file`). In der Liste stehen Firma, Stelle, Status und Notizen, aber keine RAV-Angaben und keine Unterlagen. Die Datenschutzerklärung nennt Google als Empfänger, wenn die Liste eingeschaltet ist.
- **Ausfüllen von Formularen:** Die Angaben gehen erst an Arbeitgeber oder RAV, wenn die Person selbst absendet. Die KI sieht dabei nur Feldbeschriftungen und pseudonymisierte Texte.
- **RAV-Einträge** verraten die Arbeitslosigkeit und sind besonders schützenswert. Sie bleiben im Datenordner und im Job-Room und gehen nie an die KI.
- **Eigener API-Schlüssel:** Die Datenschutzerklärung sagt, dass die Aufrufe dann unter dem Vertrag der Person direkt an Anthropic gehen und nicht über die Vermittlung.

**Für den Onlinedienst zusätzlich:** Hosting der Daten selbst; Export und Löschung des Kontos; inaktive Konten werden 12 Monate nach der letzten Anmeldung gelöscht, mit Vorwarnung.

**Für das Abo zusätzlich:**

- Nutzungsbedingungen mit Haftungsbegrenzung: Die Person prüft und verantwortet ihre Unterlagen.
- Bei Minderjährigen die Zustimmung der Eltern.
- Träger: Einzelfirma oder GmbH.
- Mehrwertsteuer erst ab CHF 100'000 Umsatz.

**Lizenz:** Der Code steht unter GPL-3.0. Soll auch der Betrieb als Dienst zur Offenlegung von Änderungen verpflichten, ist ein Wechsel auf AGPL-3.0 zu prüfen.

## Sicherheit

**App im Pilot:**

- Der Server läuft nur auf `127.0.0.1`. Host-Prüfung, Token pro Start und CSP bleiben; Inhalte werden nur als Text eingesetzt.
- Auf den Rechnern liegt kein API-Schlüssel, nur der Zugang zur Vermittlung im Schlüsselbund des Systems. Er erscheint nie in Protokollen oder Fehlermeldungen.
- Die Vermittlung speichert Zugänge nur als Hash, prüft Budget und Modelle bei jedem Aufruf und hält den Anthropic-Schlüssel als Geheimnis auf dem Server, nie im Repo.
- Die Erweiterung hat fest nur Berechtigungen für die erlaubten Portale; den Zugriff auf alle Seiten erhält sie nur mit der Erlaubnis der Person und nutzt ihn nur für Vorgänge, die die Person ausgelöst hat. Sie öffnet nur Tabs für Bewerbungen, die die App ihr nennt. Treffer, Inserate und Formularfelder nimmt die App nur über Native Messaging von der eigenen Erweiterung an (Chrome prüft deren ID) und prüft sie wie jede Eingabe von aussen; Text von fremden Seiten ist Daten, keine Anweisung.
- Dateien zum Hochladen gibt die App nur für die gewählte Bewerbung heraus und nur aus dem Datenordner.
- Ein eigener API-Schlüssel liegt nur im Schlüsselbund des Systems.
- Importierte Dateien (HTML-Vorlage, Lebenslauf) werden geprüft und nie als Code ausgeführt.
- Fotos werden neu kodiert und ihre Metadaten entfernt.
- Die Pakete werden in der CI gebaut und signiert; Abhängigkeiten werden geprüft.

**Onlinedienst zusätzlich:**

- Anmeldung mit Passkeys oder E-Mail-Link; Sitzungen mit sicheren Cookies; Schutz gegen CSRF.
- Die Daten jeder Person liegen in einem eigenen Container und Volume. Ein Test stellt sicher, dass kein Weg zu fremden Daten führt.
- Anfragen, Uploads und KI-Aufrufe sind pro Person begrenzt.

## Abo (Phase 2, Vorschlag)

**Preis:** CHF 12–19 pro Monat, monatlich kündbar. Als Alternative ein „Paket Stellensuche“ über 3 Monate. Für Schülerinnen und Schüler ist die Lehrstellensuche kostenlos (Entscheid 2.11.2026). Ihr Zugang zur Vermittlung hat trotzdem ein Budget; die Kosten trägt das Abo der übrigen Personen oder eine Unterstützung (z.B. Stiftung, Gemeinde), zu klären nach dem Pilot.

**KI-Kontingent im Preis:** zum Beispiel 30 Anschreiben pro Monat. Es deckelt die Kosten pro Person.

**Zahlung:** über Payrexx (Karte, TWINT), Tarif ab CHF 19 pro Monat, Gebühren rund 1.3 %.

- Ob TWINT für wiederkehrende Zahlungen geht, ist in der Dokumentation widersprüchlich und muss mit Payrexx geklärt werden.
- Alternative: Stripe.

**Grobe Rechnung, zu prüfen:**

- Die Fixkosten eines Onlinedienstes (Server, Sicherung, Domain, Zahlungsanbieter) liegen bei etwa CHF 100–150 pro Monat. Mit der App und einem Abo-Zugang zur Vermittlung fielen die Server für Daten und deren Sicherung weg.
- Pro Person kommen KI-Kosten von CHF 5–6 dazu.
- Bei CHF 15 Abo bleiben etwa CHF 8 pro Person. Ab etwa 15–20 zahlenden Personen sind die Fixkosten gedeckt, ohne die eigene Arbeitszeit.

## Offene Entscheide

1. **LinkedIn:** Automatische Suche dort nur mit eigenem Schlüssel und nach Warnung (Entscheid 3.11.2026). Nach dem Pilot prüfen, ob es Einschränkungen von Konten gab.
2. **Signatur der App:** Apple-Entwicklerkonto für den Pilot; unter Windows Signatur oder Anleitung (MIN-342).
3. **Nach dem Pilot:** gehosteter Onlinedienst (MIN-343), App mit Abo-Zugang zur Vermittlung oder beides?
4. **Kostenlose Konten:** Dürfen sie im Release über die Claude API in den USA laufen (MIN-337)? Empfehlung: nicht für Schülerinnen und Schüler. Sie sind meist minderjährig, ihre Konten sind immer kostenlos und laufen darum im Release wie alle anderen nur in der EU.
5. **EU-Anbieter im Release:** Bedrock EU oder Vertex AI „eu“ (MIN-337)?
6. **Hosting-Anbieter:** Die Vermittlung läuft im Pilot auf dem bestehenden Hosting; für den Onlinedienst wird nach dem Pilot entschieden.
7. **Träger und Rechtsform** für das Abo. Erst nach dem Pilot zu entscheiden.
8. **RAV auf Papier:** Welche RAV der Teilnehmenden verlangen den Nachweis noch auf Papier, und reicht dann eine Liste zum Ausdrucken?

## Arbeitsschritte (Linear)

Meilenstein **„Pilot: lokale App“**:

| Ticket | Inhalt | Priorität |
|---|---|---|
| MIN-332 | Einstieg per Interview: Skill `einstieg` (Stellen- und Lehrstellensuche) | hoch |
| MIN-333 | Einstieg per HTML-Vorlage zum Ausfüllen, mit Import | hoch |
| MIN-334 | Pseudonymisierung vor jedem KI-Aufruf | hoch |
| MIN-335 | Lehrstellensuche: Grundlagen für den Pilot | hoch |
| MIN-342 | Lokale App: Installationspaket für macOS und Windows, Ersteinrichtung | hoch |
| MIN-344 | KI-Vermittlung: Zugang pro Person statt API-Schlüssel auf dem Rechner | hoch |
| MIN-339 | Browser-Erweiterung: Grundgerüst, automatische Suche auf den erlaubten Portalen mit IP und Login der Person, Übergabe an die App | hoch |
| MIN-345 | Erweiterung: Knöpfe „Stelle prüfen“ und „Stelle speichern“ auf jeder Seite (nach MIN-339, MIN-338) | hoch |
| MIN-346 | Bewerbungsformulare vorausfüllen und Unterlagen hochladen, passende Zertifikate als ZIP (nach MIN-339, MIN-338) | hoch |
| MIN-347 | RAV-Arbeitsbemühungen im Job-Room vorausfüllen (nach MIN-339) | hoch |
| MIN-348 | Erweiterte Einstellungen: eigener API-Schlüssel hebt die Beschränkung auf Portale auf (nach MIN-338, MIN-339) | mittel |
| MIN-338 | KI-Modul `ki.py` (nach MIN-334) | mittel |
| MIN-359 | Sicherung erstellen: Datenordner als ZIP, mit Erinnerung | mittel |
| MIN-340 | Betrieb im Pilot: Vermittlung betreiben, Einladungen, Verteilung und Updates, Kosten | mittel |
| MIN-336 | Rechtstexte: Datenschutz, Einwilligung (auch der Eltern), Auftragsverarbeitung | mittel |
| MIN-341 | Pilot durchführen und auswerten (nach MIN-336, MIN-338 bis MIN-340, MIN-342, MIN-344 bis MIN-348) | mittel |

Meilenstein **„Onlinedienst: Release (Abo, EU)“**:

| Ticket | Inhalt |
|---|---|
| MIN-337 | KI-Verarbeitung nur in der EU |
| MIN-343 | Onlinedienst: Hosting mit Proxy, Anmeldung, Container pro Person, Sicherung (falls nach dem Pilot entschieden) |

Später folgen: Zahlung und Abo, Nutzungsbedingungen, Lesezugang für Begleitpersonen, Lehrstellenportale in der Erweiterung, Datenbank statt Container pro Person.

## Quellen

- Claude-Modelle und Preise: [Anthropic Pricing](https://www.anthropic.com/pricing)
- Bedrock, Regionen pro Modell: [Regional availability by models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html), [Claude Sonnet 5.5 auf Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html)
- Payrexx und TWINT: [Gebühren](https://payrexx.com/en-ch/guides/zahlungsgebuehren-marge-handel), [TWINT in Payrexx Pay](https://docs.payrexx.com/merchant/bezahldienste/payrexx-pay/zahlungsmittel/twint)
