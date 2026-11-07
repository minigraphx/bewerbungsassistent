# Installation und erste Schritte

Der Bewerbungsbegleiter nimmt Ihnen Suche, Formatierung und Verwaltung ab. Die Zeit, die so frei wird, gehört Ihrer Bewerbung: sich mit der Firma und der Stelle befassen und das Anschreiben darauf anpassen.

Diese Anleitung führt Sie von der Installation bis zur ersten Suche. Sie brauchen dazu:

- einen Computer mit Windows, macOS oder Linux,
- den Browser Chrome oder Edge,
- für die KI-Unterstützung einen Einladungscode von Ihrer Begleitperson.

Sie suchen eine Lehrstelle? Die Installation ist dieselbe. Unter [Für Lehrstellen](#für-lehrstellen) steht, was bei dir anders ist.

## 1. App herunterladen und starten

Die neueste Version finden Sie unter [Releases](https://github.com/minigraphx/bewerbungsassistent/releases/latest).

Im Pilot ist die App noch nicht signiert. Darum warnt Ihr Betriebssystem beim ersten Start. Das ist bei dieser Version zu erwarten, und Sie müssen die Warnung einmal bestätigen.

### Windows

1. `Bewerbungsbegleiter-Setup-<Version>.exe` herunterladen und öffnen. Warnt der Browser beim Herunterladen, behalten Sie die Datei.
2. Erscheint „Der Computer wurde durch Windows geschützt“: auf **Weitere Informationen** klicken, dann auf **Trotzdem ausführen**. Die App ist nicht signiert, darum diese Warnung.
3. Die Installation durchlaufen. Administratorrechte braucht es nicht. Die App steht danach im Startmenü.

Die App öffnet sich in Ihrem Browser mit der Seite „Einrichtung“.

### macOS

1. `Bewerbungsbegleiter-<Version>-macOS.zip` herunterladen und im Finder öffnen.
2. **Die App in den Ordner „Programme“ ziehen.** Sonst funktionieren spätere Updates nicht.
3. Die App dort öffnen. macOS warnt und öffnet sie nicht.
4. **Systemeinstellungen → Datenschutz & Sicherheit** öffnen, nach unten scrollen und bei der App auf **Dennoch öffnen** klicken.

Die App öffnet sich in Ihrem Browser mit der Seite „Einrichtung“.

### Linux

Zugesagt ist das aktuelle Ubuntu LTS. Linux Mint baut darauf auf und wird mitgeprüft. Auf anderen Systemen wie Fedora, Debian oder Arch läuft die App meist auch, aber ohne Zusage.

1. `Bewerbungsbegleiter-<Version>-x86_64.AppImage` herunterladen und in einen festen Ordner legen, zum Beispiel `Programme` in Ihrem Benutzerordner. Dort soll die Datei bleiben: Die App meldet sich beim Start unter diesem Pfad an, für den Einladungslink und die Erweiterung.
2. Die Datei ausführbar machen: im Dateimanager unter **Eigenschaften** „Als Programm ausführen“ erlauben, oder im Terminal mit `chmod +x Bewerbungsbegleiter-*.AppImage`.
3. Die Datei doppelt anklicken. Danach steht der Bewerbungsbegleiter auch im Anwendungsmenü.

Die App öffnet sich in Ihrem Browser mit der Seite „Einrichtung“. Für die Erweiterung braucht es Chrome oder Edge als Paket von der Seite des Herstellers, nicht als Snap oder Flatpak (mehr unter [Häufige Fehler](#häufige-fehler)).

## 2. Einrichtung in der App

Die App läuft in Ihrem Browser, aber nur auf Ihrem Computer. Sie beenden sie im Menü **Mehr** mit **Beenden**.

Die Einrichtung hat fünf Schritte und dauert zusammen etwa zehn Minuten. Jeden Schritt können Sie später ändern; Sie finden die Seite im Menü **Mehr** unter **Einrichtung**.

### Schritt 1: Was wird gesucht?

Wählen Sie **Eine Stelle** oder **Eine Lehrstelle**, wie die App Sie ansprechen soll und ob Sie beim RAV gemeldet sind. Mit **Ja** hilft die App beim Eintragen der Arbeitsbemühungen im Job-Room. Klicken Sie dann auf **Weiter**.

### Schritt 2: Datenordner

![Seite Einrichtung mit den fünf Schritten und dem Feld für den Datenordner](bilder/einrichtung-start.jpg)

Hier liegen Ihr Lebenslauf, Ihre Anschreiben und Ihre Bewerbungen. Der Vorschlag unter „Dokumente“ passt meistens: Klicken Sie auf **Ordner anlegen und weiter**. Einen anderen Ordner wählen Sie mit **Ordner wählen …**.

### Schritt 3: Angaben aus einer Datei

Haben Sie schon eine Datei `einstieg.zip` oder `einstieg.json`, zum Beispiel aus Claude, wählen Sie sie mit **Datei wählen …** und klicken auf **Importieren**. Sonst klicken Sie auf **Überspringen** und erfassen Ihre Angaben später unter **Meine Angaben**.

### Schritt 4: KI

![Schritt KI einrichten mit dem Feld für den Einladungscode](bilder/einrichtung-ki.jpg)

Lesen Sie zuerst die Datenschutzerklärung und willigen Sie ein: Die App ist für Erwachsene, und ohne Einwilligung gehen keine Texte an die KI. Bei der Lehrstellensuche richtet ein Elternteil oder die gesetzliche Vertretung die App ein und bestätigt das hier. Widerrufen können Sie jederzeit unter **Erweiterte Einstellungen**.

Tragen Sie danach den Einladungscode ein und klicken Sie auf **Einladung einlösen**. Haben Sie stattdessen einen Einladungslink erhalten, genügt ein Klick darauf; der Code wird nach der Einwilligung eingelöst. Ohne Code geht es mit **Ohne KI weiter**. Suche, Unterlagen und Versand funktionieren dann trotzdem.

### Schritt 5: Browser-Erweiterung

Die Erweiterung sucht in Ihrem Browser nach Stellen und füllt Bewerbungsformulare aus. Ausserdem liest sie auf Klick das Inserat ein, das Sie gerade offen haben, zum Beispiel auf LinkedIn oder der Karriereseite einer Firma: Inserat öffnen, auf ihr Symbol klicken, **Stelle speichern**. In Microsoft Edge kommt sie aus dem Store, für Chrome folgt der Store-Eintrag.

**In Edge:** Auf **Im Edge-Store öffnen** klicken, im [Eintrag bei Edge Add-ons](https://microsoftedge.microsoft.com/addons/detail/mcbcijjbklfeffbollnemgkgnabnmfmp) auf **Abrufen** klicken und bestätigen. Fertig: In der App erscheint von selbst „Die Erweiterung ist bereit“.

**In Chrome und in allen anderen Fällen** laden Sie die Erweiterung einmal von Hand:

![Schritt Browser-Erweiterung mit dem Knopf Im Edge-Store öffnen, den Knöpfen In Chrome öffnen und In Edge öffnen, dem Pfad des Ordners und dem Knopf Ordner zeigen](bilder/einrichtung-erweiterung.jpg)

1. Auf **In Chrome öffnen** oder **In Edge öffnen** klicken. Die Erweiterungsseite und der Ordner der Erweiterung gehen auf.
2. Den **Entwicklermodus** einschalten: in Chrome oben rechts, in Edge links.
3. Den Ordner `erweiterung` auf die Erweiterungsseite ziehen. Geht das nicht: **Entpackte Erweiterung laden** wählen und den Ordner auswählen. Der Knopf **Kopieren** neben dem Pfad hilft dabei: Auf dem Mac fügen Sie den Pfad im Auswahlfenster mit Cmd+Shift+G ein, unter Windows oben in die Adresszeile, unter Linux mit Ctrl+L.

![Erweiterungsseite von Chrome mit eingeschaltetem Entwicklermodus, dem Knopf Entpackte Erweiterung laden und der geladenen Erweiterung](bilder/chrome-erweiterungen.jpg)

Die Erweiterung steht dann in der Liste, und in der App erscheint von selbst „Die Erweiterung ist bereit“.

## 3. Erste Schritte

1. **Meine Angaben**: Erfassen Sie Lebenslauf und Suchprofil. Vorhandene Unterlagen als PDF oder Word können Sie hochladen. Die KI macht daraus Vorschläge, und Sie prüfen jeden davon. Zum Schluss klicken Sie auf **Übernehmen**. Erst danach zählen Ihre Angaben für die Suche.
2. **Stellen suchen**: Klicken Sie auf **Jetzt suchen**. Die Erweiterung sucht auf den Portalen, in Ihrem Browser und nur, wenn Sie die Suche starten. Ohne gewählte Kantone sucht sie in der ganzen Schweiz; Stellen nahe Ihrem Wohnort stehen dann zuerst. Unter **Suche einstellen**, **Wo suchen Sie?**, wählen Sie die Portale. Passen Ihre Begriffe nicht zur Informatik, ist ictjobs zu Beginn ausgeschaltet. Pro Portal holt ein Lauf höchstens 150 neue Inserate, der Rest kommt bei der nächsten Suche.
3. **Bewerten** lässt die KI einschätzen, wie gut eine Stelle zu Ihnen passt. **Übernehmen** legt eine Bewerbung an, **Verwerfen** blendet den Treffer aus.
4. **Bewerben**: Die **Übersicht** zeigt unter **Das steht an**, was als Nächstes zu tun ist, und in der Liste den nächsten Schritt jeder Bewerbung. Öffnen Sie eine Bewerbung und klicken Sie auf **Unterlagen erstellen**. Fehlt noch ein Anschreiben, entwirft die KI dabei zuerst eines; das kann bis zu einer Minute dauern. Der Entwurf ist ein Ausgangspunkt: Lesen Sie ihn, passen Sie ihn mit **Ändern** an die Stelle und die Firma an, und klicken Sie dann auf **Freigeben**. Danach öffnet **Formular öffnen** das Formular der Firma, und die Erweiterung füllt es aus. Haben Sie schon einen fertigen Lebenslauf, entfällt das Erstellen (siehe unten).

Abgeschickt wird eine Bewerbung immer von Ihnen selbst.

### Fertige Dateien verwenden

Unter **Meine Dateien** (im Menü **Mehr**) laden Sie Ihren Lebenslauf als PDF sowie Zertifikate und Zeugnisse hoch. Sie werden so verwendet, wie sie sind. Der Lebenslauf gilt für alle Bewerbungen, bei denen keine Variante gewählt ist. Welche Zertifikate mitgehen, wählen Sie pro Bewerbung. Die Dateien gehen nicht an die KI.

Ein eigenes Anschreiben laden Sie als PDF auf der Seite der Bewerbung hoch, unter **Eigenes Anschreiben**. Es gilt nur für diese Bewerbung und anstelle eines Entwurfs. Solange es gilt, entwirft und prüft die KI dort kein Anschreiben; den Inhalt vergleichen Sie selbst mit dem Inserat. Entfernen Sie die Datei, gilt wieder der Entwurf.

Hat ein Formular nur ein Feld für eine Datei, baut die App daraus ein gemeinsames PDF. Bleibt ein Upload-Feld trotzdem offen, klicken Sie im Balken oder auf der Seite der Bewerbung auf **Dateien im Ordner zeigen**. Die App legt dann alle Dateien der Bewerbung in einen Ordner, öffnet ihn und nennt den Pfad. Von dort ziehen Sie die Datei ins Formular. Oder Sie fügen den Pfad im Datei-Dialog ein: auf dem Mac mit ⇧⌘G, unter Windows im Feld „Dateiname“. Direkt in diesen Ordner kann die App den Datei-Dialog nicht lenken, das lässt der Browser nicht zu.

Ersetzen Sie eine Datei, während ein Formular offen ist, behält das Formular die frühere Fassung. Laden Sie das Formular neu, damit es die aktuelle bekommt. Tauschen Sie die Datei dort nicht von Hand aus: Bei „Abgeschickt? Ja“ hält die App fest, was das Formular von ihr bekommen hat.

Damit das Formular auch Name, Adresse und Kontakt einfüllt, braucht es trotzdem die Angaben unter **Meine Angaben**. Ohne sie bleiben diese Felder leer, und Sie tragen sie selbst ein.

![Seite „Meine Dateien“ mit einem hochgeladenen Lebenslauf, einem Zertifikat und einem Zeugnis, je mit Knopf zum Entfernen](bilder/meine-dateien.jpg)

## Für Lehrstellen

Du installierst alles genau wie oben beschrieben. Lass dir dabei ruhig von deinen Eltern oder deiner Begleitperson helfen, vor allem bei den Warnungen des Computers.

Danach ist Folgendes anders:

1. Unter **Meine Angaben** wählst du die **Lehrstellensuche**. Die Fragen führen dich durch alles, was es braucht.
2. Weisst du noch nicht, welcher Beruf passt? Auf der Seite **Stellen suchen** kann dir die KI Berufe vorschlagen. Du entscheidest, welche du in deine Suche aufnimmst.
3. Unter **Suche einstellen** wählst du, ob du Lehrstellen, Schnupperlehren oder beides suchst. Die Erweiterung sucht dann auf LENA (berufsberatung.ch) und yousty. Unter **Wo suchst du?** kannst du eines davon ausschalten.

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

![Abschnitt Eigener API-Schlüssel mit den Hinweisen, dem Häkchen und dem Feld für den Schlüssel](bilder/einstellungen-schluessel.jpg)

1. Im Menü **Mehr** die **Erweiterten Einstellungen** öffnen.
2. Die Hinweise lesen und das Häkchen setzen.
3. Den Schlüssel einfügen und auf **Prüfen und speichern** klicken.

Die App prüft den Schlüssel mit einem kleinen, kostenlosen Aufruf. Zum Guthaben sagt diese Prüfung nichts: Fehlt es, merken Sie das erst beim ersten Aufruf der KI. Der Schlüssel liegt danach nur im Schlüsselbund Ihres Computers, nie im Datenordner und nie in der Browser-Erweiterung.

Was die KI gekostet hat, steht oben auf derselben Seite unter **Kosten der KI**. Das ist die eigene Notiz der App. Massgebend ist die Abrechnung von Anthropic.

### Weitere Seiten durchsuchen

Mit gespeichertem Schlüssel erscheint auf derselben Seite dieser Abschnitt. Hier tragen Sie Seiten ein, auf denen die Suche zusätzlich schauen soll, zum Beispiel die offenen Stellen einer Firma.

![Abschnitt Eigener API-Schlüssel mit gespeichertem Schlüssel und darunter Weitere Seiten durchsuchen mit zwei erfundenen Adressen und den Knöpfen Seiten speichern und Zugriff in der Erweiterung erlauben](bilder/einstellungen-seiten.jpg)

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

**App:** Gibt es eine neue Version, fragt die App beim Start in einem Fenster nach. Klicken Sie auf **Installieren**, oder auf **Später** und arbeiten Sie weiter. Dann steht oben ein Hinweis mit **Jetzt aktualisieren**, und beim nächsten Start fragt die App wieder. Beim **Beenden** installiert sich die neue Version von selbst im Hintergrund, beim nächsten Start läuft sie. Ihre Daten und Einstellungen bleiben erhalten.

**Unter Linux** installiert sich die App nicht selbst: Auf **Neue Version herunterladen** klicken, die neue AppImage-Datei an die Stelle der alten legen und ausführbar machen. Ihre Daten und Einstellungen bleiben erhalten.

**Erweiterung:** Die App bringt die neue Version mit, und die Erweiterung lädt sich von selbst neu, sobald die App läuft und keine Suche oder kein Formular offen ist. Sie müssen nichts tun. Der Entwicklermodus muss dafür eingeschaltet bleiben. Zeigt die Seite „Einrichtung“ trotzdem eine andere Version, öffnen Sie `chrome://extensions` oder `edge://extensions` und klicken bei der Erweiterung auf **Neu laden**. Das ist auch beim Wechsel auf die erste Version mit dieser Funktion einmal nötig.

### Wechsel von Version 0.2.10 oder älter

Bis Version 0.2.10 hiess die App technisch `Bewerbungsassistent`. Von dort aktualisiert sie sich nicht von selbst: Sie zeigt nur den Link zum Herunterladen. Laden Sie die neue Version einmal von Hand und installieren Sie sie wie oben. Danach geht es wieder von selbst.

Beim ersten Start übernimmt die neue Version Ihre Einstellungen, den Datenordner und den Zugang zur KI. Der Mac fragt dabei unter Umständen einmal nach Ihrem Passwort für den Schlüsselbund. Lehnen Sie ab, lösen Sie Ihre Einladung neu ein. Eine noch offene alte App wird dabei beendet.

Von Hand bleibt:

- **Mac:** Die alte `Bewerbungsassistent.app` aus „Programme“ löschen. Windows entfernt die alte Version selbst.
- **Erweiterung:** Die alte Erweiterung auf der Erweiterungsseite des Browsers entfernen und den neuen Ordner laden, wie in Schritt 5 beschrieben.
- **Eigenes Claude-Abo:** Die drei Skills in der App neu herunterladen und in Claude ersetzen, und Claude Desktop einmal neu starten. Haben Sie die App in Claude Code eingetragen: `claude mcp remove bewerbungsassistent` und den Befehl aus den Einstellungen neu ausführen.

Einladungslinks, die mit `bewerbungsassistent://` beginnen, öffnen die App nicht mehr. Geben Sie den Code in diesem Fall in der App ein.

## Häufige Fehler

| Meldung oder Problem | Was hilft |
|---|---|
| „Diese Seite öffnet sich nur über die App“ | Sie haben die Adresse von Hand geöffnet oder in einem anderen Browser. Öffnen Sie den Bewerbungsbegleiter über sein Programmsymbol, auch wenn er schon läuft. Andere Konten auf demselben Rechner kommen so nicht an Ihre Daten. |
| Windows blockiert die Datei, und **Trotzdem ausführen** fehlt | Vermutlich ist [Smart App Control](https://support.microsoft.com/de-de/windows/smart-app-control-frequently-asked-questions-285ea03d-fa88-4d56-882e-6698afdb7003) aktiv. Es blockiert nicht signierte Programme, und laut Microsoft gibt es keine Ausnahme für einzelne Programme. Die App läuft dann nur, wenn Sie es in der Windows-Sicherheit ausschalten. Das gilt für alle Programme; entscheiden Sie das bewusst, bei Jugendlichen zusammen mit der Begleitperson. |
| „Für die Suche braucht es die Browser-Erweiterung.“ | Die Erweiterung ist nicht geladen oder ausgeschaltet. Gehen Sie zu [Schritt 5](#schritt-5-browser-erweiterung), oder schalten Sie sie auf der Erweiterungsseite ein. |
| „Keine Verbindung zur KI. Ist der Rechner mit dem Internet verbunden?“ | Prüfen Sie Ihre Internetverbindung und versuchen Sie es nochmals. |
| „Vor der ersten KI-Nutzung braucht es die Einwilligung“ | Willigen Sie unter **Erweiterte Einstellungen**, Abschnitt **Einwilligung**, ein. |
| „Die KI ist noch nicht eingerichtet.“ | Lösen Sie den Einladungscode in [Schritt 4](#schritt-4-ki) ein. |
| „Der Zugang zur KI gilt nicht mehr.“ | Melden Sie sich bei der Person, die Sie im Pilot begleitet. |
| „Das Budget für die KI ist für diesen Monat aufgebraucht.“ | Ab dem nächsten Monat geht es wieder. Alles andere funktioniert weiterhin. |
| „Das sieht nicht wie ein API-Schlüssel aus.“ | Fügen Sie den ganzen Schlüssel aus der Console ein, ohne etwas davor oder danach. |
| „Dieser Schlüssel gilt nicht.“ | Prüfen Sie in der [Console](https://platform.claude.com/settings/keys), ob es ihn noch gibt, oder erstellen Sie einen neuen. Gespeichert wurde nichts. |
| „Das Guthaben bei Anthropic reicht nicht mehr.“ | Laden Sie unter [Billing](https://platform.claude.com/settings/billing) nach, oder entfernen Sie den eigenen Schlüssel. |
| „Zuerst in den Ordner Programme verschieben“ (macOS) | Beenden Sie die App, ziehen Sie sie in den Ordner „Programme“ und starten Sie sie von dort. |
| „Der Datenordner … wurde nicht gefunden“ | Liegt er auf einem USB-Stick, stecken Sie ihn ein und laden die Seite neu. Oder wählen Sie einen anderen Ordner. |
| Die Seite der App reagiert nicht mehr | Starten Sie die App neu. Ihre Daten bleiben erhalten. |
| Linux: Das AppImage startet nicht, und es erscheint ein Hinweis auf FUSE | Unter Ubuntu und Mint `sudo apt install fuse3`, unter Arch `sudo pacman -S fuse3`, unter Fedora `sudo dnf install fuse3`. Danach die Datei erneut öffnen. |
| Linux: Die Erweiterung findet die App nicht | Chrome oder Edge laufen vermutlich als Snap oder Flatpak, etwa das Chromium von Ubuntu. Solche Browser dürfen keine Programme ausserhalb starten. Installieren Sie Chrome oder Edge als `.deb`-Paket von der Seite von Google oder Microsoft und starten Sie danach die App einmal neu. |
| Linux: „Der Zugang liess sich nicht im Schlüsselbund des Systems ablegen“ | Die App legt den Zugang zur KI nur verschlüsselt ab, im Schlüsselbund des Systems. Ubuntu und Mint haben ihn. Auf schlanken Desktops fehlt er manchmal: den GNOME-Schlüsselbund (`gnome-keyring`) oder KWallet installieren, neu anmelden und den Einladungslink nochmals öffnen. |
| Linux: „Für den Auswahldialog fehlt zenity oder kdialog“ | Den Pfad ins Feld darunter tippen, oder `zenity` installieren (`sudo apt install zenity`). |

Kommen Sie nicht weiter, melden Sie sich bei der Person, die Sie im Pilot begleitet.
