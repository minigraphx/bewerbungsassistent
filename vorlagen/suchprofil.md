# Suchprofil – Vorlage

Kopie in den privaten Datenordner legen (`suchprofil.md`) und ausfüllen. Der Skill `jobsuche` liest diese Datei vor jeder Suche. Alle Werte hier sind Beispiele.

## Person
- Name: Erika Beispiel
- Sprache der Antworten: Deutsch

## Kontext
- Jobliste (optional): Google Sheet "Jobliste Bewerbungen", ID `<sheet-id>`, Tab `Stellen`. Mit dieser Zeile ist die Liste aktiviert: Jeder Eintrag kommt ins Register und in die Liste. Quelle ist immer das Register. Ohne diese Zeile gibt es nur das Register; anlegen lässt sich die Liste jederzeit auf Wunsch.
- Weitere Kontextdateien: `notizen/bewerbungen.md`

## Portale und Rhythmus
Der regelmässige Lauf (geplante Aufgabe) sucht standardmässig **wöchentlich** am hier gewählten Tag.

Wochentag: Montag

Zeitfenster: Die App nimmt Inserate der letzten 21 Tage, erlaubt sind 1 bis 60 Tage. Nach einem erfolgreichen Lauf sucht sie pro Portal nur die Tage seit diesem Lauf.
- Zeitfenster: 21 Tage

Pro Portal festlegen:
`automatisch` (unbeaufsichtigter Lauf), `mit Nutzer` (nur gemeinsam in einer Sitzung, z.B. wegen Login oder
Nutzungsbedingungen; der Lauf erinnert nur daran) oder `aus`.

| Portal | Modus |
|---|---|
| job-room | automatisch |
| jobs.ch | automatisch |
| jobscout24 | automatisch |
| ictjobs | automatisch |
| LinkedIn | mit Nutzer |
| Karriereseiten | automatisch |

## Suchrichtungen
1. Software-Entwicklung, Web und Daten (Priorität 1)
2. Interne Schulung und E-Learning mit IT-Bezug (Priorität 2, auch mit Lücken aufnehmen, Notiz-Präfix "Bildung IT:")
   - Nur mit IT-Bezug im Titel oder Volltext: Informatik, ICT, Software, digitale Kompetenzen
   - Ausschluss: Bildung ohne IT-Bezug, Recruiting

## Region
- Kantone (job-room): BE, SO
- Orte (jobs.ch, LinkedIn): Bern, Solothurn
- PLZ (jobscout24): 3000, 4500
- Regionen (ictjobs): grossraum-bern, solothurn
- Pendelgrenze: ausserhalb davon (z.B. Zürich, Basel, Genf) nur mit Remote
- Remote: ja

jobscout24 sucht um jede PLZ 20 km im Umkreis, nahe PLZ finden darum oft dieselben Stellen. Eine Zeile wie `- Regionen (jobscout24): Region Bern (BE/FR/SO), Homeoffice / Remote` lässt jobscout24 stattdessen pro Begriff einmal in allen genannten Regionen suchen; die Namen schreibt man wie jobscout24 sie zeigt, die Kantone in Klammern dürfen fehlen. Solange eine Region gewählt ist, gilt die Zeile mit den PLZ nicht, bleibt aber stehen. jobs.ch sucht bei jedem Ort auch im ganzen Kanton; ein zweiter Ort im selben Kanton bringt darum kaum neue Stellen.

## Keywords
- Kernliste: Python, TypeScript, Softwareentwickler, Data Engineer, E-Learning, Kursleiter (nur mit Informatik, ICT)
- Nischen (ohne Ort suchen): EdTech, Remote Python

Ein breiter Begriff kann Pflichtwörter tragen: «Kursleiter (nur mit Informatik, ICT)» sucht auf den Portalen nur «Kursleiter», behält aber nur Stellen, deren Titel oder Inserat eines der Wörter nennt, verglichen wie beim Titelfilter. Eine Stelle, die auch ein anderer Begriff fand, bleibt immer. Die Wörter stehen mit Komma getrennt in der Klammer; bei einer Gruppe mit «/» gelten sie für jeden Begriff. Das geht auf jeder Zeile unter Keywords, nicht bei den nummerierten Suchrichtungen.

Ohne Angabe sucht die App jeden Begriff auf allen Portalen. Eine eigene Zeile wie `- Nur jobs.ch, job-room: Lernbegleiter, Kursleiter` beschränkt ihre Begriffe auf die genannten Portale, geschrieben wie in der Tabelle oben und mit Komma getrennt; es darf mehrere geben. Nennt eine Zeile ein Portal, das die App nicht kennt, sucht sie deren Begriffe überall. Die Nischen lassen sich nicht beschränken.

## Titelfilter
- Positiv: Python, Software, Entwickler/Developer/Engineer, Daten/Data, Web, Learning, Trainer
- Ausschluss: Praktikum, Lehrstelle, Werkstudent, PhD, Sales (ganzes Wort), Head of

Ein Begriff passt auch als Anfang oder Ende eines Worts: «Software» passt zu «Softwareentwickler», «Praktikum» zu «Sommerpraktikum». Mit «(ganzes Wort)» dahinter passt er nur als ganzes Wort, darum sortiert «Sales (ganzes Wort)» den «Salesforce-Entwickler» nicht aus. Bei einer Gruppe mit «/» gilt der Zusatz für jeden Begriff. Begriffe mit höchstens drei Buchstaben wie «KI» passen immer nur als ganzes Wort.

## Sprachen
- Deutsch (Muttersprache), Englisch (gut), Französisch (Grundkenntnisse)
- Französisch auf gutem Niveau als Muss → ausschliessen; "von Vorteil" → aufnehmen mit Hinweis

## Abschluss und Erfahrung
- Bachelor Informatik, zehn Jahre Praxis

## Stärken
- Python, TypeScript, Datenpipelines, technische Themen verständlich erklären

## Ausschlüsse
Die App prüft jedes Inserat vor der Bewertung mit festen Regeln: Sprachen und Abschluss gegen Lebenslauf und diese Datei, dazu die Technologien hier. Passt eines nicht, steht der Treffer mit Grund unten in der Liste.
- Technologien als Schwerpunkt: Java, .NET

## Typische Haken (offen benennen)
- Java- oder .NET-Schwerpunkt, Startdatum nach 1.3., Befristung

## Rahmen
- Frühester Start: 1.3.
- Pensum: 80–100%

## Zielfirmen mit Karriereseite
- Beispiel AG: Liste unter `https://jobs.example.ch/`, Links `a[href*="stellen"]`, Ort nach "Standort", Anforderungen ab "Dein Profil". Nur Bern oder Remote.

## Vermittler
Bei Inseraten von Vermittlern vergleicht die App Titel und Pensum mit den offenen Bewerbungen und zeigt einen Hinweis, wenn es dieselbe Stelle sein könnte. Die bekannten Vermittler kennt sie schon; weitere hier ergänzen.
- Weitere Vermittler: Beispiel Personal AG

## Hinweise zu bestimmten Firmen
- Keine
