# Konzept: Bewerbungsassistent als Onlinedienst (MIN-305)

Stand 2.11.2026; ersetzt den Entwurf vom 26.10.2026. Das Konzept ist eine Entscheidungsgrundlage für den Meilenstein „Onlineservice für nicht versierte Nutzer“. Umgesetzt wird erst nach Freigabe.

## Entscheide

| Frage | Entscheid (2.11.2026) |
|---|---|
| Zielgruppe | Zuerst ein **Pilot mit 5–10 Personen aus dem Bekanntenkreis**, betrieben vom Projektinhaber. Nach dem Pilot wird über einen öffentlichen Dienst entschieden. |
| KI | Der **Dienst ruft die Claude API** mit eigenem Schlüssel auf und trägt die Kosten. Die Nutzer brauchen kein eigenes Claude-Abo. |
| Finanzierung | **Kleines Abo** ab dem öffentlichen Dienst. Der Pilot ist gratis und dient dazu, die Kosten pro Person zu messen. |

Die lokale Variante bleibt bestehen. Sie ist für technisch Versierte die datensparsamste Wahl.

## Zielgruppe und Nutzen

Die Zielgruppe sind Stellensuchende ohne technische Kenntnisse: kein Python, kein Git, keine Kommandozeile. Sie arbeiten im Browser nach demselben Ablauf wie lokal: Stelle → Unterlagen → Prüfung → Versand. Die KI-Schritte laufen im Dienst, nicht in Claude Code.

Der Nutzen für sie: Pro Stelle entstehen ein passender Lebenslauf und ein Anschreiben im eigenen Stil, in dem jede Aussage belegt ist. Dazu kommen eine Übersicht über alle Bewerbungen und die fertigen Angaben für den Job-Room.

## Phasen

1. **Pilot** (etwa 3 Monate, gratis, auf Einladung). Er soll zwei Fragen klären: Kommen nicht versierte Personen damit zurecht? Und was kostet eine aktive Person pro Monat?
2. **Öffentlicher Dienst mit Abo.** Er kommt nur, wenn der Pilot die Erfolgskriterien erfüllt.

Erfolgskriterien des Pilots:

- Mindestens 5 Personen schicken je mindestens 3 Bewerbungen ab, die mit dem Dienst erstellt wurden.
- Eine Bewerbung dauert von der Stelle bis zu den fertigen PDFs unter 30 Minuten.
- Die KI-Kosten liegen unter CHF 10 pro aktive Person und Monat (gemessen, nicht geschätzt).
- Kein Datenschutzvorfall, und keine Person sieht Daten einer anderen.
- Die Rückmeldungen zeigen, welche Schritte ohne Hilfe nicht klappen.

## Umfang im Pilot

| Enthalten | Nicht im Pilot |
|---|---|
| Konto auf Einladung, Anmeldung mit Passkey oder E-Mail-Link | Stellensuche auf Portalen (läuft weiter über den Skill `jobsuche` im eigenen Browser) |
| **Einstieg:** bisherigen Lebenslauf (PDF oder Text) und 2–3 frühere Anschreiben hochladen. Die KI erstellt daraus Lebenslauf, Stilprofil und Bausteine, die Person bestätigt jede Angabe. | Versand durch den Dienst (die Person schickt selbst ab) |
| Lebenslauf, Themes, Foto (Metadaten werden entfernt) | Erinnerungen per E-Mail |
| Stelle erfassen: Inseratstext einfügen. Die KI bewertet die Passung (Note 1–6) mit Begründung. | Coaches und Teams |
| Lebenslauf-Variante vorschlagen (regelbasiert wie heute) | Französisch, Englisch |
| Anschreiben-Entwurf im eigenen Stil (KI) mit Überarbeitung | |
| Formale Prüfung (wie heute) und inhaltliche Prüfung (KI) | |
| Register, Versand festhalten, Job-Room-Angaben zum Kopieren | |
| Entwürfe und Versionen, Export aller Daten, Löschen des Kontos | |

Der Einstieg ist die grösste Hürde für nicht versierte Personen. Lokal entstehen Lebenslauf, Stilprofil und Bausteine heute in einer Claude-Sitzung, online braucht es dafür einen geführten Ablauf.

## KI-Funktionen und Kosten

### Annahmen

