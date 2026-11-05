# Mit dem eigenen Claude-Abo arbeiten

Wer ein Abo bei Anthropic hat, kann den Bewerbungsassistenten mit Claude nutzen, ohne Einladung und ohne API-Schlüssel. Claude sucht, bewertet und entwirft; die App hält Register, Unterlagen und Entwürfe.

## So funktioniert es

Sie arbeiten in Claude, angemeldet mit Ihrem eigenen Konto. Claude schreibt über eine lokale Verbindung in die App auf Ihrem Computer.

Die KI-Knöpfe in der App (zum Beispiel „Bewerten“ oder „Entwurf erstellen“) laufen damit **nicht**. Anthropic [erlaubt nicht](https://code.claude.com/docs/en/legal-and-compliance), dass andere Apps Anfragen über die Zugangsdaten eines Abos schicken. Für diese Knöpfe braucht es eine Einladung oder einen [eigenen API-Schlüssel](installation.md#eigener-api-schlüssel-freiwillig). Die Aufgaben selbst erledigt auf diesem Weg Claude.

## Was Sie wissen sollten

- **Klartext:** Claude liest Lebenslauf, Suchprofil, Bausteine und Bewerbungen im Klartext. Die Pseudonymisierung der App gilt auf diesem Weg nicht.
- **Ihr Vertrag:** Es gilt Ihr eigener Vertrag mit Anthropic, auch in den USA. Ob Ihre Chats zum Training dienen, stellen Sie in Claude unter den Einstellungen zum Datenschutz ein.
- **Alter:** Claude setzt laut den [Bedingungen von Anthropic](https://www.anthropic.com/legal/consumer-terms) mindestens 18 Jahre voraus. Für jüngere Lehrstellensuchende passt dieser Weg nicht; sie nutzen die App mit Einladung.
- **Kosten und Grenzen:** Die Nutzung zählt auf die Grenzen Ihres Abos. Eine Suche über mehrere Portale braucht viel davon.
- **Portale:** Claude liest die Portale in Ihrem Browser. Für LinkedIn gilt: LinkedIn verbietet Automatisierung und kann Konten einschränken. Das Risiko liegt bei Ihnen.

Abschicken, „Versand erfassen“, Anmeldungen und alles zum RAV bleiben bei Ihnen. Dafür gibt es keinen Zugang. Jede Änderung an einer Datei sichert die App als Entwurf; unter „Entwürfe“ kommen Sie zurück.

## Einrichten

Sie brauchen ein bezahltes Abo, weil [Claude in Chrome](https://support.claude.com/en/articles/12012173-get-started-with-claude-in-chrome) nur damit läuft.

1. **App laden und starten**, wie in der [Installation](installation.md) beschrieben. Die Einladung und die Browser-Erweiterung des Bewerbungsassistenten können Sie überspringen.
2. **Zugang einschalten:** In der App unter Menü, „Erweiterte Einstellungen“, Abschnitt „Mit dem eigenen Claude-Abo arbeiten“. Hinweise lesen, Häkchen setzen, „Zugang einschalten“.

   ![Abschnitt „Mit dem eigenen Claude-Abo arbeiten“ in den erweiterten Einstellungen, mit den drei Skills, dem Knopf zum Eintragen in Claude Desktop und dem Knopf zum Ausschalten](bilder/einstellungen-claude.jpg)

3. **Skills hochladen:** Laden Sie im selben Abschnitt `einstieg.zip`, `jobsuche.zip` und `bewerbung.zip` herunter. In Claude: [Anpassen, Skills, „+“, Skill hochladen](https://support.claude.com/en/articles/12512180-use-skills-in-claude). Einmal pro Datei; entpacken ist nicht nötig.
4. **Claude mit der App verbinden:** „In Claude Desktop eintragen“ klicken und Claude Desktop einmal ganz beenden und neu öffnen. Die App ändert nur ihren eigenen Eintrag und legt die alte Datei daneben. Claude Code statt Desktop: Der Befehl steht unter „Claude Code oder von Hand eintragen“. Claude Code liest Skills aus dem Ordner `~/.claude/skills/`; entpacken Sie die drei ZIP-Dateien dort.
5. **Browser verbinden:** In Chrome die Erweiterung [Claude in Chrome](https://claude.com/claude-in-chrome) installieren und anmelden. In Claude Desktop unter Einstellungen, Anpassen, Connectors den Eintrag „Claude in Chrome“ einschalten. In Claude Code: `claude --chrome`.

## Beispiel: von der Suche zur Bewerbung

Beispiel mit erfundenen Angaben: Erika Beispiel sucht eine Stelle als Köchin in der Region Bern.

**Angaben erfassen.** Entweder in der App unter „Meine Angaben“, oder in Claude:

> Richte mich im Bewerbungsassistenten ein. Ich suche eine Stelle als Köchin in der Region Bern. Hier ist mein alter Lebenslauf.

Claude fragt nach, was fehlt, und speichert Lebenslauf, Suchprofil, Stil und Bausteine in der App. Claude fragt bei jedem Werkzeug um Erlaubnis. Das können Sie pro Werkzeug dauerhaft erlauben.

**Suchen.**

> Suche neue Stellen nach meinem Suchprofil und bewerte sie.

Claude holt in der App den Suchplan, liest die gewählten Portale in Chrome, gibt die Inserate an die App und bewertet sie. Die Treffer stehen danach in der App unter „Suche“, mit Note und Begründung. Kommt ein Portal mit einer Anmeldung oder einem CAPTCHA, ist das Ihre Aufgabe.

**Bewerben.**

> Bewirb mich auf die Stelle bei der Muster AG: Variante wählen, Anschreiben entwerfen, Unterlagen erstellen und prüfen.

Claude übernimmt die Stelle ins Register, schlägt eine Lebenslauf-Variante vor, schreibt das Anschreiben und baut die PDFs. Sie lesen die PDFs in der App auf der Seite der Bewerbung, schicken selbst ab und klicken danach „Versand erfassen“.

## Häufige Fehler

| Meldung oder Beobachtung | Was hilft |
|---|---|
| „Der Zugang für Claude ist ausgeschaltet.“ | In der App unter „Erweiterte Einstellungen“ einschalten. |
| Claude kennt die Werkzeuge `bewerbungsassistent` nicht | Claude Desktop ganz beenden und neu öffnen. Unter Connectors nachsehen, ob der Eintrag erscheint. |
| „Die Einstellungen von Claude Desktop lassen sich nicht lesen.“ | Die Datei selbst ergänzen. Text und Pfad stehen unter „Claude Code oder von Hand eintragen“. |
| „Die App startet nicht.“ | App von Hand öffnen und nochmals versuchen. |
| Die App wurde verschoben | „In Claude Desktop eintragen“ nochmals klicken. |
| „Bewerten“ in der App meldet, die KI sei nicht eingerichtet | Auf diesem Weg bewertet Claude: „Bewerte die neuen Treffer in der App.“ |

## Wieder ausschalten

„Zugang ausschalten“ sperrt alle Werkzeuge sofort. „Aus Claude Desktop entfernen“ löscht den Eintrag. Die Skills entfernen Sie in Claude unter Anpassen, Skills.
