# Konzept: Bewerbungsassistent als Onlinedienst (MIN-305)

Stand 2.11.2026 (freigegeben); ersetzt den Entwurf vom 26.10.2026. Grundlage für die Meilensteine „Onlinedienst: Pilot“ und „Onlinedienst: Release (Abo, EU)“ im Linear-Projekt.

## Entscheide

| Frage | Entscheid (2.11.2026) |
|---|---|
| Zielgruppe | Zuerst ein **Pilot mit 5–10 Personen aus dem Bekanntenkreis**, betrieben vom Projektinhaber. Nach dem Pilot wird über einen öffentlichen Dienst entschieden. |
| Kernstück | Die **Stellensuche**: Sie dauert heute am längsten und gehört darum in den Pilot. |
| KI | Der Dienst ruft die KI mit eigenem Schlüssel auf und trägt die Kosten. In der **Testphase** (Pilot, eventuell kostenlose Konten) läuft sie über die **Claude API von Anthropic**, auch in den USA. Im **Release** gibt es **keine Verarbeitung in den USA** mehr, nur noch in der EU. |
| Modell | Für die Anschreiben werden Sonnet 5.5 und Opus 5.5 im Pilot verglichen. |
| Personendaten an die KI | Sie werden **von Anfang an**, schon vor dem ersten KI-Aufruf im Pilot, **durch Platzhalter ersetzt** (Pseudonymisierung). So gehen auch in der Testphase nicht alle Daten in die USA. |
| LinkedIn | **Halbautomatisch:** Die Person sitzt am Rechner und öffnet die Stellenübersicht selbst. Wie es weitergeht, wird nach ersten Erfahrungen entschieden. |
| Einstieg | Der Einstieg geht auf drei Wegen: Unterlagen hochladen, ein **Interview mit Claude** oder eine **HTML-Vorlage**, die mit Daten ausgefüllt wird. |
| Ausbildungssuche | Damit auch Schulabgängerinnen und Schulabgänger den Dienst nutzen können. **2 Lehrstellensuchende**, die aktuell suchen, **machen im Pilot mit**; die Grundlagen kommen darum schon in den Pilot, ausgebaut wird in der fertigen Version. |
| Hosting | Wird später entschieden. |
| Finanzierung | **Kleines Abo** ab dem öffentlichen Dienst. Der Pilot ist gratis und dient dazu, die Kosten pro Person zu messen. |

Die lokale Variante bleibt bestehen. Sie ist für technisch Versierte die datensparsamste Wahl.

## Zielgruppen und Nutzen

- **Stellensuchende ohne technische Kenntnisse:** Sie brauchen kein Python, kein Git und keine Kommandozeile. Sie arbeiten im Browser nach demselben Ablauf wie lokal: Suche → Stelle → Unterlagen → Prüfung → Versand.
  - Nutzen: Passende Stellen finden sie schneller. Pro Stelle entstehen ein passender Lebenslauf und ein Anschreiben im eigenen Stil, in dem jede Aussage belegt ist. Dazu kommen eine Übersicht über alle Bewerbungen und die Angaben für den Job-Room.