- Der Kontext eines Anschreibens umfasst Stilprofil, Bausteine, Lebenslauf und Inserat. Gemessen an echten Daten sind das rund 20'000 Zeichen oder etwa 7'000 Tokens. Mit Anweisungen sind es etwa **10'000 Tokens Eingabe**.
- Die Ausgabe eines Anschreibens samt Denken umfasst **5'000–10'000 Tokens**.
- Preise der Claude API (Stand Oktober 2026, pro Million Tokens):

| Modell | Eingabe | Ausgabe |
|---|---|---|
| Claude Opus 5.5 | USD 4 | USD 20 |
| Claude Sonnet 5.5 | USD 2 | USD 10 |
| Claude Haiku 5.5 | USD 0.10 | USD 0.50 |

  Auf Amazon Bedrock gelten eigene Preise (siehe Datenstandort).
- Die Beträge sind in USD gerechnet. Für eine Grobschätzung entsprechen sie in etwa Franken.

### Kosten pro Aufruf (Schätzung)

| Funktion | Modell (Vorschlag) | Tokens Eingabe / Ausgabe | Kosten pro Aufruf |
|---|---|---|---|
| Stelle bewerten (Passung 1–6) | Haiku 5.5 | 5'000 / 1'000 | ca. 0.1 Rappen |
| Anschreiben-Entwurf | Sonnet 5.5 | 10'000 / 8'000 | ca. 10 Rappen |
| Überarbeitung (je Runde) | Sonnet 5.5 | 12'000 / 6'000 | ca. 8 Rappen |
| Inhaltliche Prüfung | Sonnet 5.5 | 15'000 / 3'000 | ca. 6 Rappen |
| Einstieg: Stilprofil, Bausteine, Lebenslauf (einmalig) | Opus 5.5 | 30'000 / 15'000 | ca. 40 Rappen |

Daraus ergibt sich:

- **Eine Bewerbung** (Entwurf, 2 Überarbeitungen, Prüfung) kostet etwa **30–35 Rappen** mit Sonnet 5.5 und etwa das Doppelte mit Opus 5.5.
- **Eine aktive Person pro Monat** (15 Bewerbungen, 100 bewertete Stellen) kostet etwa **CHF 5–6** mit Sonnet 5.5 und **CHF 10–12** mit Opus 5.5.
- **Prompt-Caching** senkt den Eingabe-Anteil: Stilprofil, Bausteine und Lebenslauf bleiben pro Person gleich. Der grössere Teil der Kosten ist aber die Ausgabe.

Im Pilot werden die echten Werte pro Aufruf protokolliert, ohne Inhalte. Für das Anschreiben werden Sonnet 5.5 und Opus 5.5 an denselben Stellen verglichen. Die Wahl des Modells fällt nach Qualität und gemessenen Kosten.

### Datenstandort der KI

Für die KI-Aufrufe kommen drei Wege in Frage:

- **Claude API direkt:** Die Region lässt sich nur auf „global“ oder „us“ festlegen, eine Region in der EU oder der Schweiz gibt es nicht. Die Daten gehen damit ins Ausland, auch in die USA. Nach Art. 16 DSG ist das zulässig, wenn ein angemessener Schutz besteht. Zu prüfen ist, ob Anthropic unter dem Swiss-U.S. Data Privacy Framework zertifiziert ist; sonst braucht es Standardvertragsklauseln.
- **Amazon Bedrock:** Die aktuellen Claude-Modelle laufen in Zürich (eu-central-2) nicht direkt in der Region. Mit der Geo-Inferenz „EU“ bleibt die Verarbeitung aber in EU-Regionen und Zürich (unter anderem Frankfurt, Stockholm, Mailand). Die EU gilt nach DSG als angemessen. Die Preise weichen von der Claude API ab.
- **Google Vertex AI:** Hier gibt es eine Multi-Region „eu“ als Alternative.

**Vorschlag:** Für den Pilot Bedrock mit EU-Geo-Inferenz aus einem AWS-Konto in Zürich. Der Code nutzt das Anthropic SDK, ein Wechsel zur Claude API ist daher eine Konfiguration.

**Datenminimierung:**

