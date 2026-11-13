"use strict";
// Text sets of the pages (MIN-369, docs/design/texte.md): a job with Sie, a job with du, an apprenticeship with du.
// The set follows the choice in the setup (GET /api/einrichtung/wahl, `textsatz`). Only texts that speak to the
// person are here; neutral texts stay in the page. An entry is { sie, du, lehrstelle? }: an apprenticeship falls
// back to du. „du“, „dein“, „dir“ are lower case except at the start of a sentence.
// Pages add their texts here when they are redesigned. No DOM in choosing a text, so it can be tested.
(function (global) {
  const SAETZE = ["stelle-sie", "stelle-du", "lehrstelle-du"];
  const VORGABE = "stelle-sie";

  const TEXTE = {
    // Navigation (step 3)
    "nav.suche": { sie: "Stellen suchen", du: "Stellen suchen", lehrstelle: "Lehrstellen suchen" },
    "nav.stellen": { sie: "Stellen", du: "Stellen", lehrstelle: "Lehrstellen" },
    // Other pages (step 6)
    "dateien.variante": { sie: "Wenn Sie in einer Bewerbung eine Variante wählen, gilt sie dort.", du: "Wenn du in einer Bewerbung eine Variante wählst, gilt sie dort." },
    "dateien.eigen-titel": { sie: "Ihr eigenes PDF", du: "Dein eigenes PDF" },
    "dateien.eigen": { sie: "Sonst gilt der Lebenslauf, den Sie hier hochladen.", du: "Sonst gilt der Lebenslauf, den du hier hochlädst." },
    "dateien.wie-es-ist": {
      sie: "Ihr PDF wird so verwendet, wie es ist. Ändern Sie es dort, wo Sie es erstellt haben, und laden Sie es neu hoch.",
      du: "Dein PDF wird so verwendet, wie es ist. Ändere es dort, wo du es erstellt hast, und lade es neu hoch.",
    },
    "dateien.gebaut": { sie: "Ohne eigenes PDF erstellt die App den Lebenslauf aus Ihren Angaben.", du: "Ohne eigenes PDF erstellt die App den Lebenslauf aus deinen Angaben." },
    "entwuerfe.intro": {
      sie: "Jedes Speichern legt eine Fassung an. Sie können jede ansehen, mit einer anderen vergleichen und zurückholen.",
      du: "Jedes Speichern legt eine Fassung an. Du kannst jede ansehen, mit einer anderen vergleichen und zurückholen.",
    },
    "inhalte.intro": {
      sie: "Hier sehen Sie, woraus die App Ihre Unterlagen baut, und können es direkt bearbeiten. Für das Übliche reichen Meine Angaben.",
      du: "Hier siehst du, woraus die App deine Unterlagen baut, und kannst es direkt bearbeiten. Für das Übliche reichen Meine Angaben.",
    },

    // Questions and settings (design check, #23)
    "fragen.hilfe": {
      sie: "Fragen Sie hier zur Stellensuche und zu Ihrer Bewerbung. Die KI kennt Ihre Angaben, nicht Ihre Liste der Bewerbungen, und sie ändert nichts. Das Gespräch bleibt nur auf dieser Seite. Prüfen Sie wichtige Antworten, auch eine KI irrt sich.",
      du: "Frag hier zur Stellensuche und zu deiner Bewerbung. Die KI kennt deine Angaben, nicht deine Liste der Bewerbungen, und sie ändert nichts. Das Gespräch bleibt nur auf dieser Seite. Prüfe wichtige Antworten, auch eine KI irrt sich.",
      lehrstelle: "Frag hier zur Lehrstellensuche und zu deiner Bewerbung. Die KI kennt deine Angaben, nicht deine Liste der Bewerbungen, und sie ändert nichts. Das Gespräch bleibt nur auf dieser Seite. Prüfe wichtige Antworten, auch eine KI irrt sich.",
    },
    "fragen.label": { sie: "Ihre Frage", du: "Deine Frage" },
    "fragen.sprecher": { sie: "Sie", du: "Du" },
    "suche.wo": { sie: "Wo suchen Sie?", du: "Wo suchst du?" },
    // Firmen with kununu (G35, #188, docs/design/firmen.md); „Firma“ stays neutral, apprenticeships say „Lehrbetrieb“
    "nav.firmen": { sie: "Firmen", du: "Firmen", lehrstelle: "Lehrbetriebe" },
    "suche.firmen": { sie: "Firmen ansehen", du: "Firmen ansehen", lehrstelle: "Lehrbetriebe ansehen" },
    "firmen.titel": { sie: "Firmen", du: "Firmen", lehrstelle: "Lehrbetriebe" },
    "firmen.alle": { sie: "Alle Firmen", du: "Alle Firmen", lehrstelle: "Alle Lehrbetriebe" },
    "firmen.zeile": {
      sie: "{anzahl} Firmen aus Treffern und Bewerbungen · {gefunden} bei kununu gefunden",
      du: "{anzahl} Firmen aus Treffern und Bewerbungen · {gefunden} bei kununu gefunden",
      lehrstelle: "{anzahl} Lehrbetriebe aus Treffern und Bewerbungen · {gefunden} bei kununu gefunden",
    },
    "firmen.nur-name": {
      sie: "Prüfen öffnet die Firma bei kununu in einem neuen Tab. Nur der Firmenname geht an kununu. Ihre Angaben bleiben auf diesem Computer.",
      du: "Prüfen öffnet die Firma bei kununu in einem neuen Tab. Nur der Firmenname geht an kununu. Deine Angaben bleiben auf diesem Computer.",
      lehrstelle: "Prüfen öffnet den Lehrbetrieb bei kununu in einem neuen Tab. Nur der Name des Lehrbetriebs geht an kununu. Deine Angaben bleiben auf diesem Computer.",
    },
    "firmen.spalte": { sie: "Firma", du: "Firma", lehrstelle: "Lehrbetrieb" },
    "firmen.suchen": { sie: "Firma suchen", du: "Firma suchen", lehrstelle: "Lehrbetrieb suchen" },
    "firmen.keine-passt": { sie: "Keine Firma passt zu dieser Suche.", du: "Keine Firma passt zu dieser Suche.", lehrstelle: "Kein Lehrbetrieb passt zu dieser Suche." },
    "firmen.mehrere": { sie: "Mehrere Firmen bei kununu", du: "Mehrere Firmen bei kununu", lehrstelle: "Mehrere Lehrbetriebe bei kununu" },
    "firmen.hilfe": {
      sie: "Auf kununu bewerten heutige und frühere Mitarbeitende ihre Firma: 5 ist der beste Wert, 1 der schlechteste. Unter 10 Bewertungen sagt der Wert wenig. Die Note der App sagt dagegen, wie gut eine Stelle zu Ihren Angaben passt.",
      du: "Auf kununu bewerten heutige und frühere Mitarbeitende ihre Firma: 5 ist der beste Wert, 1 der schlechteste. Unter 10 Bewertungen sagt der Wert wenig. Die Note der App sagt dagegen, wie gut eine Stelle zu deinen Angaben passt.",
      lehrstelle: "Auf kununu bewerten heutige und frühere Mitarbeitende und Lernende ihren Lehrbetrieb: 5 ist der beste Wert, 1 der schlechteste. Unter 10 Bewertungen sagt der Wert wenig. Die Note der App sagt dagegen, wie gut eine Lehrstelle zu deinen Angaben passt.",
    },
    "firmen.leer": {
      sie: "Noch keine Firmen. Die Liste füllt sich mit der Suche und mit Stellen, die Sie von Hand erfassen.",
      du: "Noch keine Firmen. Die Liste füllt sich mit der Suche und mit Stellen, die du von Hand erfasst.",
      lehrstelle: "Noch keine Lehrbetriebe. Die Liste füllt sich mit der Suche und mit Lehrstellen, die du von Hand erfasst.",
    },
    "firmen.dialog": { sie: "Welche kununu-Seite gehört zu {firma}?", du: "Welche kununu-Seite gehört zu {firma}?" },
    "firmen.dialog-feld": { sie: "Link zur Firma bei kununu", du: "Link zur Firma bei kununu", lehrstelle: "Link zum Lehrbetrieb bei kununu" },
    "firmen.dialog-hilfe": {
      sie: "Bei kununu die Firma öffnen und den Link aus der Adresszeile kopieren. kununu.com/ch und kununu.de gehen.",
      du: "Bei kununu die Firma öffnen und den Link aus der Adresszeile kopieren. kununu.com/ch und kununu.de gehen.",
      lehrstelle: "Bei kununu den Lehrbetrieb öffnen und den Link aus der Adresszeile kopieren. kununu.com/ch und kununu.de gehen.",
    },
    "firmen.dialog-fehler": {
      sie: "Das ist kein Link zu einer Firma bei kununu.", du: "Das ist kein Link zu einer Firma bei kununu.",
      lehrstelle: "Das ist kein Link zu einem Lehrbetrieb bei kununu.",
    },
    "einwilligung.ersetzt": {
      sie: "Bevor ein Text zur KI geht, ersetzt die App Ihre Angaben zu Name, Adresse, Telefon, E-Mail, Links und Geburtsdatum durch Platzhalter, ebenso Referenzen und Kontaktpersonen. Firmen, Ausbildungen und Jahreszahlen bleiben stehen. Ersetzen kann die App nur, was unter Meine Angaben richtig eingetragen ist.",
      du: "Bevor ein Text zur KI geht, ersetzt die App deine Angaben zu Name, Adresse, Telefon, E-Mail, Links und Geburtsdatum durch Platzhalter, ebenso Referenzen und Kontaktpersonen. Firmen, Ausbildungen und Jahreszahlen bleiben stehen. Ersetzen kann die App nur, was unter Meine Angaben richtig eingetragen ist.",
      lehrstelle: "Bevor ein Text zur KI geht, ersetzt die App deine Angaben zu Name, Adresse, Telefon, E-Mail, Links und Geburtsdatum sowie deine Schulen durch Platzhalter, ebenso Referenzen und Kontaktpersonen. Betriebe und Jahreszahlen bleiben stehen. Ersetzen kann die App nur, was unter Meine Angaben richtig eingetragen ist.",
    },
    // Why ictjobs is on or off (#107); the key ends in `grund` from /api/suche/liste
    "suche.ictjobs.aus": {
      sie: "Aus, weil keiner Ihrer Suchbegriffe nach Informatik klingt. Mit dem Häkchen einschalten.",
      du: "Aus, weil keiner deiner Suchbegriffe nach Informatik klingt. Mit dem Häkchen einschalten.",
    },
    "suche.ictjobs.passt": {
      sie: "An, weil Ihr Suchbegriff «{begriff}» nach Informatik klingt. Mit dem Häkchen ausschalten.",
      du: "An, weil dein Suchbegriff «{begriff}» nach Informatik klingt. Mit dem Häkchen ausschalten.",
    },
    "suche.ictjobs.gewaehlt": {
      sie: "Ihre Wahl. Mit dem Häkchen ändern; die App schaltet hier nichts mehr von selbst um.",
      du: "Deine Wahl. Mit dem Häkchen ändern; die App schaltet hier nichts mehr von selbst um.",
    },
    "suche.ictjobs.keine": {
      sie: "An, bis Suchbegriffe da sind. Mit dem Häkchen ausschalten.",
      du: "An, bis Suchbegriffe da sind. Mit dem Häkchen ausschalten.",
    },
    "einstellungen.einwilligung": {
      sie: "Ohne Einwilligung gehen keine Texte an die KI, auch nicht mit einem eigenen Schlüssel. Suche, Unterlagen und Versand funktionieren trotzdem. Mit dem Claude-Abo läuft die KI über Ihr eigenes Konto bei Anthropic; dafür gilt der Hinweis weiter unten.",
      du: "Ohne Einwilligung gehen keine Texte an die KI, auch nicht mit einem eigenen Schlüssel. Suche, Unterlagen und Versand funktionieren trotzdem. Mit dem Claude-Abo läuft die KI über dein eigenes Konto bei Anthropic; dafür gilt der Hinweis weiter unten.",
    },
    "einstellungen.eingewilligt": {
      sie: "Sie haben eingewilligt. Sie können das jederzeit widerrufen; danach gehen keine Texte mehr an die KI, bis Sie wieder einwilligen.",
      du: "Du hast eingewilligt. Du kannst das jederzeit widerrufen; danach gehen keine Texte mehr an die KI, bis du wieder einwilligst.",
    },
    "einstellungen.schluessel": {
      sie: "Sie brauchen das nicht, die App läuft auch ohne. Mit einem eigenen Schlüssel von Anthropic gehen die KI-Aufrufe direkt an die Claude API statt über die Vermittlung. Namen und andere persönliche Angaben werden auch dann vor dem Senden ersetzt.",
      du: "Du brauchst das nicht, die App läuft auch ohne. Mit einem eigenen Schlüssel von Anthropic gehen die KI-Aufrufe direkt an die Claude API statt über die Vermittlung. Namen und andere persönliche Angaben werden auch dann vor dem Senden ersetzt.",
    },
    "einstellungen.seiten-adressen": {
      sie: "Die Suche läuft dann auch auf diesen Seiten, sobald Sie sie starten. Tragen Sie die Adresse so ein, wie sie im Browser steht, eine pro Zeile,",
      du: "Die Suche läuft dann auch auf diesen Seiten, sobald du sie startest. Trag die Adresse so ein, wie sie im Browser steht, eine pro Zeile,",
    },
    "einstellungen.seiten-suche": {
      sie: "Hat die Seite ein Suchfeld, sucht die App dort mit den Begriffen aus Ihrem Suchprofil. Sonst liest sie die Stellen, die auf der Seite stehen, zum Beispiel die offenen Stellen einer Firma. Die KI liest die Stellen aus dem Text der Seite.",
      du: "Hat die Seite ein Suchfeld, sucht die App dort mit den Begriffen aus deinem Suchprofil. Sonst liest sie die Stellen, die auf der Seite stehen, zum Beispiel die offenen Stellen einer Firma. Die KI liest die Stellen aus dem Text der Seite.",
    },
    "einstellungen.seiten-grenzen": {
      sie: "Pro Seite höchstens zehn Suchen und dreissig Inserate pro Lauf, mit Pausen dazwischen. Nur Links auf dieselbe Seite werden übernommen. Anmeldungen und CAPTCHAs bleiben bei Ihnen: Verlangt eine Seite das, überspringt die Suche sie. LinkedIn verbietet Automatisierung und kann Konten einschränken oder sperren.",
      du: "Pro Seite höchstens zehn Suchen und dreissig Inserate pro Lauf, mit Pausen dazwischen. Nur Links auf dieselbe Seite werden übernommen. Anmeldungen und CAPTCHAs bleiben bei dir: Verlangt eine Seite das, überspringt die Suche sie. LinkedIn verbietet Automatisierung und kann Konten einschränken oder sperren.",
    },
    "einstellungen.vor-schluessel": {
      sie: "Bevor Sie einen Schlüssel eintragen:",
      du: "Bevor du einen Schlüssel einträgst:",
    },
    "einstellungen.kosten-selbst": {
      sie: "Sie tragen die Kosten selbst. Anthropic rechnet direkt mit Ihnen ab.",
      du: "Du trägst die Kosten selbst. Anthropic rechnet direkt mit dir ab.",
    },
    "einstellungen.linkedin": {
      sie: "LinkedIn verbietet Automatisierung und kann Konten einschränken oder sperren. Das Risiko liegt bei Ihnen, wenn Sie LinkedIn als weitere Seite durchsuchen lassen.",
      du: "LinkedIn verbietet Automatisierung und kann Konten einschränken oder sperren. Das Risiko liegt bei dir, wenn du LinkedIn als weitere Seite durchsuchen lässt.",
    },
    "einstellungen.vertrag": {
      sie: "Für die Verarbeitung gilt Ihr eigener Vertrag mit Anthropic, auch in den USA.",
      du: "Für die Verarbeitung gilt dein eigener Vertrag mit Anthropic, auch in den USA.",
    },
    "einstellungen.abo": {
      sie: "Haben Sie ein Abo bei Anthropic, dann kann Claude selbst suchen, bewerten und Anschreiben entwerfen und das Ergebnis hier in die App schreiben. Die KI-Knöpfe der App laufen damit nicht, denn Anthropic erlaubt nicht, ein Abo in anderen Apps zu nutzen.",
      du: "Hast du ein Abo bei Anthropic, dann kann Claude selbst suchen, bewerten und Anschreiben entwerfen und das Ergebnis hier in die App schreiben. Die KI-Knöpfe der App laufen damit nicht, denn Anthropic erlaubt nicht, ein Abo in anderen Apps zu nutzen.",
    },
    "einstellungen.abo-klartext": {
      sie: "Claude liest Ihre Angaben im Klartext: Lebenslauf, Suchprofil, Bausteine und Bewerbungen. Die Pseudonymisierung der App gilt auf diesem Weg nicht.",
      du: "Claude liest deine Angaben im Klartext: Lebenslauf, Suchprofil, Bausteine und Bewerbungen. Die Pseudonymisierung der App gilt auf diesem Weg nicht.",
    },
    "einstellungen.abo-vertrag": {
      sie: "Für die Verarbeitung gilt Ihr eigener Vertrag mit Anthropic, auch in den USA. Ob Ihre Chats zum Training dienen, stellen Sie in Claude ein.",
      du: "Für die Verarbeitung gilt dein eigener Vertrag mit Anthropic, auch in den USA. Ob deine Chats zum Training dienen, stellst du in Claude ein.",
    },
    "einstellungen.abo-versand": {
      sie: "Abschicken, „Versand erfassen“ und alles zum RAV bleiben bei Ihnen. Dafür gibt es keinen Zugang.",
      du: "Abschicken, „Versand erfassen“ und alles zum RAV bleiben bei dir. Dafür gibt es keinen Zugang.",
    },

    // Search (step 5)
    "suche.wie": {
      sie: "Die Erweiterung sucht in Ihrem Browser und nur, wenn Sie die Suche starten. Die KI schätzt jeden neuen Treffer als Note von 1 bis 6 ein.",
      du: "Die Erweiterung sucht in deinem Browser und nur, wenn du die Suche startest. Die KI schätzt jeden neuen Treffer als Note von 1 bis 6 ein.",
    },
    // #220: „Ihre Bewerbungen“ instead of „Register“
    "suche.schon-titel": { sie: "Schon in Ihren Bewerbungen", du: "Schon in deinen Bewerbungen" },
    "suche.schon-marke": { sie: "schon in Ihren Bewerbungen", du: "schon in deinen Bewerbungen" },
    "suche.sichtbar": { sie: "Langsamer, dafür sehen Sie, was die Erweiterung tut.", du: "Langsamer, dafür siehst du, was die Erweiterung tut." },
    "suche.laufnotiz": {
      sie: "Ein Suchlauf dauert einige Minuten. Sie können währenddessen weiterarbeiten.",
      du: "Ein Suchlauf dauert einige Minuten. Du kannst währenddessen weiterarbeiten.",
    },
    "suche.keine": {
      sie: "Die Portale haben nichts Neues gemeldet. Versuchen Sie weitere Suchbegriffe oder eine grössere Umgebung.",
      du: "Die Portale haben nichts Neues gemeldet. Versuche weitere Suchbegriffe oder eine grössere Umgebung.",
      lehrstelle: "Die Portale haben nichts Neues gemeldet. Nimm weitere Berufe dazu oder suche in einer grösseren Umgebung.",
    },
    "suche.notenhilfe-titel": { sie: "Wie lese ich die Note?", du: "Wie lese ich die Note?", lehrstelle: "Wie lese ich die Noten?" },
    "suche.notenhilfe": {
      sie: "Schweizer Noten: 6 ist die beste, 1 die schlechteste Note, halbe Noten sind möglich. Ab 4 passt die Stelle genügend. Die Note ist eine Einschätzung der KI und kann falsch sein.",
      du: "Schweizer Noten: 6 ist die beste, 1 die schlechteste Note, halbe Noten sind möglich. Ab 4 passt die Stelle genügend. Die Note ist eine Einschätzung der KI und kann falsch sein.",
      lehrstelle: "Schweizer Noten: 6 ist die beste, 1 die schlechteste Note. Die Note «Beruf» sagt, wie gut der Beruf zu dir passt, die Note «Lehrstelle», wie gut dieser Lehrbetrieb passt. Ab 4 passt es genügend. Die KI kann sich irren.",
    },
    "suche.angaben-offen": {
      sie: "In «Meine Angaben» gibt es Änderungen, die noch nicht übernommen sind. Die Suche nimmt noch die bisherigen Angaben.",
      du: "In «Meine Angaben» hast du Änderungen, die noch nicht übernommen sind. Die Suche nimmt noch die bisherigen Angaben.",
    },

    // Application page (step 4)
    "bewerbung.angaben": { sie: "Angaben zur Stelle", du: "Angaben zur Stelle", lehrstelle: "Angaben zur Lehrstelle" },
    "bewerbung.stellentext": { sie: "Stellentext", du: "Stellentext", lehrstelle: "Inseratstext" },
    "bewerbung.gespraech": { sie: "Gespräch vorbereiten", du: "Gespräch vorbereiten", lehrstelle: "Einladung vorbereiten" },
    "bewerbung.feld-firma": { sie: "Firma", du: "Firma", lehrstelle: "Lehrbetrieb" },
    "bewerbung.feld-stelle": { sie: "Stelle", du: "Stelle", lehrstelle: "Lehrstelle" },
    "bewerbung.inserat": {
      sie: "Ohne den Text des Inserats können Variante, Anschreiben und Prüfung nicht darauf eingehen. Kopieren Sie ihn aus dem Inserat in das Feld.",
      du: "Ohne den Text des Inserats können Variante, Anschreiben und Prüfung nicht darauf eingehen. Kopiere ihn aus dem Inserat in das Feld.",
    },
    "bewerbung.eigenes": {
      sie: "Die KI ist nicht eingerichtet. Laden Sie ein eigenes Anschreiben als PDF hoch. Alles andere funktioniert auch ohne KI.",
      du: "Die KI ist nicht eingerichtet. Lade ein eigenes Anschreiben als PDF hoch. Alles andere funktioniert auch ohne KI.",
    },
    "bewerbung.formular": {
      sie: "Die App öffnet das Formular der Firma in einem neuen Tab. Die Erweiterung füllt aus, was sie weiss, und markiert, was offen ist. Sie prüfen und schicken selbst ab.",
      du: "Die App öffnet das Formular der Firma in einem neuen Tab. Die Erweiterung füllt aus, was sie weiss, und markiert, was offen ist. Du prüfst und schickst selbst ab.",
      lehrstelle: "Die App öffnet das Formular des Lehrbetriebs in einem neuen Tab. Die Erweiterung füllt aus, was sie weiss, und markiert, was offen ist. Du prüfst und schickst selbst ab.",
    },
    "bewerbung.versand": {
      sie: "Es gibt keinen Link zu einem Formular. Schicken Sie die Unterlagen selbst ab, etwa per E-Mail, und erfassen Sie danach den Versand.",
      du: "Es gibt keinen Link zu einem Formular. Schick die Unterlagen selbst ab, etwa per E-Mail, und erfasse danach den Versand.",
    },
    "bewerbung.jobroom": {
      sie: "Die Erweiterung füllt den Eintrag im Job-Room aus. Speichern und anmelden machen Sie selbst. Oder kopieren Sie die Angaben einzeln.",
      du: "Die Erweiterung füllt den Eintrag im Job-Room aus. Speichern und anmelden machst du selbst. Oder kopiere die Angaben einzeln.",
    },
    "bewerbung.warten": {
      sie: "Ohne Antwort erinnert Sie die Übersicht am {datum} ans Nachfragen.",
      du: "Ohne Antwort erinnert dich die Übersicht am {datum} ans Nachfragen.",
    },
    "bewerbung.absage": {
      sie: "Das gehört dazu. Ihre Unterlagen für diese Stelle bleiben gespeichert.",
      du: "Das gehört dazu. Deine Unterlagen für diese Stelle bleiben gespeichert.",
      lehrstelle: "Das gehört dazu. Deine Unterlagen für diese Lehrstelle bleiben gespeichert.",
    },
    "bewerbung.freigeben": {
      sie: "Der Entwurf ist fertig. Lesen Sie ihn, bevor er an die Firma geht. Erst mit der Freigabe öffnet die Erweiterung das Formular.",
      du: "Der Entwurf ist fertig. Lies ihn, bevor er an die Firma geht. Erst mit der Freigabe öffnet die Erweiterung das Formular.",
      lehrstelle: "Der Entwurf ist fertig. Lies ihn, bevor er an den Lehrbetrieb geht. Erst mit der Freigabe öffnet die Erweiterung das Formular.",
    },
    "bewerbung.freigeben-offen": {
      sie: "Der Entwurf ist fertig. {aussagen} noch keinen Beleg in Ihren Angaben; gelb markiert.",
      du: "Der Entwurf ist fertig. {aussagen} noch keinen Beleg in deinen Angaben; gelb markiert.",
    },
    "bewerbung.geoeffnet": {
      sie: "Das Formular ist in einem neuen Tab offen. Abgeschickt wird erst durch Sie.",
      du: "Das Formular ist in einem neuen Tab offen. Abgeschickt wird erst durch dich.",
    },
    "bewerbung.jobroom-offen": {
      sie: "Der Job-Room ist offen. Gespeichert wird erst durch Sie.", du: "Der Job-Room ist offen. Gespeichert wird erst durch dich.",
    },

    // Overview (step 3)
    "uebersicht.von-hand": { sie: "Stelle von Hand erfassen", du: "Stelle von Hand erfassen", lehrstelle: "Lehrstelle von Hand erfassen" },
    "uebersicht.feld-firma": { sie: "Firma", du: "Firma", lehrstelle: "Lehrbetrieb" },
    "uebersicht.feld-stelle": { sie: "Stelle", du: "Stelle", lehrstelle: "Lehrstelle" },
    "uebersicht.suche": { sie: "Firma oder Stelle", du: "Firma oder Stelle", lehrstelle: "Lehrbetrieb oder Lehrstelle" },
    "uebersicht.spalte": { sie: "Stelle und Firma", du: "Stelle und Firma", lehrstelle: "Lehrstelle und Lehrbetrieb" },
    "uebersicht.liste-leer": {
      sie: "Noch keine Bewerbungen. Klicken Sie in der Suche bei einer Stelle auf «Merken» oder erfassen Sie eine von Hand.",
      du: "Noch keine Bewerbungen. Klicke in der Suche bei einer Stelle auf «Merken» oder erfasse eine von Hand.",
      lehrstelle: "Noch keine Bewerbungen. Klicke in der Suche bei einer Lehrstelle auf «Merken» oder erfasse eine von Hand.",
    },
    "uebersicht.leer.titel": { sie: "Erste Stellen suchen", du: "Erste Stellen suchen", lehrstelle: "Erste Lehrstellen suchen" },
    "uebersicht.leer.text": {
      sie: "Ihre Angaben sind übernommen. Die Erweiterung sucht jetzt auf den Portalen, die KI schätzt jeden Treffer ein. Ein Suchlauf dauert einige Minuten.",
      du: "Deine Angaben sind übernommen. Die Erweiterung sucht jetzt auf den Portalen, die KI schätzt jeden Treffer ein. Ein Suchlauf dauert einige Minuten.",
    },
    "uebersicht.start.text": {
      sie: "Die App hilft Ihnen, passende Stellen zu finden und Unterlagen vorzubereiten. Abschicken und entscheiden bleibt immer bei Ihnen.",
      du: "Die App hilft dir, passende Stellen zu finden und Unterlagen vorzubereiten. Abschicken und entscheiden bleibt immer bei dir.",
      lehrstelle: "Die App hilft dir, passende Lehrstellen und Schnupperlehren zu finden und deine Unterlagen vorzubereiten. Abschicken und entscheiden bleibt immer bei dir.",
    },
    "uebersicht.start.karte": {
      sie: "Ihr Werdegang, was Sie suchen und wie Sie schreiben. Sie können jederzeit unterbrechen, nichts geht verloren.",
      du: "Dein Werdegang, was du suchst und wie du schreibst. Du kannst jederzeit unterbrechen, nichts geht verloren.",
      lehrstelle: "Deine Schule, welche Berufe du suchst und wie du schreibst. Du kannst jederzeit unterbrechen, nichts geht verloren.",
    },
    "uebersicht.karte.abschicken": {
      sie: "Die Unterlagen sind bereit. Die Erweiterung öffnet das Formular und füllt es aus. Abschicken machen Sie selbst.",
      du: "Die Unterlagen sind bereit. Die Erweiterung öffnet das Formular und füllt es aus. Abschicken machst du selbst.",
    },
    "uebersicht.karte.abschicken-alle": {
      sie: "Die Unterlagen sind bereit. Die Erweiterung öffnet pro Bewerbung einen Tab und füllt das Formular aus. Abschicken machen Sie selbst.",
      du: "Die Unterlagen sind bereit. Die Erweiterung öffnet pro Bewerbung einen Tab und füllt das Formular aus. Abschicken machst du selbst.",
    },
    "uebersicht.karte.rav": {
      sie: "Beworben, aber noch nicht als Arbeitsbemühung eingetragen. Die Erweiterung füllt den Job-Room aus; anmelden und speichern machen Sie selbst.",
      du: "Beworben, aber noch nicht als Arbeitsbemühung eingetragen. Die Erweiterung füllt den Job-Room aus; anmelden und speichern machst du selbst.",
    },
    "uebersicht.karte.unterlagen": {
      sie: "Für diese Stelle fehlt noch der Lebenslauf als PDF. In der Bewerbung lassen sich Lebenslauf und Anschreiben erstellen.",
      du: "Für diese Stelle fehlt noch der Lebenslauf als PDF. In der Bewerbung lassen sich Lebenslauf und Anschreiben erstellen.",
      lehrstelle: "Für diese Lehrstelle fehlt noch der Lebenslauf als PDF. In der Bewerbung lassen sich Lebenslauf und Anschreiben erstellen.",
    },
    "uebersicht.karte.freigeben": {
      sie: "Der Entwurf ist fertig. Lesen Sie ihn, bevor er an die Firma geht. Erst mit der Freigabe öffnet die Erweiterung das Formular.",
      du: "Der Entwurf ist fertig. Lies ihn, bevor er an die Firma geht. Erst mit der Freigabe öffnet die Erweiterung das Formular.",
      lehrstelle: "Der Entwurf ist fertig. Lies ihn, bevor er an den Lehrbetrieb geht. Erst mit der Freigabe öffnet die Erweiterung das Formular.",
    },
    "uebersicht.geoeffnet": {
      sie: "{anzahl} Tab(s) geöffnet. Abgeschickt wird erst durch Sie.", du: "{anzahl} Tab(s) geöffnet. Abgeschickt wird erst durch dich.",
    },
    "uebersicht.jobroom-offen": {
      sie: "Der Job-Room ist offen, {anzahl} Einträge warten. Gespeichert wird erst durch Sie.",
      du: "Der Job-Room ist offen, {anzahl} Einträge warten. Gespeichert wird erst durch dich.",
    },
    "uebersicht.doppelt": {
      sie: "Möchten Sie das Formular trotzdem öffnen?", du: "Möchtest du das Formular trotzdem öffnen?",
    },

    // Heute and the first start (#260, A1 and A2)
    "heute.wartet.nichts": { sie: "Gerade wartet nichts auf Sie.", du: "Gerade wartet nichts auf dich." },
    "heute.wartet.eins": { sie: "Eine Sache wartet auf Sie.", du: "Eine Sache wartet auf dich." },
    "heute.wartet.viele": { sie: "{anzahl} Dinge warten auf Sie, das wichtigste zuoberst.", du: "{anzahl} Dinge warten auf dich, das wichtigste zuoberst." },
    "heute.stand": { sie: "Ihr Stand", du: "Dein Stand" },
    "heute.stand.neu": { sie: "Neue Stellen", du: "Neue Stellen", lehrstelle: "Neue Lehrstellen" },
    "heute.durchgang.unter": {
      sie: "{anzahl} gemerkte Stellen · bewerben oder verwerfen, eine nach der anderen",
      du: "{anzahl} gemerkte Stellen · bewerben oder verwerfen, eine nach der anderen",
      lehrstelle: "{anzahl} gemerkte Lehrstellen · bewerben oder verwerfen, eine nach der anderen",
    },
    "heute.rav": {
      sie: "Noch nicht im Job-Room eingetragen: {anzahl} vom {monat}. Das RAV erhält die Einträge bis zum {frist}.",
      du: "Noch nicht im Job-Room eingetragen: {anzahl} vom {monat}. Das RAV erhält die Einträge bis zum {frist}.",
    },
    "heute.weg": { sie: "Ihr Weg zur ersten Bewerbung", du: "Dein Weg zur ersten Bewerbung" },
    "heute.start.einrichtung": {
      sie: "Den Zugang zur KI und die Erweiterung im Browser richten Sie in der Einrichtung ein.",
      du: "Den Zugang zur KI und die Erweiterung im Browser richtest du in der Einrichtung ein.",
    },
    "heute.start.suchen": {
      sie: "Die Erweiterung sucht auf den Portalen. Zu jeder Stelle sehen Sie eine Einschätzung.",
      du: "Die Erweiterung sucht auf den Portalen. Zu jeder Stelle siehst du eine Einschätzung.",
      lehrstelle: "Die Erweiterung sucht auf den Portalen. Zu jeder Lehrstelle siehst du eine Einschätzung.",
    },
    "heute.start.bewerbung": {
      sie: "Lebenslauf und Anschreiben für die Stelle. Abschicken machen Sie selbst, das Formular ist vorausgefüllt.",
      du: "Lebenslauf und Anschreiben für die Stelle. Abschicken machst du selbst, das Formular ist vorausgefüllt.",
      lehrstelle: "Lebenslauf und Anschreiben für die Lehrstelle. Abschicken machst du selbst, das Formular ist vorausgefüllt.",
    },
    "heute.wissen.computer": { sie: "Ihre Angaben bleiben auf diesem Computer.", du: "Deine Angaben bleiben auf diesem Computer." },
    "heute.wissen.entscheiden": { sie: "Die KI schlägt vor, Sie entscheiden.", du: "Die KI schlägt vor, du entscheidest." },
    "heute.wissen.weg": { sie: "Jede Bewerbung schicken Sie selbst ab.", du: "Jede Bewerbung schickst du selbst ab." },

    // Setup (step 2 of the redesign)
    "einrichtung.ordner.frage": {
      sie: "Wo sollen Ihre Unterlagen liegen?",
      du: "Wo sollen deine Unterlagen liegen?",
    },
    "einrichtung.ordner.zeile": { sie: "Ihre Unterlagen liegen in:", du: "Deine Unterlagen liegen in:" },
    "einrichtung.ordner.text": {
      sie: "In diesem Ordner speichert die App Lebenslauf, Anschreiben, Entwürfe und versendete Fassungen. Er bleibt auf Ihrem Computer.",
      du: "In diesem Ordner speichert die App Lebenslauf, Anschreiben, Entwürfe und versendete Fassungen. Er bleibt auf deinem Computer.",
    },
    "einrichtung.vorlage.ohne": {
      sie: "Ohne diese Datei überspringen Sie den Schritt und erfassen Ihre Angaben danach unter Meine Angaben, auch aus Unterlagen wie PDF oder Word.",
      du: "Ohne diese Datei überspringst du den Schritt und erfasst deine Angaben danach unter Meine Angaben, auch aus Unterlagen wie PDF oder Word.",
    },
    "einrichtung.vorlage.unvollstaendig": {
      sie: "Einige Angaben fehlen noch; sie werden mit Ihrer Begleitperson aus den Dokumenten ergänzt.",
      du: "Einige Angaben fehlen noch; sie werden mit deiner Begleitperson aus den Dokumenten ergänzt.",
    },
    "einrichtung.ki.aufgabe": {
      sie: "Die KI schätzt Stellen ein und entwirft Anschreiben.",
      du: "Die KI schätzt Stellen ein und entwirft Anschreiben.",
      lehrstelle: "Die KI schätzt Lehrstellen ein und entwirft Anschreiben.",
    },
    "einrichtung.ki.code": {
      sie: "Sie haben von Ihrer Begleitperson einen Einladungscode erhalten.",
      du: "Du hast von deiner Begleitperson einen Einladungscode erhalten.",
    },
    "einrichtung.ki.ohne": {
      sie: "Ohne KI funktionieren Suche, Unterlagen und Versand trotzdem. Anschreiben laden Sie dann selbst hoch, und Treffer bekommen keine Note.",
      du: "Ohne KI funktionieren Suche, Unterlagen und Versand trotzdem. Anschreiben lädst du dann selbst hoch, und Treffer bekommen keine Note.",
    },
    "einrichtung.ki.selbst": {
      sie: "Mit einem eigenen Schlüssel von Anthropic oder Ihrem Claude-Abo zahlen Sie die Kosten selbst:",
      du: "Mit einem eigenen Schlüssel von Anthropic oder deinem Claude-Abo zahlst du die Kosten selbst:",
    },
  };

  function satzOder(satz) {
    return SAETZE.includes(satz) ? satz : VORGABE;
  }

  /** The text of a key in a set, with {name} filled from `werte`. An unknown key is a programming error. */
  function text(schluessel, satz, werte = {}) {
    const eintrag = TEXTE[schluessel];
    if (!eintrag) throw new Error(`Unbekannter Text: ${schluessel}`);
    const gewaehlt = satzOder(satz);
    const roh = gewaehlt === "lehrstelle-du" ? (eintrag.lehrstelle ?? eintrag.du)
      : gewaehlt === "stelle-du" ? eintrag.du : eintrag.sie;
    return roh.replace(/\{(\w+)\}/g, (_, name) => String(werte[name] ?? ""));
  }

  /** Fill every element with data-text below `wurzel` (textContent only, never HTML). */
  function anwenden(wurzel, satz) {
    for (const element of wurzel.querySelectorAll("[data-text]")) element.textContent = text(element.dataset.text, satz);
  }

  /** The name of a status as the person reads it: for apprenticeships an interview is often a trial apprenticeship. */
  function statusName(status, satz) {
    return satzOder(satz) === "lehrstelle-du" && status === "Gespräch" ? "Einladung" : status;
  }

  // A decimal point, as the design system says (4.5, never 4,5; abgleich #1).
  const notenText = note => String(note);

  const texte = { SAETZE, VORGABE, TEXTE, satzOder, text, anwenden, statusName, notenText };
  if (typeof module !== "undefined") module.exports = texte;
  else global.Texte = texte;
})(typeof window !== "undefined" ? window : globalThis);
