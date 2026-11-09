# Häufige Fragen

Hier steht genau, was die App vor dem Senden an die KI ersetzt, wo das an Grenzen stösst, warum das Portal ictjobs an oder aus ist und ob mehrere Personen die App nutzen können. Die Beispiele sind erfunden.

- [Was sieht die KI von mir?](#was-sieht-die-ki-von-mir)
- [Was ersetzt die App?](#was-ersetzt-die-app)
- [Welche Schreibweisen erkennt sie?](#welche-schreibweisen-erkennt-sie)
- [Was erkennt sie nicht?](#was-erkennt-sie-nicht)
- [Was bleibt absichtlich stehen?](#was-bleibt-absichtlich-stehen)
- [Was passiert, wenn trotzdem etwas im Text bleibt?](#was-passiert-wenn-trotzdem-etwas-im-text-bleibt)
- [Gilt das auch mit eigenem Schlüssel oder eigenem Claude-Abo?](#gilt-das-auch-mit-eigenem-schlüssel-oder-eigenem-claude-abo)
- [Warum ist ictjobs an oder aus?](#warum-ist-ictjobs-an-oder-aus)
- [Wie schalte ich ictjobs ein oder aus?](#wie-schalte-ich-ictjobs-ein-oder-aus)
- [Für Lehrstellen](#für-lehrstellen)
- [Können mehrere Personen die App nutzen?](#können-mehrere-personen-die-app-nutzen)

## Was sieht die KI von mir?

Bevor ein Text zur KI geht, ersetzt die App Ihre persönlichen Angaben durch Platzhalter. Aus «Léa Müller-Brändli, 079 123 45 67» wird «{{NAME}}, {{PHONE}}». In der Antwort setzt die App Ihre Angaben wieder ein. Die KI erfährt so, was Sie können, aber nicht, wer Sie sind.

Das gilt für jeden Aufruf der KI, zum Beispiel beim Bewerten der Treffer, beim Entwurf und bei der Prüfung des Anschreibens, bei der Hilfe in Bewerbungsformularen und beim Einlesen Ihrer Angaben aus einer Datei.

## Was ersetzt die App?

Aus Ihren Angaben unter Meine Angaben:

- Ihren Namen, auch Vor- und Nachnamen einzeln, weitere Vornamen und jeden Teil eines Doppelnamens
- Adresse, Postleitzahl, Telefon, E-Mail, Webseite, Profil-Links und die Benutzernamen darin, Geburtsdatum
- die Namen Ihrer Referenzen

Aus der Bewerbung und dem Anschreiben:

- die Kontaktperson der Firma mit ihrer E-Mail und Telefonnummer
- Empfänger im Anschreiben, die mit «Frau» oder «Herr» beginnen

Im Inserat und in anderen Texten, die zur KI gehen:

- E-Mail-Adressen und Telefonnummern
- Namen nach «Frau» oder «Herr», etwa «Frau Petra Meier»
- Namen in einer persönlichen E-Mail-Adresse wie petra.meier@…, nicht aber Postfächer wie info@ oder jobs@

Lesen Sie Ihre Angaben aus einer Datei ein, findet die App in diesen Dokumenten zusätzlich Strasse und Hausnummer, Postleitzahl mit Ort, Geburtsdatum, Heimatort, Zivilstand, Nationalität, AHV-Nummer und Links.

## Welche Schreibweisen erkennt sie?

- Gross- und Kleinschreibung und zusätzliche Leerzeichen
- die Form mit s: «Müller-Brändlis Lebenslauf»
- eine andere Reihenfolge wie «Brändli Léa» oder ein Leerzeichen statt des Bindestrichs wie «Müller Brändli», weil jeder Teil einzeln ersetzt wird
- Namen ohne Umlaute oder Akzente: «Mueller-Braendli», «Lea Muller-Brandli»
- Telefonnummern in jeder Schweizer Schreibweise: «0791234567», «+41 79 123 45 67», «+41 (0)79 123 45 67», «0041 79 123 45 67», auch mit Punkten oder Schrägstrichen wie «079.123.45.67» oder «079/123 45 67»
- das Geburtsdatum als «3.3.1994», «03.03.94», «1994-03-03», «3. März 1994» oder «3. Mär. 1994»
- Links mit oder ohne https:// und www: «lea-beispiel.ch», «http://lea-beispiel.ch/»

## Was erkennt sie nicht?

- Spitznamen, Kurzformen und Tippfehler wie «Lele» oder «Müler»
- den Anfangsbuchstaben in «L. Müller-Brändli»: Der Nachname wird ersetzt, das «L.» bleibt stehen
- Namensteile unter drei Buchstaben, wenn sie allein stehen, etwa «Li»; im ganzen Namen werden sie mit ersetzt
- Datumsformen wie «03/03/1994» oder «März 1994»
- Namen anderer Personen ohne «Frau» oder «Herr», etwa «Peter Meier» in einem Zeugnis. Tragen Sie die Kontaktperson einer Firma darum in das Feld Kontaktperson der Bewerbung ein.

Tipp: Tragen Sie Ihren Namen unter Meine Angaben genau so ein wie im Lebenslauf. Ersetzen kann die App nur, was dort richtig eingetragen ist.

## Was bleibt absichtlich stehen?

Arbeitgeber, Ausbildungen, Funktionen, Jahreszahlen und der Name Ihres Wohnorts. Die KI braucht sie, um Stellen einzuschätzen und Anschreiben zu entwerfen.

Postleitzahlen von 1900 bis 2099 sehen aus wie Jahreszahlen und bleiben darum ebenfalls stehen, damit die Jahre im Lebenslauf lesbar bleiben.

## Was passiert, wenn trotzdem etwas im Text bleibt?

Kurz vor dem Senden prüft die App den Text ein zweites Mal, mit eigenen Regeln. Findet sie noch eine E-Mail-Adresse, eine Telefonnummer oder einen Ihrer Werte, sendet sie nichts. Ihren Namen und andere Werte mit mindestens zehn Buchstaben findet sie dabei auch zusammengeschrieben und ohne Umlaute oder Akzente, etwa «LeaMuellerBraendli».

Sie sehen dann eine Meldung wie diese:

> Persönliche Angaben wären an die KI gegangen (E-Mail, Name); nichts gesendet.

In der Klammer steht, welche Art von Angabe gefunden wurde, nie der Wert selbst. Entfernen Sie die Angabe aus dem Text, oder tragen Sie sie unter Meine Angaben richtig ein, und versuchen Sie es noch einmal.

## Gilt das auch mit eigenem Schlüssel oder eigenem Claude-Abo?

Mit einem eigenen Schlüssel von Anthropic ersetzt die App genau gleich wie über die Vermittlung.

Mit dem eigenen Claude-Abo arbeitet Claude selbst mit Ihren Dateien und liest sie im Klartext; die Platzhalter gibt es auf diesem Weg nicht. Mehr dazu in der [Anleitung zum eigenen Abo](eigenes-abo.md).

## Warum ist ictjobs an oder aus?

Auf ictjobs stehen nur Stellen aus der Informatik. Wer im Handwerk oder in der Pflege sucht, findet dort nichts. Bei der Lehrstellensuche gibt es ictjobs nicht.

Bis Sie die Portale selbst gewählt haben, schaut die App Ihre Suchbegriffe an:

- Klingt ein Suchbegriff nach Informatik, etwa «Software-Entwickler», «Data Engineer» oder «Informatiker», ist ictjobs an.
- Klingt keiner danach, ist ictjobs aus. Begriffe wie «Administration», «Datenschutz», «Systemgastronomie» oder «Testfahrer» zählen nicht als Informatik.
- Ohne Suchbegriffe ist ictjobs an, ebenso wenn sonst kein Portal an wäre.
- Schliesst Ihr Suchprofil ictjobs aus, bleibt es aus.

Unter dem Häkchen steht meist in einem Satz, warum ictjobs gerade an oder aus ist.

## Wie schalte ich ictjobs ein oder aus?

Unter Stellen suchen › Suche einstellen › Wo suchen Sie? setzen oder entfernen Sie das Häkchen bei ictjobs. Ab der ersten Änderung gilt Ihre Wahl für alle Portale, auch wenn sich Ihre Suchbegriffe später ändern; die App schaltet dann nichts mehr von selbst um. Mindestens ein Portal bleibt an, sonst findet die Suche nichts.

## Für Lehrstellen

Für dich gilt alles, was oben steht. Dazu ersetzt die App bei der Lehrstellensuche auch die Namen deiner Schulen. Das gilt auch, solange noch kein Suchprofil da ist. Gesucht wird auf LENA und yousty, ictjobs gibt es hier nicht.

## Können mehrere Personen die App nutzen?

Ja. Jede Person hat ihren eigenen Datenordner mit Lebenslauf, Anschreiben und Bewerbungen. Am einfachsten hat jede Person ein eigenes Benutzerkonto auf dem Computer und richtet die App dort ein. Dann hat sie auch ihren eigenen Zugang zur KI.

Teilen sich mehrere Personen ein Benutzerkonto, wechseln sie unter Mehr › Einrichtung › Datenordner zum Ordner der anderen Person. Der Zugang zur KI gehört aber zum Benutzerkonto, nicht zum Datenordner: Alle nutzen dann denselben Zugang und dasselbe Budget, auch mit einem eigenen API-Schlüssel. Wie der Wechsel geht und was Sie vorher abschliessen, steht in der Anleitung unter [Mehrere Personen](installation.md#mehrere-personen).