- Name, Adresse, Geburtsdatum, Telefon und E-Mail werden vor dem Aufruf durch Platzhalter ersetzt und danach wieder eingesetzt.
- Das Foto geht nie an die KI.
- Inseratstexte bleiben Daten: Anweisungsartige Zeilen werden wie im Skill `bewerbung` erkannt und gemeldet.

## Architektur im Pilot: ein Datenordner pro Person

Der Grundsatz lautet: so viel vom heutigen Code wie möglich unverändert nutzen. Jede Person bekommt einen eigenen Datenordner wie lokal (YAML, Git, `versendet/`, `.entwuerfe/`) und einen eigenen Container mit der bestehenden Oberfläche. Die Trennung der Daten macht der Container, nicht neuer Mandanten-Code.

```
Browser ──HTTPS──▶ Reverse Proxy (Caddy) ──▶ Anmeldung (z.B. Authelia: Passkey, Einladung)
                         │
                         ├─▶ Container Person A: app.py + Typst ──▶ Volume A (Datenordner, verschlüsselt)
                         ├─▶ Container Person B: …
                         └─▶ KI-Aufrufe ──▶ Bedrock EU (Geo-Inferenz)
```

- **Server:** 1 virtueller Server in der Schweiz (z.B. Infomaniak Public Cloud oder Exoscale) mit Docker. 10 Personen brauchen je etwa 100–200 MB RAM; Typst rendert einen Lebenslauf in rund 300 ms.
- **Anmeldung:** über ein bewährtes Werkzeug vor dem Proxy (z.B. Authelia mit Passkeys), nicht selbst gebaut. Der Proxy leitet jede Anmeldung fest zum Container dieser Person.
- **Anpassungen an der Oberfläche:**
  - Die Host-Prüfung erlaubt den öffentlichen Namen.
  - Der Server vertraut der Anmeldung des Proxys nur im internen Netz.
  - Es gibt Grenzen für Uploads.
  - Ein Hochladen ersetzt das Bearbeiten im Text-Editor.
  - Token pro Start und CSP bleiben.
- **KI-Modul:** Ein neues Modul `bewerbungen/ki.py` erhält eine schmale Schnittstelle: `bewerte_stelle`, `entwirf_anschreiben`, `pruefe_inhalt`, `richte_ein`. Die Regeln aus den Skills (Belegpflicht, Stilprofil, Inserat ist Daten) werden zu Prompts. Das Modul läuft auch lokal mit eigenem API-Schlüssel. Damit hat auch die lokale Variante KI ohne Claude Code.
- **Versionen:** Git pro Datenordner, wie lokal (MIN-303, MIN-304).
- **Sicherung:** täglich, verschlüsselt, an einem zweiten Standort in der Schweiz; Wiederherstellung einmal im Pilot üben.

Für das Abo mit mehr als etwa 50 Personen reicht ein Container pro Person nicht mehr: Die Kosten und der Betrieb wachsen pro Person. Dann bekommen Register, Entwürfe und Versionen eine Server-Umsetzung derselben Schnittstellen: Datenbank statt YAML, Objektspeicher statt Ordner.

## Datenschutz und Recht

**Besonders schützenswerte Daten:**

- Lebensläufe enthalten Foto, Geburtsdatum, Adresse, Bewerbungsstände und Absagen.
- Job-Room-Angaben verraten die Arbeitslosigkeit. Sie können als Daten über Massnahmen der sozialen Hilfe besonders schützenswert sein (Art. 5 DSG).
- Massgeblich ist das DSG, bei Personen in der EU zusätzlich die DSGVO.

**Schon im Pilot nötig:**

- **Datenschutzerklärung und Einwilligung:** Sie sagen, wo die Daten liegen, was an die KI geht und wie lange die Daten gespeichert bleiben.
- **Auftragsverarbeitung:** Verträge mit dem Hosting-Anbieter und mit AWS bzw. Anthropic. Zu bestätigen ist, dass API-Daten nicht für das Training verwendet werden.
- **Löschung:** Nach dem Pilot werden die Daten exportiert und gelöscht, ausser die Person will weitermachen. Inaktive Konten werden 12 Monate nach der letzten Anmeldung gelöscht, mit Vorwarnung.
- **Datensparsamer Betrieb:** keine Tracker, Protokolle ohne Inhalte.

**Für das Abo zusätzlich:**

