# Bewerbungsbegleiter

*Das Repo heisst weiter `bewerbungsassistent`.*

Werkzeuge und Claude-Skills für den ganzen Bewerbungsablauf: passende Stellen finden, Lebenslauf und Anschreiben pro Stelle zuschneiden, vor dem Absenden prüfen und den Versand vorbereiten. Ausgelegt auf den Schweizer Stellenmarkt (job-room.ch, jobs.ch, LinkedIn).

## Wozu: weniger, dafür passende Bewerbungen

Die App ist eine Erleichterung, keine Bewerbungsmaschine. Sie nimmt Routinearbeit ab, damit mehr Zeit für das bleibt, was eine gute Bewerbung ausmacht: die richtige Stelle wählen, sich mit der Firma befassen, das Anschreiben darauf anpassen und zeigen, was man mitbringt. Sie arbeitet nach diesen Grundsätzen:

- **Passung vor Menge.** Die Suche filtert nach einem persönlichen Suchprofil (Richtung, Region, Pensum, Ausschlüsse) und gleicht gegen bisherige Bewerbungen ab. So landen nur Stellen auf der Liste, die wirklich passen, und keine Firma bekommt dieselbe Bewerbung zweimal.
- **Zugeschnitten auf die Stelle.** Jede Anforderung des Inserats wird geprüft: abgedeckt, fehlt oder überdehnt. Der Lebenslauf zeigt die Erfahrung, die für diese Stelle zählt, das Anschreiben bezieht sich auf genau diese Firma und bleibt bei einer Seite.
- **Im eigenen Stil.** Das Anschreiben folgt dem Tonfall der Person, abgeleitet aus ihren bisherigen Anschreiben, und bleibt dabei professionell und passend zu Branche und Firma.
- **Eigenes Design.** Inhalt und Gestaltung sind getrennt. Wer will, gestaltet Lebenslauf und Anschreiben mit einem eigenen Template (Farben, Schriften, Aufbau; [Anleitung](lebenslauf/README.md#eigenes-theme)). So sehen die Unterlagen nicht aus wie die von allen anderen.
- **Die Person entscheidet und schickt selbst.** Die App macht Vorschläge und Entwürfe. Freigabe und Versand liegen immer bei der Person; nichts wird automatisch verschickt.
- **Nachvollziehbar.** Jede versendete Fassung wird mit Datum festgehalten. Vor einem Gespräch ist sofort klar, welche Unterlagen die Firma bekommen hat, und Rückfragen lassen sich zuverlässig beantworten.
- **Daten bleiben bei der Person.** Lebenslauf, Foto und Bewerbungsstände liegen lokal im eigenen Datenordner, nicht in diesem Repo und nicht auf einem fremden Server.

**Für Bewerbende** heisst das: weniger Zeit für die Suche nach passenden Stellen, für Formatierung und Verwaltung, mehr für die Auswahl und die Vorbereitung aufs Gespräch. Dazu Unterlagen in einem eigenen Design und ein sauberer Nachweis der Arbeitsbemühungen für den Job-Room.

**Für Arbeitgeber** heisst das: Ausschreibungen werden von passenden Bewerbenden auch dann gefunden, wenn sie weit hinten in den Suchergebnissen stehen. Die App prüft jede gefundene Ausschreibung auf Passung und wird dabei nicht müde. Er ist auf gezielte Auswahl statt Streuung ausgelegt. Die Unterlagen beziehen sich auf die ausgeschriebene Stelle, auf die Anforderungen des Inserats und auf die Firma, und sie sind übersichtlich gestaltet.

**Loslegen:** Die [Anleitung zur Installation](docs/installation.md) führt mit Bildern durch App, Einrichtung und Erweiterung.

## So sieht es aus

Alle Bilder zeigen frei erfundene Beispieldaten.

**Übersicht der Bewerbungen:** Was als Nächstes ansteht, dazu Stand, Passung (Note 1–6) und nächster Schritt jeder Stelle auf einen Blick. Von hier aus bewerben Sie sich über die Formulare der Firmen und tragen abgeschickte Bewerbungen im Job-Room ein; speichern und abschicken tun immer Sie.

![Übersicht mit „Das steht an“: der nächste Schritt als Karte, daneben, was auch noch offen ist, darunter die Liste der Bewerbungen, auf die die Person wartet, mit Stand, Note und nächstem Schritt; Knöpfe für Gemerkt, Beworben, Abgeschlossen und Alle](docs/bilder/uebersicht.jpg)

**Stellensuche:** Die Browser-Erweiterung sucht auf job-room, jobs.ch, jobscout24 und ictjobs nach dem Suchprofil, bei einem Suchprofil für Lehrstellen auf LENA und yousty, wahlweise nach Lehrstellen, Schnupperlehren oder beidem. Neue Stellen landen hier, nicht direkt im Register. Die KI bewertet die Passung in Paketen von zehn, nach der Suche von selbst (höchstens 30 pro Suche, abschaltbar) oder auf Knopfdruck. Bei Lehrstellen zählt der eigene Beruf mit Sternen zuerst. Dieselbe Stelle von einem zweiten Portal ist angehängt (+1), und bei einer Firma mit laufender Bewerbung steht ein Hinweis. Inserate von anderen Seiten, etwa LinkedIn, prüft oder speichert die Erweiterung auf Klick.

![Seite Stellen suchen: links die Liste der Treffer mit Note, Firma, dem Wert bei kununu, Ort, Pensum und Portal, rechts die Einschätzung der KI zum gewählten Treffer mit den Knöpfen Übernehmen, Verwerfen und Neu bewerten](docs/bilder/treffer.jpg)

**Eine Bewerbung in sechs Schritten:** Von der Stelle bis zum Festhalten sehen Sie, wo die Bewerbung steht und was als Nächstes kommt. Ein Anschreiben der KI geht erst weiter, wenn Sie es gelesen und freigegeben haben.

![Seite einer Bewerbung mit den sechs Schritten, der Karte „Nächster Schritt“ und den Angaben zur Stelle](docs/bilder/bewerbung.jpg)

**Unterlagen und Prüfung:** Lebenslauf und Anschreiben pro Stelle als PDF. Die automatische Prüfung findet hier, dass im Anschreiben noch die Firma einer anderen Bewerbung steht.

![Abschnitt Unterlagen prüfen: die Befunde der Prüfung, darunter Lebenslauf und Anschreiben als PDF und die Wahl der Beilagen](docs/bilder/pruefung.jpg)

**Entwürfe und Versionen:** Jedes Speichern legt einen Entwurf mit Datum an, geordnet nach Lebenslauf, Anschreiben je Bewerbung, Stil und Bausteinen und Suchprofil; ältere Fassungen sind aufklappbar. Was versendet wurde, bleibt erhalten und lässt sich nicht mehr löschen.

![Entwürfe nach Lebenslauf und Anschreiben gruppiert, je Dokument die neueste Fassung und die älteren aufklappbar](docs/bilder/entwuerfe.jpg)

**Fotoausschnitt (freiwillig):** Ausschnitt per Maus oder Tastatur einstellen, mit Vorschau in Druckgrösse.

![Editor für den runden Fotoausschnitt mit Reglern für Zoom und Ausschnitt, darunter Ihre Fotos mit dem aktiven Foto und einem zweiten mit den Knöpfen Verwenden und Löschen](docs/bilder/foto.jpg)

**Meine Angaben:** eine Seite in der App, die Schritt für Schritt alles abfragt, was die App braucht, und direkt in den Datenordner speichert. Bestehende Unterlagen lädt man gleich am Anfang hoch: „Aus Unterlagen vorbefüllen“ füllt das Formular aus PDF, Word und Text vor. Der Text geht ohne Name, Adresse und Kontaktangaben an die KI, und jeder Vorschlag bleibt markiert, bis er geprüft ist.

## Module

| Ordner | Inhalt |
|---|---|
| [`lebenslauf/`](lebenslauf/README.md) | Lebenslauf und Anschreiben als PDF aus YAML und Typst-Themes, Zuschnitt pro Stelle über Tags, mehrsprachige Inhalte |
| [`bewerbungen/`](bewerbungen/README.md) | Lokale Oberfläche: Bewerbungsregister, Unterlagen erstellen und prüfen, KI-Unterstützung mit Pseudonymisierung, Versand erfassen, Entwürfe und Versionen, Job-Room-Angaben, Fotoausschnitt |
| [`skills/einstieg/`](skills/einstieg/SKILL.md) | Claude-Skill: Einstieg aus bestehenden Unterlagen (Lebenslauf, Zeugnisse, Zertifikate, frühere Anschreiben) und per Interview – Lebenslauf, Suchprofil, Stilprofil mit eigenen Formulierungen und Bausteine, auch für die Lehrstellensuche |
| [`skills/jobsuche/`](skills/jobsuche/SKILL.md) | Claude-Skill: Stellensuche auf job-room.ch, jobs.ch, LinkedIn und Karriereseiten, Eintrag ins Register, optional Jobliste in Google Sheets |
| [`skills/bewerbung/`](skills/bewerbung/SKILL.md) | Claude-Skill: von der Stelle zur fertigen Bewerbung – Variante wählen, Anschreiben im eigenen Stil, Prüfung, Versand |
| [`desktop/`](desktop/README.md) | Lokale App für Windows, macOS und Linux: Installer bzw. AppImage, Start per Doppelklick, Einladungslink, signierte Updates vom eigenen Server |
| [`erweiterung/`](erweiterung/README.md) | Browser-Erweiterung für Chrome und Edge: aus dem [Chrome Web Store](https://chromewebstore.google.com/detail/bewerbungsbegleiter/nopiegcdnjpkekgfakgglegkeifpmopo) bzw. dem [Edge-Store](https://microsoftedge.microsoft.com/addons/detail/mcbcijjbklfeffbollnemgkgnabnmfmp), sonst von Hand geladen; Stellensuche auf job-room, jobs.ch, jobscout24 und ictjobs, Lehrstellensuche auf LENA und yousty nach dem Suchprofil, im Browser der Person; Treffer gehen an die App |
| [`vermittlung/`](vermittlung/README.md) | KI-Vermittlung für den Pilot: Zugang pro Person per Einladung, Budgets, Kosten ohne Inhalte; Container hinter HTTPS |
| [`onboarding/`](onboarding/README.md) | Formular für die Grundlagen (Stellen- und Lehrstellensuche): Quellen der Seite „Meine Angaben“ und Import in den Datenordner |
| [`vorlagen/`](vorlagen/) | Vorlagen für die persönlichen Dateien (Suchprofil, Stilprofil, Bausteine fürs Anschreiben) |

## Eigene Daten

Dieses Repo enthält nur Code, Themes, Skills und erfundene Beispieldaten. Persönliche Daten – Stammdaten des Lebenslaufs, Foto, Suchprofil, Zuschnitte pro Stelle, erzeugte PDFs – liegen in einem separaten privaten Ordner oder Repo daneben und werden per Pfad übergeben:

```
dev/
  bewerbungsassistent/          ← dieses Repo
  bewerbungsassistent-daten/    ← privat: cv.yaml, foto.jpg, suchprofil.md, jobs/, bewerbungen.yaml, …
```

## Schnellstart

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cd lebenslauf
python build.py data/beispiel.yaml -o build/beispiel.pdf
```

Eigene Fassung:

```bash
python build.py ../../bewerbungsassistent-daten/cv.yaml \
  --job ../../bewerbungsassistent-daten/jobs/ki.yaml \
  --build-dir ../../bewerbungsassistent-daten/.build \
  -o ../../bewerbungsassistent-daten/out/ki.pdf
```

Lokale Oberfläche:

```bash
cd bewerbungen
python app.py ../../bewerbungsassistent-daten
```

## Skills einrichten

`skills/einstieg/`, `skills/jobsuche/` und `skills/bewerbung/` in Claude Code nach `~/.claude/skills/` kopieren oder verlinken; in claude.ai als Skill hochladen. Die persönlichen Dateien im privaten Datenordner (`cv.yaml`, `suchprofil.md`, `anschreiben/stil.md`, `anschreiben/bausteine.md`) erarbeitet der Skill `einstieg` aus bestehenden Unterlagen und im Interview oder die Person selbst mit der Einstiegsvorlage (`onboarding/`); alternativ die Vorlagen aus `vorlagen/` kopieren und ausfüllen. Der Skill braucht Claude in Chrome (Suche im eingeloggten Browser-Tab) und nur für eine optionale Jobliste in Google Sheets den Google-Sheets-Connector.

## Lizenz

Erstellt von Andreas Schmidt.

[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0). Ohne Gewährleistung und ohne Haftung (Abschnitte 15 und 16 der Lizenz). Nutzen und weiterentwickeln darf den Bewerbungsbegleiter jede und jeder, auch kommerziell; wer ihn weitergibt oder eine geänderte Fassung über das Netz als Dienst anbietet (Abschnitt 13), muss den Quellcode offen halten und den Vermerk in [`docs/NOTICE`](docs/NOTICE) mit der Nennung des Urhebers erhalten (Abschnitt 7 b).

Schriften unter `lebenslauf/fonts/`: SIL Open Font License (siehe dort).
