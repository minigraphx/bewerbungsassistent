# Konzept: Bewerbungsassistent als Onlinedienst (MIN-305)

Entwurf vom 26.10.2026 für den Meilenstein „Onlineservice für nicht versierte Nutzer (später)“. Ziel ist eine Entscheidungsgrundlage, keine Umsetzung.

## Zielgruppe und Nutzen

Stellensuchende ohne technische Kenntnisse: kein Python, kein Git, keine Kommandozeile. Sie erhalten dieselben Funktionen wie die lokale Oberfläche – Bewerbungen verwalten, Lebenslauf und Anschreiben im eigenen Stil, Prüfung, Versand festhalten, Angaben für den Job-Room – im Browser, ohne Installation. Die lokale Variante bleibt bestehen und ist für technisch Versierte die datensparsamste Wahl.

## Umfang (Vorschlag für eine erste Fassung)

| Enthalten | Später | Nicht vorgesehen |
|---|---|---|
| Lebenslauf aus Formular, Themes, Fotoausschnitt | Mehrsprachige Inhalte im Formular | Automatischer Versand ohne Freigabe |
| Anschreiben aus Bausteinen und Stilprofil (LLM) | Stellensuche auf Portalen (siehe unten) | Bewerbungen im Namen der Person auf Portalen |
| Register, Status, Job-Room-Angaben | Erinnerungen (Fristen, Nachfassen) per E-Mail | Weitergabe von Daten an Arbeitgeber oder Vermittler |
| Entwürfe und Versionen, Export aller Daten | Teamfunktionen (Coach sieht Bewerbungen) | |

Die Stellensuche läuft heute über einen Claude-Skill im eingeloggten Browser der Person. Online ginge nur die Suche über öffentliche Schnittstellen (z.B. jobs.ch) ohne Login; LinkedIn und Job-Room bleiben bei der Person.

## Architektur

- **Gleicher Kern:** Die Module `lebenslauf` und `bewerbungen` trennen schon heute Logik und Speicherung. Für den Dienst bekommen Register, Varianten, Entwürfe und Versionen eine Server-Umsetzung derselben Schnittstellen (wie `versionen.Versionierung`): Datenbank (z.B. PostgreSQL) statt YAML, Objektspeicher statt `.entwuerfe/` und `versendet/`.
- **Rendern:** Typst läuft serverseitig in einer Warteschlange mit Zeitlimit; Schriften liegen im Container. Eine Vorschau braucht heute 35–60 ms, ein Lebenslauf rund 300 ms – für einen kleinen Dienst ohne eigene Rechenknoten machbar.
- **LLM:** Anschreiben und inhaltliche Prüfung über die Claude API, mit Belegpflicht wie im Skill `bewerbung`. Personendaten gehen nur so weit an den Anbieter, wie für den Entwurf nötig; Vertrag zur Auftragsverarbeitung nötig.
- **Oberfläche:** Die bestehenden Seiten (statisches HTML, Vanilla-JS, CSP ohne Inline-Skripte) lassen sich übernehmen; dazu kommen Anmeldung und Formulare für Inhalte statt Text-Editor.

## Datenschutz und Recht

- **Besonders schützenswert:** Foto, Geburtsdatum, Adresse, Bewerbungsstände, Absagen, Arbeitslosigkeit (Job-Room). Massgeblich: revidiertes DSG der Schweiz; bei Nutzern in der EU zusätzlich die DSGVO.
- **Hosting** in der Schweiz oder EU; Verschlüsselung in der Übertragung und im Speicher, Schlüssel getrennt verwaltet.
- **Datenminimierung:** keine Analyse- oder Werbe-Tracker; Protokolle ohne Inhalte; Löschfristen für inaktive Konten (z.B. 12 Monate nach letzter Anmeldung, mit Vorwarnung).
- **Rechte der Nutzer:** Export aller Daten (YAML und PDFs, gleiches Format wie lokal) und vollständiges Löschen auf Knopfdruck.
- **Rechtstexte:** Datenschutzerklärung, Nutzungsbedingungen mit Haftungsbegrenzung (die GPL des Codes deckt den Betrieb eines Dienstes nicht ab), Verträge zur Auftragsverarbeitung mit Hosting- und LLM-Anbieter.
- **Lizenz:** Der Code ist GPL-3.0. Ein Dienst darf ihn nutzen; Änderungen müssen bei Weitergabe offengelegt werden. Soll auch der Betrieb als Dienst zur Offenlegung verpflichten, wäre ein Wechsel auf AGPL-3.0 zu prüfen.

## Sicherheit

Die lokale Oberfläche ist durch „nur 127.0.0.1“, ein Token pro Start und die Host-Prüfung geschützt. Online braucht es stattdessen:

- Anmeldung (E-Mail mit Einmal-Link oder Passkeys), Sitzungen mit sicheren Cookies, CSRF-Schutz.
- Strikte Trennung der Daten pro Konto (Mandantenfähigkeit) auf jeder Abfrage, mit Tests.
- Begrenzung von Anfragen und Uploads; Fotos serverseitig neu kodieren und Metadaten (GPS, Kamera) entfernen, wie heute lokal.
- Die bestehende CSP und das Einsetzen von Inhalten nur als Text beibehalten.
- Regelmässige Abhängigkeits- und Sicherheitsprüfungen in der CI.

## Betrieb und Kosten (grobe Schätzung, zu prüfen)

- Ein kleiner Server oder Container-Dienst in der Schweiz, Datenbank, Objektspeicher, Backup.
- LLM-Kosten pro Anschreiben im Rappen- bis tiefen Frankenbereich je nach Modell und Länge.
- Geschäftsmodell offen: kostenlos mit Kontingent, Spende, kleines Abo oder Angebot über Bildungs- und Arbeitsintegrationsstellen.

## Barrierefreiheit und Sprache

Einfache Sprache, klare Schritte (Stelle → Unterlagen → Prüfung → Versand), Tastaturbedienung und Kontraste nach WCAG 2.1 AA, Deutsch zuerst, Französisch und Englisch später.

## Voraussetzungen und nächste Schritte

1. Lokal stabil: Editor mit Formularen (MIN-302), Versionierung im Alltag erprobt (MIN-303).
2. Entscheidung, ob und für wen der Dienst angeboten wird (Zielgruppe, Träger, Finanzierung).
3. Rechtliche Abklärung (Datenschutz, Haftung, Lizenz).
4. Prototyp mit wenigen Testpersonen, lokal betrieben, bevor echte Daten online gehen.
