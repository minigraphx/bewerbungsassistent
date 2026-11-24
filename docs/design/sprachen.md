# Bewerbungsbegleiter auf Französisch und Englisch

Stand: 23.11.2026 · Board #95 (App in fr und en), Schritt 1: #414, Schritt 2: #415 · Spec G10

Die Oberfläche der App kommt auf Französisch und Englisch dazu. Deutsch bleibt die Quelle und ändert sich nicht. Dieses Dokument beschreibt, wie die Übersetzung funktioniert, wie ein späterer Schritt eine Seite übersetzt, welche Wörter in allen Sprachen gleich übersetzt werden und was Andy entschieden hat.

## Entscheide von Andy (23.11.2026)

1. **Der Schalter geht einmal am Ende an** (#434, letzter Schritt von #95). Bis dahin spricht die App immer Deutsch, auch wenn die Person Französisch oder Englisch gewählt hat. Halb übersetzte Seiten sieht niemand.
2. **Französisch duzt mit tu**, wo der deutsche Textsatz du verwendet (Stelle mit du, Lehrstelle). Die Sie-Form wird zu vous.
3. **`onboarding/dist/einstieg.html` bleibt deutsch.** Die eigenständige Einstiegsvorlage bekommt keine Übersetzung.
4. **Nach dem Einschalten verlangt das Gate fr und en für jeden neuen Text der Oberfläche.** Der letzte Schritt ersetzt dafür die Liste `FERTIG` durch alle Quellen.
5. Übersetzt wird von Agenten, ohne eigenes Lektorat. Sichtbarer Wortlaut läuft wie immer über die UI/UX-Prüfung.

## Wie es funktioniert

### Katalog

Die Übersetzungen liegen in `bewerbungen/sprachen/`, eine JSON-Datei pro Gruppe von Items (zum Beispiel `rahmen.json`, `heute.json`). Der Schlüssel ist der deutsche Text, genau wie er auf der Seite steht. Darum braucht Deutsch keinen Eintrag, und fehlt ein Eintrag, zeigt die Seite den deutschen Text.

```json
{
  "Gespeichert.": { "fr": "Enregistré.", "en": "Saved." },
  "Abgabe bis {datum}": { "fr": "À remettre d'ici le {datum}", "en": "Due by {datum}" },
  "texte:fragen.label": {
    "fr": { "sie": "Votre question", "du": "Ta question" },
    "en": { "sie": "Your question" }
  }
}
```

- Ein Eintrag aus `seiten/texte.js` heisst `"texte:<Schlüssel>"` und hat pro Sprache seine Formen: Französisch `sie` und `du`, Englisch nur `sie`, dazu `lehrstelle`, wenn der deutsche Eintrag eine hat. Englisch kennt kein du und fällt auf `sie` zurück; `lehrstelle` fällt auf `du` und dann auf `sie` zurück.
- Platzhalter wie `{datum}` stehen in jeder Sprache genau so wie im Deutschen.
- Der Lader (`bewerbungen/translation_catalog.py`) legt alle Dateien zusammen. Derselbe Schlüssel in zwei Dateien ist erlaubt, aber nur mit derselben Übersetzung; sonst bricht er mit beiden Dateinamen ab.

### Woher die Sprache kommt

`bewerbungen/ui_texts.py` gibt mit `sprache(k)` die Sprache der App für den Datenordner. Seiten, Skripte und die Meldungen des Servers (#415) lesen sie nur dort.

- Solange der Schalter aus ist (`SWITCH_ON = False`), gibt `sprache(k)` immer `de`.
- Für die Entwicklung und für die Prüfung eines Items schaltet die Umgebungsvariable `BEWERBUNGSBEGLEITER_SPRACHE_VORSCHAU=1` die Vorschau ein: Dann gilt die gespeicherte Sprache der App aus `sprachen.yaml` (Einstellungen, Karte „Sprache“).

```
BEWERBUNGSBEGLEITER_SPRACHE_VORSCHAU=1 PYTHONPATH=bewerbungen:lebenslauf:onboarding python desktop/start.py
```

### Seiten

`Server._seite` gibt jede Seite durch `page_translation.translate`:

- Auf Deutsch bleibt die Seite Byte für Byte, wie sie ist.
- Auf Französisch oder Englisch setzt sie `<html lang="fr">` bzw. `"en"`, übersetzt Textknoten ausserhalb von `script` und `style` und die Attribute `aria-label`, `placeholder`, `title` und `alt`, in doppelten wie in einfachen Anführungszeichen. Ein Element mit `data-text` bekommt die Sie-Form seines Textsatzes; `Texte.anwenden` setzt danach die passende Form.
- Der Inhalt eines `<textarea>` ist Text der Person und bleibt, wie er ist; nur die Attribute des Felds werden übersetzt.
- Vor das erste `<script>` kommt `<script src="/uebersetzung.js?sprache=fr">`. Es setzt `Uebersetzung` mit den Texten dieser Sprache. Das Skript kommt von der App selbst (`script-src 'self'`); Skripte und Stile der Seite bleiben unberührt, darum gelten auch die Hashes von „Meine Angaben“ weiter.
- Ist der Katalog kaputt, bleibt die Seite deutsch, und die Konsole nennt die Datei.

Gesucht wird der Text, wie er nach dem Entschlüsseln der HTML-Zeichen (`&amp;` → `&`) mit zusammengezogenen Leerzeichen und Zeilenumbrüchen dasteht. Ein Satz, den Markup trennt („Mit <a>…</a> geht es weiter“), besteht aus mehreren Textknoten; den schreibt der Schritt der Seite so um, dass jeder Teil für sich übersetzbar ist, oder setzt ihn per Skript mit `Texte.t`.

### Skripte

In `seiten/texte.js`:

- `Texte.t("Abgabe bis {datum}", { datum })` gibt den Text in der Sprache der Seite (`document.documentElement.lang`), sonst Deutsch, und füllt die Platzhalter.
- `Texte.text(schlüssel, satz)` gibt die Form des Textsatzes in der Sprache der Seite; fehlt der Eintrag, die deutsche Form wie bisher.
- `Texte.setzeSprache(sprache, katalog)` ist nur für Tests; ohne Argumente entscheidet wieder die Seite.

Einen Text, der aus Teilen zusammengesetzt wird, schreibt man als eine Vorlage mit Platzhaltern, nie als Verkettung.

### Meldungen des Servers

Eine Meldung für die Person schreibt eine Route als `T("Abgabe bis {datum}", datum=datum)` aus `ui_texts`:

- `T` ist eine Unterklasse von `str` und ist der deutsche Text mit eingesetzten Werten. Code und Tests, die die Meldung lesen (`str(fehler) == "Abgabe bis 20.11.2026"`), merken nichts. Dazu behält `T` die Vorlage (`template`) und die Werte (`values`), denn der Schlüssel im Katalog ist die Vorlage.
- **Fehler:** `_run_route` gibt die Meldung eines `ValueError`, `KeyError` (auch `NichtGefunden`) oder `StatusError` als `fehler.args[0]` an `_fehler`, ein `T` also als `T`. `_fehler` sagt sie in der Sprache der App: ein `T` über seine Vorlage, ein schlichter deutscher Text nur, wenn er genau so im Katalog steht (feste Meldungen wie „Nicht gefunden“).
- **Antworten:** `json_antwort` behält den Wert der Antwort; vor dem Senden ersetzt der Server darin nur die `T`, etwa in `hinweis` oder in Befunden. Alles andere sind Daten und bleibt deutsch, auch ein Text, der zufällig ein Schlüssel im Katalog ist (ein Stand, ein Titel). Auf Deutsch geht die Antwort Byte für Byte so hinaus, wie die Route sie gebaut hat.
- Ein Wert, der selbst ein `T` ist, kommt in derselben Sprache in die Vorlage.
- Die Sprache kommt aus dem Datenordner des Servers, darum folgen auch die Antworten an die Erweiterung und an Claude über die App.
- Wer eine Meldung ausserhalb einer Route zeigt (etwa `desktop/dialogs.py`), holt sie mit `ui_texts.uebersetze(text, sprache)`.
- `lebenslauf/` importiert nichts aus der App und bleibt auf der Befehlszeile deutsch. Was die App von dort zeigt, trägt seine Teile als Daten: die Kürzungen in `cuts.py` (#428), die Ablehnungen als `refusal.Refusal` mit Vorlage und Werten: die des Anschreibens (`anschreiben.LetterError`, #453), des Fotoausschnitts und der Überschriften (`fotoausschnitt.py`, `build.py`, #455). `bewerbungen/refusal_messages.in_app_language()` macht daraus um jeden Bau von Lebenslauf, Anschreiben und Dossier ein `T`, ebenso um jeden Aufruf von `fotoausschnitt` auf der Seite „Foto“.
- Ein Git-Fehler von `versionen.py` ist ein `RuntimeError` mit einem `T`; der Versand gibt dieses `T` in den Hinweis „Versand erfasst, aber nicht in Git eingefroren“, damit auch sein Rahmen der Sprache folgt (#455). Was Git schreibt, bleibt, wie es ist.
- Ist der Katalog kaputt, bleibt die Meldung deutsch, und die Konsole nennt die Datei.

Eine Meldung mit Werten braucht `T`: Ein f-String ergibt einen Text, der nie im Katalog steht.

### Prüfung auf fehlende Texte

```
cd bewerbungen
python -m sprachen_pruefen              # die Dateien in FERTIG
python -m sprachen_pruefen --alle       # jede Quelle der App
python -m sprachen_pruefen seiten/heute.html seiten/heute.js
```

Jede Zeile nennt `datei:zeile: text [fr,en]` mit den fehlenden Sprachen; `[Texte.t]` heisst, ein Skript zeigt einen deutschen Text, ohne ihn über `Texte.t` zu holen, `[T]`, eine Meldung in Python ist ein f-String statt eines `T`. Mit einer Lücke endet der Befehl mit 1.

Gelesen wird:

- **HTML:** was die Seite übersetzt (Textknoten, die vier Attribute, Textsätze über `data-text`).
- **JavaScript:** der Text in jedem `Texte.t(…)`, der Schlüssel in jedem `Texte.text(…)` und deutsch aussehende Texte ausserhalb davon (ein Satz mit Leerzeichen oder ein grossgeschriebenes Wort).
- **Python:** die Vorlage in jedem `T(…)`, auch `ui_texts.T(…)`, und die Meldung eines `raise`, auch über eine Konstante des Moduls; eine Meldung als f-String gilt als Lücke `[T]`.

Nicht als Text zählen:

- Namen aus `INVARIANT` (Bewerbungsbegleiter, Claude, Anthropic, CHF, jobs.ch, Job-Room, kununu und weitere in `language_sources.py`).
- Gespeicherte Werte (`DATA_VALUES`, die Stände aus `register.STATUS`).
- Vergleiche (`=== "Gespräch"`, `case`), Schlüssel von Objekten, Klassen, Pfade, Adressen und Kennungen.
- Zeilen mit dem Vermerk `# kein UI-Text` (Python) oder `// kein UI-Text` (JavaScript).

`bewerbungen/tests/test_sprachen.py` läuft im Gate. Es prüft:

- dass der Katalog stimmt (fr und en da und nicht leer, gleiche Platzhalter, Textsätze, die `texte.js` kennt);
- dass er keine Waisen hat (Einträge, die keine Quelle zeigt);
- dass jede Datei in `FERTIG` jeden Text in fr und en hat.

`FERTIG` steht in `bewerbungen/sprachen_pruefen.py` und ist noch leer; die Beispieldateien unter `bewerbungen/tests/fixtures/sprachen/` vertreten die Seiten, eine davon mit einem absichtlich fehlenden Text.

## Eine Seite übersetzen (spätere Schritte)

1. `python -m sprachen_pruefen --alle | grep <seite>` zeigt, was fehlt.
2. Deutsch aussehende Texte in Skripten über `Texte.t` holen. Verkettungen werden Vorlagen mit Platzhaltern. Was kein Text für die Person ist, bekommt den Vermerk `kein UI-Text`.
3. Die Übersetzungen in die Datei der Gruppe in `bewerbungen/sprachen/` schreiben, nach dem Glossar unten.
4. Die HTML-Datei, jedes Skript, das sie lädt, und ihre Routen-Module in `FERTIG` eintragen. Eine Seite ist fertig, wenn alle drei darin stehen.
5. Mit der Vorschau ansehen und den Wortlaut durch die UI/UX-Prüfung geben.

Nur Schritt 1 und der letzte Schritt ändern `bewerbungen/CLAUDE.md`.

## Glossar

Festgelegt im Plan von #95:

| Deutsch | Französisch | Englisch |
| --- | --- | --- |
| RAV | ORP | RAV |
| EFZ | CFC | EFZ |
| EBA | AFP | EBA |
| KI | IA | AI |
| Job-Room | Job-Room | Job-Room |
| Bewerbungsbegleiter | Bewerbungsbegleiter | Bewerbungsbegleiter |

- **Noten** behalten den Dezimalpunkt in jeder Sprache: 4.5, nie 4,5.
- Für Englisch nennt der Plan bei RAV, EFZ und EBA nichts; sie bleiben als Namen der Schweizer Stellen und Abschlüsse stehen, bis die UI/UX-Prüfung anders entscheidet.

Vorschläge für die ersten Seiten, bis die UI/UX-Prüfung sie bestätigt oder ändert:

| Deutsch | Französisch | Englisch |
| --- | --- | --- |
| Anschreiben | lettre de motivation | cover letter |
| Lebenslauf | CV | CV |
| Lehrstelle | place d'apprentissage | apprenticeship |
| Lehrbetrieb | entreprise formatrice | host company |
| Stelle | poste | job |
| Meine Angaben | Mes informations | My details |
| Einladungscode | code d'invitation | invitation code |

- **Beträge** bleiben `CHF 5.00` mit Punkt, **Daten** stehen als 20.11.2026 wie im Deutschen.

## Gespeicherte Werte bleiben deutsch

Was die App speichert oder liest, bleibt in jeder Sprache deutsch; übersetzt wird nur, wie die Seite es zeigt.

- **Stände** der Bewerbungen (Gemerkt, Beworben, Gespräch …) in `bewerbungen.yaml`; die Seite benennt sie (`Texte.statusName`).
- **Werte von `onboarding/form.json`**: Was ins Formular und in `cv.yaml` geht, bleibt deutsch; übersetzt werden nur Beschriftungen (`T` um `optionLabels`, ab #415).
- **Die Grammatik des Suchprofils:** Abschnitte und Labels wie Keywords, Titelfilter, «Nur jobs.ch: …», «(ganzes Wort)», «(nur mit …)». Französische und englische Texte zitieren sie auf Deutsch, damit die Person sie im Suchprofil wiederfindet.
- Code, der deutsche Wörter liest (etwa `split(" (")` in `onboarding/src/dom.js`, «anfordern» in `texte.js`, `MONTH_NAMES`, «Einladung»), bekommt im Schritt seiner Seite eine Lösung pro Sprache.

## Offen für spätere Schritte

- **Routen umstellen:** Die Meldungen des Servers übersetzt `T` seit #415 (Abschnitt oben); die Module der Routen stellen die Schritte ihrer Seiten auf `T` um, `server.py` selbst mit dem gemeinsamen Rahmen.
- **#96, Erweiterung:** nutzt `sprache(k)`, das Katalogformat, den Scanner und das Glossar; die Sprache kommt über eine Antwort, die die Erweiterung schon bekommt.
- **Grösse:** Bei etwa 3500 Texten wird der Katalog pro Sprache rund 300 KB gross; er kommt vom eigenen Rechner.
