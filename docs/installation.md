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

1. **Meine Angaben** (im Menü): Wählen Sie die Stellensuche und erfassen Sie Lebenslauf und Suchprofil. Vorhandene Unterlagen als PDF oder Word können Sie hochladen. Die KI macht daraus Vorschläge, und Sie prüfen jeden davon. Zum Schluss klicken Sie auf **Übernehmen**.
2. **Treffer**: Klicken Sie auf **Stellen suchen**. Die Erweiterung sucht auf den Portalen, in Ihrem Browser und nur, wenn Sie die Suche starten.
3. **Bewerten** lässt die KI einschätzen, wie gut eine Stelle zu Ihnen passt. **Übernehmen** legt eine Bewerbung an, **Verwerfen** blendet den Treffer aus.

Abgeschickt wird eine Bewerbung immer von Ihnen selbst.

## Für Lehrstellen

Du installierst alles genau wie oben beschrieben. Lass dir dabei ruhig von deinen Eltern oder deiner Begleitperson helfen, vor allem bei den Warnungen des Computers.

Danach ist Folgendes anders:

1. Unter **Meine Angaben** wählst du die **Lehrstellensuche**. Die Fragen führen dich durch alles, was es braucht.
2. Weisst du noch nicht, welcher Beruf passt? Auf der Seite **Treffer** kann dir die KI Berufe vorschlagen. Du entscheidest, welche du in deine Suche aufnimmst.
3. Auf der Seite **Treffer** wählst du, ob du Lehrstellen, Schnupperlehren oder beides suchst. Die Erweiterung sucht dann auf LENA (berufsberatung.ch) und yousty.

Deine Bewerbung schickst immer du selbst ab.

## Updates

**App:** Gibt es eine neue Version, zeigt die App oben einen Hinweis. Klicken Sie auf **Jetzt aktualisieren**. Ihre Daten und Einstellungen bleiben erhalten.

**Erweiterung:** Die App bringt die neue Version mit. Zeigt die Seite „Einrichtung“, dass eine andere Version geladen ist, öffnen Sie `chrome://extensions` oder `edge://extensions` und klicken bei der Erweiterung auf **Neu laden**.

## Häufige Fehler

| Meldung oder Problem | Was hilft |
|---|---|
| „Für die Suche braucht es die Browser-Erweiterung.“ | Die Erweiterung ist nicht geladen oder ausgeschaltet. Gehen Sie zu [Schritt 4](#schritt-4-browser-erweiterung), oder schalten Sie sie auf der Erweiterungsseite ein. |
| „Keine Verbindung zur KI. Ist der Rechner mit dem Internet verbunden?“ | Prüfen Sie Ihre Internetverbindung und versuchen Sie es nochmals. |
| „Die KI ist noch nicht eingerichtet.“ | Lösen Sie den Einladungscode in [Schritt 3](#schritt-3-ki-unterstützung) ein. |
| „Der Zugang zur KI gilt nicht mehr.“ | Melden Sie sich bei der Person, die Sie im Pilot begleitet. |
| „Das Budget für die KI ist für diesen Monat aufgebraucht.“ | Ab dem nächsten Monat geht es wieder. Alles andere funktioniert weiterhin. |
| „Zuerst in den Ordner Programme verschieben“ (macOS) | Beenden Sie die App, ziehen Sie sie in den Ordner „Programme“ und starten Sie sie von dort. |
| „Der Datenordner … wurde nicht gefunden“ | Liegt er auf einem USB-Stick, stecken Sie ihn ein und laden die Seite neu. Oder wählen Sie einen anderen Ordner. |
| Die Seite der App reagiert nicht mehr | Starten Sie die App neu. Ihre Daten bleiben erhalten. |

Kommen Sie nicht weiter, melden Sie sich bei der Person, die Sie im Pilot begleitet.