- **Schulabgängerinnen und Schulabgänger** (2 im Pilot, ausgebaut in der fertigen Version): Sie suchen Lehrstellen und Schnupperlehren und erstellen ihr erstes Bewerbungsdossier (siehe [Ausbildungssuche](#ausbildungssuche)).

## Phasen

1. **Pilot = Testphase** (etwa 3 Monate, gratis, auf Einladung, KI über die Claude API). Er soll drei Fragen klären: Spart die Suche wirklich Zeit? Kommen nicht versierte Personen damit zurecht? Was kostet eine aktive Person pro Monat?
2. **Release: öffentlicher Dienst mit Abo**, KI-Verarbeitung nur in der EU, Ausbildungssuche ausgebaut. Er kommt nur, wenn der Pilot die Erfolgskriterien erfüllt.

Erfolgskriterien des Pilots:

- Eine wöchentliche Suche samt Bewertung der Treffer dauert für die Person unter 15 Minuten.
- Mindestens 5 Personen schicken je mindestens 3 Bewerbungen ab, die mit dem Dienst erstellt wurden.
- Beide Lehrstellensuchenden schicken Bewerbungen mit Lebenslauf und Motivationsschreiben aus dem Assistenten ab.
- Eine Bewerbung dauert von der Stelle bis zu den fertigen PDFs unter 30 Minuten.
- Die KI-Kosten liegen unter CHF 10 pro aktive Person und Monat (gemessen, nicht geschätzt).
- Kein Datenschutzvorfall, und keine Person sieht Daten einer anderen.
- Die Rückmeldungen zeigen, welche Schritte ohne Hilfe nicht klappen.

## Umfang im Pilot

| Enthalten | Nicht im Pilot |
|---|---|
| Konto auf Einladung, Anmeldung mit Passkey oder E-Mail-Link | Versand durch den Dienst (die Person schickt selbst ab) |
| **Lehrstellensuche, Grundlagen:** Art der Ausschreibung, Suchprofil nach Berufen, Schülerlebenslauf, Motivationsschreiben; Lehrstellen per Text einfügen | Lehrstellenportale in der Erweiterung, Lesezugang für Begleitpersonen |
| **Einstieg** auf drei Wegen (siehe unten): Lebenslauf, Suchprofil, Stilprofil, Bausteine | Erinnerungen per E-Mail |
| **Stellensuche** über die Browser-Erweiterung auf job-room, jobs.ch, jobscout24, ictjobs und Karriereseiten nach dem Suchprofil, LinkedIn halbautomatisch | Coaches und Begleitpersonen |
| KI-Bewertung jedes Treffers (Note 1–6 mit Begründung), Abgleich gegen Doppelbewerbungen | |
| Stelle erfassen: übernehmen aus Suche oder offenem Inserat, oder Text einfügen | Französisch, Englisch |
| Lebenslauf, Themes, Foto (Metadaten werden entfernt), Lebenslauf-Variante vorschlagen (regelbasiert wie heute) | |
| Anschreiben-Entwurf im eigenen Stil (KI) mit Überarbeitung | |
| Formale Prüfung (wie heute) und inhaltliche Prüfung (KI) | |
| Register, Versand festhalten, Job-Room-Angaben zum Kopieren | |
| Entwürfe und Versionen, Export aller Daten, Löschen des Kontos | |

## Einstieg: drei Wege, ein Ergebnis

Der Einstieg ist die grösste Hürde für nicht versierte Personen. Lokal entstehen Lebenslauf, Stilprofil und Bausteine heute in einer Claude-Sitzung. Für alle drei Wege gilt: Das Ergebnis ist immer gleich, nämlich `cv.yaml`, das Suchprofil, das Stilprofil und die Bausteine. Die Person bestätigt jede Angabe, bevor sie gilt.

| Weg | Wie | Geeignet für |
|---|---|---|
| **Unterlagen hochladen** | Bisherigen Lebenslauf (PDF oder Text) und 2–3 frühere Anschreiben hochladen. Die KI liest daraus die Angaben und den Stil heraus. | Personen mit bestehenden Unterlagen |
| **Interview mit Claude** | Claude fragt Schritt für Schritt nach: Ausbildung, Stationen, Stärken, Ziele, Region, Pensum, Ton (Du/Sie). Fehlende Belege fragt es gezielt nach. Im Dienst ist das ein geführtes Gespräch. Mit eigenem Claude (claude.ai, Desktop-App) geht es über einen Skill `einstieg`, auch für die lokale Variante. | Personen ohne Unterlagen, Schulabgängerinnen und Schulabgänger |
| **HTML-Vorlage** | Eine einzelne HTML-Datei mit Formular für Lebenslauf, Suchprofil und Stil. Sie läuft ohne Server im Browser, und die Daten bleiben lokal, bis die Person sie hochlädt. Man füllt sie von Hand aus, oder Claude füllt sie aus dem Interview vor. Sie speichert eine Datei zum Hochladen in den Dienst oder für den lokalen Datenordner. | Wer lieber selbst ausfüllt, offline arbeitet oder mit Begleitung (Eltern, Beratung) ausfüllt |

Die HTML-Vorlage prüft die Eingaben mit denselben Regeln wie das Register und der Lebenslauf. Beim Hochladen prüft der Dienst nochmals, denn die Datei ist eine Eingabe von aussen. Ohne frühere Anschreiben entsteht das Stilprofil aus dem Interview und aus 2–3 Beispielsätzen, die die Person auswählt oder anpasst.

## Stellensuche über den Browser der Person

Die Suche ist das Kernstück. Stellenportale und Bewertungsseiten (job-room, LinkedIn, kununu, viele Karriereseiten) sperren aber Adressen von Rechenzentren und KI-Anbietern häufig. Ein Server des Dienstes oder die Web-Abfrage der KI kämen dort nicht zuverlässig durch. Der Skill `jobsuche` funktioniert heute nur, weil er im eingeloggten Browser der Person abfragt.

**Grundsatz:** Der Dienst und die KI rufen selbst keine fremden Websites ab. Abfragen bei Portalen laufen im Browser der Person, mit ihrer IP und ihren Logins, und nur, solange sie am Rechner ist und die Suche gestartet hat. Der Dienst erhält nur das Ergebnis, zum Beispiel eine Trefferliste oder einen Inseratstext. Bewertung, Abgleich und Jobliste laufen danach im Dienst.

| Weg | Wie | Einschätzung |
|---|---|---|
| **Browser-Erweiterung** (Empfehlung) | Die Erweiterung des Dienstes (Chrome, Firefox, Edge) sucht in Portal-Tabs nach dem Suchprofil, gleich wie der Skill `jobsuche` mit `fetch` auf derselben Seite, und holt die Volltexte. Die Treffer gehen an den Dienst. | Nutzt die IP und die Logins der Person. Muss einmal installiert und bei Änderungen der Portale nachgeführt werden. Auf dem Handy nur eingeschränkt (Firefox Android, Safari iOS). |
| **Text einfügen** | Inseratstext kopieren und einfügen | Geht immer, ohne Installation; der Ersatz, wenn die Erweiterung fehlt |
| **Job-Abos per E-Mail** | Job-Abos der Portale an eine persönliche Adresse des Dienstes weiterleiten; der Dienst liest Titel, Firma und Link | Stellenvorschläge ganz ohne Abfragen bei den Portalen. Den Volltext holt die Erweiterung, oder die Person fügt ihn ein. |
| **Offizielle Schnittstellen** | Partnerzugänge, z.B. für job-room oder JobCloud | Stabil und rechtlich sauber, aber wohl nur mit Vertrag; zu prüfen |
| ~~Proxys mit Privatanschlüssen oder ein VPN~~ | Server-Abfragen über fremde Privatanschlüsse leiten | **Abgelehnt:** umgeht die Sperren bewusst, verletzt die Nutzungsbedingungen und ist rechtlich riskant |

**Regeln für die Erweiterung:**

- **Berechtigungen:** nur für die Portale im Suchprofil und den Dienst selbst.
- **Auslöser:** Sie sucht nur, wenn die Person die Suche startet, und hält die Grenzen aus dem Skill ein (z.B. höchstens 3 Seiten pro Suchbegriff und Ort). Im Hintergrund sucht sie nicht.
- **Keine Aktionen auf den Portalen:** Sie bewirbt nicht und füllt keine Formulare aus. CAPTCHAs bleiben bei der Person.
- **LinkedIn halbautomatisch:**
  - Die Person sitzt am Rechner und ruft die Stellenübersicht selbst auf (Suche oder Empfehlungen).
  - Auf Knopfdruck liest die Erweiterung nur diese geöffnete Seite und das offene Inserat.
  - Sie navigiert nicht selbständig und fragt nichts im Hintergrund ab.
  - Die Nutzungsbedingungen von LinkedIn verbieten Automatisierung ausdrücklich. Ob und wie es weitergeht, wird nach den ersten Erfahrungen entschieden.
- **Wartung:** Sie wird zentral aktualisiert. Ändert ein Portal seine Seiten, ist das ein Update für alle.

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
| Treffer bewerten (Passung 1–6) | Haiku 5.5 | 5'000 / 1'000 | ca. 0.1 Rappen |
| Anschreiben-Entwurf | Sonnet 5.5 | 10'000 / 8'000 | ca. 10 Rappen |
| Überarbeitung (je Runde) | Sonnet 5.5 | 12'000 / 6'000 | ca. 8 Rappen |
| Inhaltliche Prüfung | Sonnet 5.5 | 15'000 / 3'000 | ca. 6 Rappen |
| Einstieg aus Unterlagen (einmalig) | Opus 5.5 | 30'000 / 15'000 | ca. 40 Rappen |
| Einstieg als Interview (einmalig, etwa 20 Fragen) | Opus 5.5 | 200'000 / 20'000, mit Caching | ca. CHF 0.50–1.50 |

Daraus ergibt sich:

- **Eine Bewerbung** (Entwurf, 2 Überarbeitungen, Prüfung) kostet etwa **30–35 Rappen** mit Sonnet 5.5 und etwa das Doppelte mit Opus 5.5.
- **Eine aktive Person pro Monat** (15 Bewerbungen, 300 bewertete Treffer) kostet etwa **CHF 5–6** mit Sonnet 5.5 und **CHF 10–12** mit Opus 5.5.
- **Prompt-Caching** senkt den Eingabe-Anteil: Suchprofil, Stilprofil, Bausteine und Lebenslauf bleiben pro Person gleich. Der grössere Teil der Kosten ist aber die Ausgabe.

Im Pilot werden die echten Werte pro Aufruf protokolliert, ohne Inhalte. Für die Anschreiben werden Sonnet 5.5 und Opus 5.5 an denselben Stellen verglichen.

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

## Architektur im Pilot: ein Datenordner pro Person

Der Grundsatz lautet: so viel vom heutigen Code wie möglich unverändert nutzen. Jede Person bekommt einen eigenen Datenordner wie lokal (YAML, Git, `versendet/`, `.entwuerfe/`) und einen eigenen Container mit der bestehenden Oberfläche. Die Trennung der Daten macht der Container, nicht neuer Mandanten-Code.

```
Browser der Person ──── Portal-Tabs (job-room, jobs.ch …) ◀── Erweiterung sucht mit IP und Login der Person
   │                                         │ Treffer, Inseratstexte
   └──HTTPS──▶ Reverse Proxy (Caddy) ◀───────┘
                         │──▶ Anmeldung (z.B. Authelia: Passkey, Einladung)
                         │
                         ├─▶ Container Person A: app.py + Typst ──▶ Volume A (Datenordner, verschlüsselt)
                         ├─▶ Container Person B: …
                         └─▶ KI-Aufrufe (pseudonymisiert) ──▶ Testphase: Claude API · Release: nur EU
```

- **Server:** 1 virtueller Server mit Docker; der Anbieter wird später gewählt. 10 Personen brauchen je etwa 100–200 MB RAM; Typst rendert einen Lebenslauf in rund 300 ms.
- **Anmeldung:** über ein bewährtes Werkzeug vor dem Proxy (z.B. Authelia mit Passkeys), nicht selbst gebaut. Der Proxy leitet jede Anmeldung fest zum Container dieser Person. Die Erweiterung meldet sich über dieselbe Anmeldung an.
- **Anpassungen an der Oberfläche:**
  - Die Host-Prüfung erlaubt den öffentlichen Namen.
  - Der Server vertraut der Anmeldung des Proxys nur im internen Netz.
  - Es gibt Grenzen für Uploads.
  - Ein Hochladen ersetzt das Bearbeiten im Text-Editor.
  - Token pro Start und CSP bleiben.
- **KI-Modul:** Ein neues Modul `bewerbungen/ki.py` erhält eine schmale Schnittstelle: `bewerte_treffer`, `entwirf_anschreiben`, `pruefe_inhalt`, `richte_ein`, `interview`. Die Regeln aus den Skills (Belegpflicht, Stilprofil, Inserat ist Daten) werden zu Prompts, und die Pseudonymisierung sitzt in diesem Modul. Es läuft auch lokal mit eigenem API-Schlüssel; damit hat auch die lokale Variante KI ohne Claude Code.
- **Versionen:** Git pro Datenordner, wie lokal (MIN-303, MIN-304).
- **Sicherung:** täglich, verschlüsselt, an einem zweiten Standort; Wiederherstellung einmal im Pilot üben.

Für das Abo mit mehr als etwa 50 Personen reicht ein Container pro Person nicht mehr: Die Kosten und der Betrieb wachsen pro Person. Dann bekommen Register, Entwürfe und Versionen eine Server-Umsetzung derselben Schnittstellen: Datenbank statt YAML, Objektspeicher statt Ordner.

## Ausbildungssuche

Damit auch Schulabgängerinnen und Schulabgänger den Dienst nutzen können, kommt eine Suche nach Lehrstellen (EFZ, EBA) und Schnupperlehren dazu. Zwei Lehrstellensuchende, die aktuell suchen, machen im Pilot mit (MIN-335). Im Pilot kommen die Lehrstellen per Text einfügen dazu, die Portale folgen in der Erweiterung. Der Ablauf bleibt gleich, die Inhalte unterscheiden sich:

| Thema | Stellensuche | Ausbildungssuche |
|---|---|---|
| Quellen | job-room, jobs.ch, jobscout24, ictjobs, LinkedIn, Karriereseiten | Lehrstellennachweis LENA auf berufsberatung.ch, yousty.ch, Lehrstellenseiten der Betriebe (Quellen und Zugriff zu prüfen, Abfragen wie bei der Stellensuche über die Erweiterung) |
| Suchprofil | Rollen, Keywords, Region, Pensum | Berufe (Berufswahl), Region und Schulweg, Lehrbeginn, Schulniveau |
| Passung | Erfahrung und Fähigkeiten gegen Anforderungen | Interessen, Stärken, Schulniveau, Ergebnisse von Eignungstests (z.B. Multicheck, Basic-Check), Schnuppererfahrung |
| Unterlagen | Lebenslauf, Anschreiben, Arbeitszeugnisse, Zertifikate | Lebenslauf für Schülerinnen und Schüler (Schule, Sprachen, Hobbys, Schnupperlehren), Motivationsschreiben, Schulzeugnisse, Testergebnisse, Schnupperberichte |
| Einstieg | Unterlagen hochladen oder Interview | Fast immer Interview oder HTML-Vorlage, weil es noch keine Unterlagen gibt |
| Job-Room | Angaben für die Arbeitsbemühungen | Entfällt |
| Begleitung | Selten | Eltern, Lehrperson oder Berufsberatung lesen oft mit: Ein Lesezugang für Begleitpersonen wird hier wichtig. |

**Besonderheiten:**

- **Minderjährige:**
  - In die Bearbeitung ihrer Daten willigen sie selbst ein, sofern sie urteilsfähig sind. Im Pilot werden die Eltern zusätzlich informiert und stimmen zu, weil die KI in der Testphase auch in den USA verarbeitet.
  - Für ein kostenpflichtiges Abo braucht es die Zustimmung der Eltern.
- **Zeitpunkt:** Lehrstellen werden oft schon im Herbst und Winter vor dem Lehrbeginn vergeben, und die zwei suchen jetzt. Darum beginnen sie mit dem Einstieg (MIN-332, MIN-333) und der lokalen Variante, bevor der Dienst läuft.
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

- **Datenschutzerklärung und Einwilligung:** Sie sagen, wo die Daten liegen, was an die KI geht (pseudonymisiert, Verarbeitung auch in den USA) und wie lange die Daten gespeichert bleiben.
- **Auftragsverarbeitung:** Verträge mit dem Hosting-Anbieter und mit Anthropic, im Release mit dem EU-Anbieter. Zu bestätigen ist, dass API-Daten nicht für das Training verwendet werden.
- **Löschung:** Nach dem Pilot werden die Daten exportiert und gelöscht, ausser die Person will weitermachen. Inaktive Konten werden 12 Monate nach der letzten Anmeldung gelöscht, mit Vorwarnung.
- **Datensparsamer Betrieb:** keine Tracker, Protokolle ohne Inhalte.

**Für das Abo zusätzlich:**

- Nutzungsbedingungen mit Haftungsbegrenzung: Die Person prüft und verantwortet ihre Unterlagen.
- Bei Minderjährigen die Zustimmung der Eltern.
- Träger: Einzelfirma oder GmbH.
- Mehrwertsteuer erst ab CHF 100'000 Umsatz.

**Lizenz:** Der Code steht unter GPL-3.0. Soll auch der Betrieb als Dienst zur Offenlegung von Änderungen verpflichten, ist ein Wechsel auf AGPL-3.0 zu prüfen.

## Sicherheit

- Anmeldung mit Passkeys oder E-Mail-Link; Sitzungen mit sicheren Cookies; Schutz gegen CSRF.
- Die Daten jeder Person liegen in einem eigenen Container und Volume. Ein Test stellt sicher, dass kein Weg zu fremden Daten führt.
- Anfragen, Uploads und KI-Aufrufe sind pro Person begrenzt. Das schützt vor Missbrauch und vor Kosten.
- Die Erweiterung hat nur die nötigen Berechtigungen. Was sie schickt, prüft der Dienst wie jede Eingabe von aussen.
- Hochgeladene Dateien (HTML-Vorlage, Lebenslauf) werden geprüft und nie als Code ausgeführt.
- Fotos werden serverseitig neu kodiert und ihre Metadaten entfernt.
- Die bestehende CSP bleibt, Inhalte werden nur als Text eingesetzt.
- Abhängigkeiten und Container-Images werden in der CI geprüft.

## Abo (Phase 2, Vorschlag)

**Preis:** CHF 12–19 pro Monat, monatlich kündbar. Als Alternative ein „Paket Stellensuche“ über 3 Monate. Für die Ausbildungssuche wäre ein Paket über die Zeit der Lehrstellensuche passend.

**KI-Kontingent im Preis:** zum Beispiel 30 Anschreiben pro Monat. Es deckelt die Kosten pro Person.

**Zahlung:** über Payrexx (Karte, TWINT), Tarif ab CHF 19 pro Monat, Gebühren rund 1.3 %.

- Ob TWINT für wiederkehrende Zahlungen geht, ist in der Dokumentation widersprüchlich und muss mit Payrexx geklärt werden.
- Alternative: Stripe.

**Grobe Rechnung, zu prüfen:**

- Die Fixkosten (Server, Sicherung, Domain, Zahlungsanbieter) liegen bei etwa CHF 100–150 pro Monat.
- Pro Person kommen KI-Kosten von CHF 5–6 dazu.
- Bei CHF 15 Abo bleiben etwa CHF 8 pro Person. Ab etwa 15–20 zahlenden Personen sind die Fixkosten gedeckt, ohne die eigene Arbeitszeit.

## Offene Entscheide

1. **LinkedIn:** Wie geht es nach den ersten Erfahrungen mit der halbautomatischen Übernahme weiter?
2. **Kostenlose Konten:** Dürfen sie im Release über die Claude API in den USA laufen (MIN-337)?
3. **EU-Anbieter im Release:** Bedrock EU oder Vertex AI „eu“ (MIN-337)?
4. **Hosting-Anbieter:** zuerst für die Testphase (MIN-340), über das Hosting im Release wird später entschieden.
5. **Träger und Rechtsform** für das Abo. Erst nach dem Pilot zu entscheiden.

## Arbeitsschritte (Linear)

Meilenstein **„Onlinedienst: Pilot“**:

| Ticket | Inhalt | Priorität |
|---|---|---|
| MIN-332 | Einstieg per Interview: Skill `einstieg` (Stellen- und Lehrstellensuche) | hoch |
| MIN-333 | Einstieg per HTML-Vorlage zum Ausfüllen, mit Import | hoch |
| MIN-334 | Pseudonymisierung vor jedem KI-Aufruf | hoch |
| MIN-335 | Lehrstellensuche: Grundlagen für den Pilot | hoch |
| MIN-339 | Browser-Erweiterung: Stellensuche mit IP und Login der Person, LinkedIn halbautomatisch | hoch |
| MIN-338 | KI-Modul `ki.py` (nach MIN-334) | mittel |
| MIN-340 | Betrieb: Proxy, Anmeldung, Container pro Person, Sicherung | mittel |
| MIN-336 | Rechtstexte: Datenschutz, Einwilligung (auch der Eltern), Auftragsverarbeitung | mittel |
| MIN-341 | Pilot durchführen und auswerten (nach MIN-336, MIN-338, MIN-339, MIN-340) | mittel |

Meilenstein **„Onlinedienst: Release (Abo, EU)“**:

| Ticket | Inhalt |
|---|---|
| MIN-337 | KI-Verarbeitung nur in der EU |

Später folgen: Zahlung und Abo, Nutzungsbedingungen, Lesezugang für Begleitpersonen, Lehrstellenportale in der Erweiterung, Datenbank statt Container pro Person.

## Quellen

- Claude-Modelle und Preise: [Anthropic Pricing](https://www.anthropic.com/pricing)
- Bedrock, Regionen pro Modell: [Regional availability by models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html), [Claude Sonnet 5.5 auf Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html)
- Payrexx und TWINT: [Gebühren](https://payrexx.com/en-ch/guides/zahlungsgebuehren-marge-handel), [TWINT in Payrexx Pay](https://docs.payrexx.com/merchant/bezahldienste/payrexx-pay/zahlungsmittel/twint)