- Nutzungsbedingungen mit Haftungsbegrenzung: Die Person prüft und verantwortet ihre Unterlagen.
- Träger: Einzelfirma oder GmbH.
- Mehrwertsteuer erst ab CHF 100'000 Umsatz.

**Lizenz:** Der Code steht unter GPL-3.0. Soll auch der Betrieb als Dienst zur Offenlegung von Änderungen verpflichten, ist ein Wechsel auf AGPL-3.0 zu prüfen.

## Sicherheit

- Anmeldung mit Passkeys oder E-Mail-Link; Sitzungen mit sicheren Cookies; Schutz gegen CSRF.
- Die Daten jeder Person liegen in einem eigenen Container und Volume. Ein Test stellt sicher, dass kein Weg zu fremden Daten führt.
- Anfragen, Uploads und KI-Aufrufe sind pro Person begrenzt. Das schützt vor Missbrauch und vor Kosten.
- Fotos werden serverseitig neu kodiert und ihre Metadaten entfernt.
- Die bestehende CSP bleibt, Inhalte werden nur als Text eingesetzt.
- Abhängigkeiten und Container-Images werden in der CI geprüft.

## Abo (Phase 2, Vorschlag)

**Preis:** CHF 12–19 pro Monat, monatlich kündbar. Als Alternative ein „Paket Stellensuche“ über 3 Monate.

**KI-Kontingent im Preis:** zum Beispiel 30 Anschreiben pro Monat. Es deckelt die Kosten pro Person.

**Zahlung:** über Payrexx (Karte, TWINT), Tarif ab CHF 19 pro Monat, Gebühren rund 1.3 %.

- Ob TWINT für wiederkehrende Zahlungen geht, ist in der Dokumentation widersprüchlich und muss mit Payrexx geklärt werden.
- Alternative: Stripe.

**Grobe Rechnung, zu prüfen:**

- Die Fixkosten (Server, Sicherung, Domain, Zahlungsanbieter) liegen bei etwa CHF 100–150 pro Monat.
- Pro Person kommen KI-Kosten von CHF 5–6 dazu.
- Bei CHF 15 Abo bleiben etwa CHF 8 pro Person. Ab etwa 15–20 zahlenden Personen sind die Fixkosten gedeckt, ohne die eigene Arbeitszeit.

## Offene Entscheide

1. **KI-Anbieter:** Bedrock EU (Datenstandort) oder Claude API direkt (einfacher, Daten in den USA)?
2. **Modell für Anschreiben:** Sonnet 5.5 oder Opus 5.5? Entscheid nach dem Vergleich im Pilot.
3. **Hosting-Anbieter in der Schweiz:** Offerten für Server, Volumes und Sicherung einholen.
4. **Pseudonymisierung:** Ersetzen der Personendaten vor jedem KI-Aufruf, ja oder nein? Vorschlag: ja.
5. **Träger und Rechtsform** für das Abo. Erst nach dem Pilot zu entscheiden.

## Nächste Schritte

1. Dieses Konzept freigeben (MIN-305).
2. KI-Modul `ki.py`, lokal mit eigenem API-Schlüssel: Stelle bewerten, Anschreiben entwerfen, inhaltlich prüfen. Es nützt auch der lokalen Variante.
3. Geführter Einstieg: Lebenslauf und frühere Anschreiben hochladen; Lebenslauf, Stilprofil und Bausteine daraus erstellen und bestätigen lassen.
4. Betrieb hinter Proxy: Host-Prüfung, Anmeldung über den Proxy, Container pro Person, Sicherung.
5. Rechtstexte für den Pilot: Datenschutzerklärung, Einwilligung, Verträge zur Auftragsverarbeitung.
6. Pilot durchführen und nach 3 Monaten auswerten: Erfolgskriterien, gemessene Kosten, Entscheid über Phase 2.

## Quellen

- Claude-Modelle und Preise: [Anthropic Pricing](https://www.anthropic.com/pricing)
- Bedrock, Regionen pro Modell: [Regional availability by models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-region-compatibility.html), [Claude Sonnet 5.5 auf Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html)
- Payrexx und TWINT: [Gebühren](https://payrexx.com/en-ch/guides/zahlungsgebuehren-marge-handel), [TWINT in Payrexx Pay](https://docs.payrexx.com/merchant/bezahldienste/payrexx-pay/zahlungsmittel/twint)
