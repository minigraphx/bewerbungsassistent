# Installation und erste Schritte

Diese Anleitung führt Sie von der Installation bis zur ersten Suche. Sie brauchen dazu:

- einen Computer mit Windows oder macOS,
- den Browser Chrome oder Edge,
- für die KI-Unterstützung einen Einladungscode von Ihrer Begleitperson.

Sie suchen eine Lehrstelle? Die Installation ist dieselbe. Unter [Für Lehrstellen](#für-lehrstellen) steht, was bei dir anders ist.

## 1. App herunterladen und starten

Die neueste Version finden Sie unter [Releases](https://github.com/minigraphx/bewerbungsassistent/releases/latest).

Im Pilot ist die App noch nicht signiert. Darum warnt Ihr Betriebssystem beim ersten Start. Das ist bei dieser Version zu erwarten, und Sie müssen die Warnung einmal bestätigen.

### Windows

1. `Bewerbungsassistent-Setup-<Version>.exe` herunterladen und öffnen.
2. Erscheint „Der Computer wurde durch Windows geschützt“: auf **Weitere Informationen** klicken, dann auf **Trotzdem ausführen**.
3. Die Installation durchlaufen. Administratorrechte braucht es nicht. Die App steht danach im Startmenü.

Die App öffnet sich in Ihrem Browser mit der Seite „Einrichtung“.

### macOS

1. `Bewerbungsassistent-<Version>-macOS.zip` herunterladen und im Finder öffnen.
2. **Die App in den Ordner „Programme“ ziehen.** Sonst funktionieren spätere Updates nicht.
3. Die App dort öffnen. macOS warnt und öffnet sie nicht.
4. **Systemeinstellungen → Datenschutz & Sicherheit** öffnen, nach unten scrollen und bei der App auf **Dennoch öffnen** klicken.

Die App öffnet sich in Ihrem Browser mit der Seite „Einrichtung“.

## 2. Einrichtung in der App

Die App läuft in Ihrem Browser, aber nur auf Ihrem Computer. Sie beenden sie oben rechts mit **Beenden**.

![Seite Einrichtung mit den Schritten Datenordner und Angaben aus der Einstiegsvorlage](bilder/einrichtung-start.jpg)

### Schritt 1: Datenordner

Hier liegen Ihr Lebenslauf, Ihre Anschreiben und Ihre Bewerbungen. Der Vorschlag unter „Dokumente“ passt meistens: Klicken Sie auf **Diesen Ordner verwenden**.

### Schritt 2: Angaben aus der Einstiegsvorlage

Haben Sie die Einstiegsvorlage schon ausgefüllt, wählen Sie die Datei `einstieg.zip` oder `einstieg.json` und klicken auf **Importieren**. Sonst überspringen Sie diesen Schritt und erfassen Ihre Angaben später.

### Schritt 3: KI-Unterstützung

![Schritt KI-Unterstützung mit dem Feld für den Einladungscode](bilder/einrichtung-ki.jpg)

Tragen Sie den Einladungscode ein und klicken Sie auf **Einladung einlösen**. Haben Sie stattdessen einen Einladungslink erhalten, genügt ein Klick darauf.

### Schritt 4: Browser-Erweiterung

Die Erweiterung sucht in Ihrem Browser nach Stellen. Bis sie im Store ist, laden Sie sie einmal von Hand.

![Schritt Browser-Erweiterung mit den Knöpfen In Chrome öffnen, In Edge öffnen, Pfad kopieren und Ordner zeigen](bilder/einrichtung-erweiterung.jpg)

1. Auf **In Chrome öffnen** oder **In Edge öffnen** klicken. Die Erweiterungsseite und der Ordner der Erweiterung gehen auf.
2. Den **Entwicklermodus** einschalten: in Chrome oben rechts, in Edge links.
3. Den Ordner `erweiterung` auf die Erweiterungsseite ziehen. Geht das nicht: **Entpackte Erweiterung laden** wählen und den Ordner auswählen. Der Knopf **Pfad kopieren** hilft dabei: Auf dem Mac fügen Sie den Pfad im Auswahlfenster mit Cmd+Shift+G ein, unter Windows oben in die Adresszeile.

![Erweiterungsseite von Chrome mit eingeschaltetem Entwicklermodus, dem Knopf Entpackte Erweiterung laden und der geladenen Erweiterung](bilder/chrome-erweiterungen.jpg)

Die Erweiterung steht dann in der Liste, und in der App erscheint von selbst „Die Erweiterung ist bereit“.

## 3. Erste Schritte

1. **Meine Angaben** (im Menü): Wählen Sie die Stellensuche und erfassen Sie Lebenslauf und Suchprofil. Vorhandene Unterlagen als PDF oder Word können Sie hochladen. Die KI macht daraus Vorschläge, und Sie prüfen jeden davon. Zum Schluss klicken Sie auf **Übernehmen**. Erst danach zählen Ihre Angaben für die Suche.
2. **Suche**: Klicken Sie auf **Stellen suchen**. Die Erweiterung sucht auf den Portalen, in Ihrem Browser und nur, wenn Sie die Suche starten. Ohne gewählte Kantone sucht sie in der ganzen Schweiz; Stellen nahe Ihrem Wohnort stehen dann zuerst. Unter **Wo suchen Sie?** wählen Sie die Portale. Passen Ihre Begriffe nicht zur Informatik, ist ictjobs zu Beginn ausgeschaltet. Pro Portal holt ein Lauf höchstens 150 neue Inserate, der Rest kommt bei der nächsten Suche.
3. **Bewerten** lässt die KI einschätzen, wie gut eine Stelle zu Ihnen passt. **Übernehmen** legt eine Bewerbung an, **Verwerfen** blendet den Treffer aus.

Abgeschickt wird eine Bewerbung immer von Ihnen selbst.

## Für Lehrstellen

Du installierst alles genau wie oben beschrieben. Lass dir dabei ruhig von deinen Eltern oder deiner Begleitperson helfen, vor allem bei den Warnungen des Computers.

Danach ist Folgendes anders:

1. Unter **Meine Angaben** wählst du die **Lehrstellensuche**. Die Fragen führen dich durch alles, was es braucht.
2. Weisst du noch nicht, welcher Beruf passt? Auf der Seite **Suche** kann dir die KI Berufe vorschlagen. Du entscheidest, welche du in deine Suche aufnimmst.
3. Auf der Seite **Suche** wählst du, ob du Lehrstellen, Schnupperlehren oder beides suchst. Die Erweiterung sucht dann auf LENA (berufsberatung.ch) und yousty. Unter **Wo suchst du?** kannst du eines davon ausschalten.

Deine Bewerbung schickst immer du selbst ab.

## Eigenes Claude-Abo (freiwillig)

Wer ein Abo bei Anthropic hat, kann auch in Claude arbeiten und das Ergebnis in die App schreiben lassen, ohne Einladung. Die KI-Knöpfe der App laufen damit nicht. Mehr dazu in der Anleitung [Mit dem eigenen Claude-Abo arbeiten](eigenes-abo.md).

## Eigener API-Schlüssel (freiwillig)

Sie brauchen das nicht: Die App läuft auch mit dem Einladungscode allein. Ein eigener Schlüssel lohnt sich, wenn Sie mehr KI nutzen möchten, als Ihr Budget im Pilot erlaubt, oder wenn die Suche zusätzliche Seiten lesen soll. Das geht nur mit eigenem Schlüssel.

Das ändert sich damit:

- Die KI-Aufrufe gehen direkt an die Claude API, nicht mehr über die Vermittlung. Namen und andere persönliche Angaben werden auch dann vor dem Senden ersetzt.
- Sie tragen die Kosten selbst. Anthropic rechnet direkt mit Ihnen ab.
- Für die Verarbeitung gilt Ihr eigener Vertrag mit Anthropic, auch in den USA.

### Schlüssel bei Anthropic holen

Auch mit einem Abo von Claude brauchen Sie dafür ein Konto in der Console, denn die API rechnet Anthropic [getrennt vom Abo](https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-do-i-have-to-pay-separately-to-use-the-claude-api-and-console) ab.

1. In der [Claude Console](https://platform.claude.com/) ein Konto eröffnen oder sich anmelden.
2. Unter [Billing](https://platform.claude.com/settings/billing) Guthaben kaufen. Die API läuft [im Voraus bezahlt](https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage): Ist das Guthaben aufgebraucht, hält sie an, bis Sie nachladen. Automatisches Nachladen müssen Sie nicht einschalten; ohne bleibt das Guthaben Ihre Obergrenze.
3. Unter [API keys](https://platform.claude.com/settings/keys) einen Schlüssel erstellen und kopieren.

Behandeln Sie den Schlüssel wie ein Passwort: Wer ihn hat, kann auf Ihre Kosten die KI nutzen. Geben Sie ihn nicht weiter und schicken Sie ihn nicht per E-Mail. Ist er doch einmal in fremde Hände geraten, löschen Sie ihn in der Console.

### Schlüssel in der App eintragen

![Seite Erweiterte Einstellungen mit den Hinweisen, dem Häkchen und dem Feld für den API-Schlüssel](bilder/einstellungen-schluessel.jpg)

1. Im Menü **Erweiterte Einstellungen** öffnen.
2. Die Hinweise lesen und das Häkchen setzen.
3. Den Schlüssel einfügen und auf **Prüfen und speichern** klicken.

Die App prüft den Schlüssel mit einem kleinen, kostenlosen Aufruf. Zum Guthaben sagt diese Prüfung nichts: Fehlt es, merken Sie das erst beim ersten Aufruf der KI. Der Schlüssel liegt danach nur im Schlüsselbund Ihres Computers, nie im Datenordner und nie in der Browser-Erweiterung.

Was die KI gekostet hat, steht unten auf derselben Seite unter **Kosten der KI**. Das ist die eigene Notiz der App. Massgebend ist die Abrechnung von Anthropic.

### Weitere Seiten durchsuchen

Mit gespeichertem Schlüssel erscheint auf derselben Seite dieser Abschnitt. Hier tragen Sie Seiten ein, auf denen die Suche zusätzlich schauen soll, zum Beispiel die offenen Stellen einer Firma.

![Abschnitt Weitere Seiten durchsuchen mit zwei erfundenen Adressen und den Knöpfen Seiten speichern und Zugriff in der Erweiterung erlauben](bilder/einstellungen-seiten.jpg)

1. Unter **Adressen** höchstens fünf Adressen eintragen, eine pro Zeile. Kopieren Sie die Adresse einfach aus der Adresszeile des Browsers, etwa `https://www.beispiel.ch/stellen`.
2. Auf **Seiten speichern** klicken.
3. Auf **Zugriff in der Erweiterung erlauben** klicken. Die Erweiterung öffnet eine eigene Seite. Dort klicken Sie auf **Zugriff erlauben und weiter** und bestätigen die Frage des Browsers. Das ist einmal nötig.

Ab der nächsten Suche kommen die Seiten dazu. Hat eine Seite ein Suchfeld, sucht die App dort mit den Begriffen aus Ihrem Suchprofil. Sonst liest sie die Stellen, die auf der Seite stehen. Findet sie nichts, öffnen Sie im Browser die Seite mit den offenen Stellen und tragen deren Adresse ein.

Die Suche liest pro Seite und Lauf höchstens zehn Ergebnisseiten und dreissig Inserate, mit Pausen dazwischen. Verlangt eine Seite eine Anmeldung oder ein CAPTCHA, überspringt die Suche sie. Das erledigt die App nicht für Sie.

**LinkedIn** verbietet Automatisierung und kann Konten einschränken oder sperren. Tragen Sie LinkedIn als Seite ein, liegt dieses Risiko bei Ihnen. Auch andere Portale regeln in ihren Bedingungen, was automatisiert erlaubt ist. Prüfen Sie das, bevor Sie ein Portal eintragen.

### Schlüssel entfernen

Klicken Sie unter **Erweiterte Einstellungen** auf **Schlüssel entfernen**. Danach läuft die App wieder über die Vermittlung, und die Erweiterung gibt den Zugriff auf alle Seiten ab. Die weiteren Seiten werden dann nicht mehr durchsucht.

Bei Anthropic bleibt der Schlüssel bestehen. Brauchen Sie ihn nicht mehr, löschen Sie ihn auch in der Console.

## Updates

**App:** Gibt es eine neue Version, zeigt die App oben einen Hinweis. Klicken Sie auf **Jetzt aktualisieren**. Ihre Daten und Einstellungen bleiben erhalten.

**Erweiterung:** Die App bringt die neue Version mit, und die Erweiterung lädt sich von selbst neu, sobald die App läuft und keine Suche oder kein Formular offen ist. Sie müssen nichts tun. Der Entwicklermodus muss dafür eingeschaltet bleiben. Zeigt die Seite „Einrichtung“ trotzdem eine andere Version, öffnen Sie `chrome://extensions` oder `edge://extensions` und klicken bei der Erweiterung auf **Neu laden**. Das ist auch beim Wechsel auf die erste Version mit dieser Funktion einmal nötig.

## Häufige Fehler

| Meldung oder Problem | Was hilft |
|---|---|
| „Für die Suche braucht es die Browser-Erweiterung.“ | Die Erweiterung ist nicht geladen oder ausgeschaltet. Gehen Sie zu [Schritt 4](#schritt-4-browser-erweiterung), oder schalten Sie sie auf der Erweiterungsseite ein. |
| „Keine Verbindung zur KI. Ist der Rechner mit dem Internet verbunden?“ | Prüfen Sie Ihre Internetverbindung und versuchen Sie es nochmals. |
| „Die KI ist noch nicht eingerichtet.“ | Lösen Sie den Einladungscode in [Schritt 3](#schritt-3-ki-unterstützung) ein. |
| „Der Zugang zur KI gilt nicht mehr.“ | Melden Sie sich bei der Person, die Sie im Pilot begleitet. |
| „Das Budget für die KI ist für diesen Monat aufgebraucht.“ | Ab dem nächsten Monat geht es wieder. Alles andere funktioniert weiterhin. |
| „Das sieht nicht wie ein API-Schlüssel aus.“ | Fügen Sie den ganzen Schlüssel aus der Console ein, ohne etwas davor oder danach. |
| „Dieser Schlüssel gilt nicht.“ | Prüfen Sie in der [Console](https://platform.claude.com/settings/keys), ob es ihn noch gibt, oder erstellen Sie einen neuen. Gespeichert wurde nichts. |
| „Das Guthaben bei Anthropic reicht nicht mehr.“ | Laden Sie unter [Billing](https://platform.claude.com/settings/billing) nach, oder entfernen Sie den eigenen Schlüssel. |
| „Zuerst in den Ordner Programme verschieben“ (macOS) | Beenden Sie die App, ziehen Sie sie in den Ordner „Programme“ und starten Sie sie von dort. |
| „Der Datenordner … wurde nicht gefunden“ | Liegt er auf einem USB-Stick, stecken Sie ihn ein und laden die Seite neu. Oder wählen Sie einen anderen Ordner. |
| Die Seite der App reagiert nicht mehr | Starten Sie die App neu. Ihre Daten bleiben erhalten. |

Kommen Sie nicht weiter, melden Sie sich bei der Person, die Sie im Pilot begleitet.
