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
    "dateien.cv-titel": { sie: "Ihr Lebenslauf", du: "Dein Lebenslauf" },
    "dateien.app": { sie: "Aus Ihren Angaben, für jede Stelle passend gewichtet. Empfohlen.", du: "Aus deinen Angaben, für jede Stelle passend gewichtet. Empfohlen." },
    "dateien.eigen": { sie: "Es geht unverändert an jede Firma. Ändern können Sie es nur ausserhalb der App.", du: "Es geht unverändert an jede Firma. Ändern kannst du es nur ausserhalb der App." },
    "dateien.app-wie": { sie: "Aus Meine Angaben. Für jede Stelle passen Sie ihn in der Bewerbung an.", du: "Aus Meine Angaben. Für jede Stelle passt du ihn in der Bewerbung an." },
    "dateien.ihr-pdf": { sie: "Ihr PDF", du: "Dein PDF" },
    "dateien.wie-es-ist": {
      sie: "Ihr PDF wird so verwendet, wie es ist. Ändern Sie es dort, wo Sie es erstellt haben, und laden Sie es neu hoch.",
      du: "Dein PDF wird so verwendet, wie es ist. Ändere es dort, wo du es erstellt hast, und lade es neu hoch.",
    },
    "dateien.ordnet": { sie: "PDF, JPG oder PNG. Die App ordnet sie selbst ein, Sie können das ändern.", du: "PDF, JPG oder PNG. Die App ordnet sie selbst ein, du kannst das ändern." },
    "dateien.zurueck-zur-app": {
      sie: "Danach erstellt die App Ihren Lebenslauf aus Ihren Angaben. Das PDF lässt sich unter Frühere Fassungen zurückholen.",
      du: "Danach erstellt die App deinen Lebenslauf aus deinen Angaben. Das PDF lässt sich unter Frühere Fassungen zurückholen.",
    },
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
    // Suche einstellen (#263, A4): the cards
    "einstellen.was": { sie: "Welche Stellen passen zu Ihnen?", du: "Welche Stellen passen zu dir?", lehrstelle: "Welche Lehrstellen passen zu dir?" },
    "einstellen.nicht": { sie: "Was Sie nicht sehen wollen", du: "Was du nicht sehen willst" },
    // How a title filter term matches (G104, #382): in the Titelfilter form and under «Im Titel»; jobs only
    "einstellen.titel-regel": {
      sie: "Ein Begriff passt auch als Anfang oder Ende eines Worts: „Software“ passt zu „Softwareentwickler“, „Bildung“ zu „Erwachsenenbildung“. Soll er nur als ganzes Wort passen, schreiben Sie „(ganzes Wort)“ dahinter, etwa „Sales (ganzes Wort)“. Begriffe mit höchstens drei Buchstaben wie „KI“ passen immer nur als ganzes Wort.",
      du: "Ein Begriff passt auch als Anfang oder Ende eines Worts: „Software“ passt zu „Softwareentwickler“, „Bildung“ zu „Erwachsenenbildung“. Soll er nur als ganzes Wort passen, schreib „(ganzes Wort)“ dahinter, etwa „Sales (ganzes Wort)“. Begriffe mit höchstens drei Buchstaben wie „KI“ passen immer nur als ganzes Wort.",
    },
    // The Titelfilter form has two lists; the rule under the second holds for both (UI/UX ruling on #382).
    "einstellen.titelfilter-regel": {
      sie: "Für beide Listen gilt: Ein Begriff passt auch als Anfang oder Ende eines Worts: „Software“ passt zu „Softwareentwickler“, „Bildung“ zu „Erwachsenenbildung“. Soll er nur als ganzes Wort passen, schreiben Sie „(ganzes Wort)“ dahinter, etwa „Sales (ganzes Wort)“. Begriffe mit höchstens drei Buchstaben wie „KI“ passen immer nur als ganzes Wort.",
      du: "Für beide Listen gilt: Ein Begriff passt auch als Anfang oder Ende eines Worts: „Software“ passt zu „Softwareentwickler“, „Bildung“ zu „Erwachsenenbildung“. Soll er nur als ganzes Wort passen, schreib „(ganzes Wort)“ dahinter, etwa „Sales (ganzes Wort)“. Begriffe mit höchstens drei Buchstaben wie „KI“ passen immer nur als ganzes Wort.",
    },
    "einstellen.verworfen": {
      sie: "Aus den Stellen, die Sie verworfen haben: {anzahl} haben «{wort}» im Titel.",
      du: "Aus den Stellen, die du verworfen hast: {anzahl} haben «{wort}» im Titel.",
    },
    // Exclusion reasons from dismissed hits by the AI (#319, G86); jobs only
    "einstellen.ki-ausschluesse": {
      sie: "Die KI sucht in den {anzahl} verworfenen Stellen, die das Suchprofil noch nicht ausschliesst, nach gemeinsamen Gründen, etwa Pensum, Branche, Arbeitsort oder Wörter im Titel. Ins Suchprofil kommt nur, was Sie übernehmen.",
      du: "Die KI sucht in den {anzahl} verworfenen Stellen, die das Suchprofil noch nicht ausschliesst, nach gemeinsamen Gründen, etwa Pensum, Branche, Arbeitsort oder Wörter im Titel. Ins Suchprofil kommt nur, was du übernimmst.",
    },
    "einstellen.ki-ausschluesse-rest": {
      sie: "Die Vorschläge unten können Sie weiter übernehmen oder zurücknehmen. Neue gibt es wieder ab {mindestens} verworfenen Stellen, die das Suchprofil noch nicht ausschliesst.",
      du: "Die Vorschläge unten kannst du weiter übernehmen oder zurücknehmen. Neue gibt es wieder ab {mindestens} verworfenen Stellen, die das Suchprofil noch nicht ausschliesst.",
    },
    "einstellen.ki-ausschluesse-was": {
      sie: "Nur Titel, Firma, Ort und Pensum der verworfenen Stellen. Kein Lebenslauf, kein Suchprofil, nichts über Sie.",
      du: "Nur Titel, Firma, Ort und Pensum der verworfenen Stellen. Kein Lebenslauf, kein Suchprofil, nichts über dich.",
    },
    "einstellen.ki-ausschluesse-leer": {
      sie: "Ab {mindestens} verworfenen Stellen kann die KI hier vorschlagen, was Sie künftig nicht mehr sehen wollen.",
      du: "Ab {mindestens} verworfenen Stellen kann die KI hier vorschlagen, was du künftig nicht mehr sehen willst.",
    },
    "einstellen.ki-ausschluesse-fertig": {
      sie: "Am Suchprofil ändert sich erst etwas, wenn Sie {welchen} übernehmen.",
      du: "Am Suchprofil ändert sich erst etwas, wenn du {welchen} übernimmst.",
    },
    "einstellen.ohne-schluessel": {
      sie: "Weitere Seiten wie die offenen Stellen einer Firma durchsucht die App mit einem eigenen API-Schlüssel. Den tragen Sie in den Einstellungen ein.",
      du: "Weitere Seiten wie die offenen Stellen einer Firma durchsucht die App mit einem eigenen API-Schlüssel. Den trägst du in den Einstellungen ein.",
    },
    // Stellen (#262, A3): the decision per hit (G58) and the own stars under the AI (G22)
    "suche.entscheiden": { sie: "Was möchten Sie mit dieser Stelle tun?", du: "Was möchtest du mit dieser Stelle tun?", lehrstelle: "Was möchtest du mit dieser Lehrstelle tun?" },
    "suche.eigene": { sie: "Ihre eigene Bewertung", du: "Deine eigene Bewertung" },
    // #374: the caption of the tab «In Bewerbungen»
    "suche.in-bewerbungen": {
      sie: "Treffer aus der Suche, die Sie gemerkt oder vorbereitet haben, mit ihrem Stand unter Bewerbungen.",
      du: "Treffer aus der Suche, die du gemerkt oder vorbereitet hast, mit ihrem Stand unter Bewerbungen.",
    },
    "suche.eigene-hinweis": { sie: "Ihr Urteil, getrennt von der Note der KI. Geht nicht an die KI.", du: "Dein Urteil, getrennt von der Note der KI. Geht nicht an die KI." },
    // Firmen with kununu (G35, #188, docs/design/firmen.md); „Firma“ stays neutral, apprenticeships say „Lehrbetrieb“
    "nav.firmen": { sie: "Firmen", du: "Firmen", lehrstelle: "Lehrbetriebe" },
    "firmen.titel": { sie: "Firmen", du: "Firmen", lehrstelle: "Lehrbetriebe" },
    // Excluded companies (#226, G65): the same words from a hit, from Firmen and from an application (#303)
    "firmen.ausschliessen": { sie: "Diese Firma nicht mehr zeigen", du: "Diese Firma nicht mehr zeigen", lehrstelle: "Diesen Lehrbetrieb nicht mehr zeigen" },
    "firmen.wieder-zeigen": { sie: "Diese Firma wieder zeigen", du: "Diese Firma wieder zeigen", lehrstelle: "Diesen Lehrbetrieb wieder zeigen" },
    "firmen.wieder-gezeigt": {
      sie: "Inserate von {firma} zeigt die Suche wieder.",
      du: "Inserate von {firma} zeigt die Suche wieder.",
      lehrstelle: "Lehrstellen von {firma} zeigt die Suche wieder.",
    },
    "firmen.nicht-geaendert": {
      sie: "Die Suche zeigt die Inserate von {firma} wie vorher.",
      du: "Die Suche zeigt die Inserate von {firma} wie vorher.",
      lehrstelle: "Die Suche zeigt die Lehrstellen von {firma} wie vorher.",
    },
    "firmen.ausgeschlossen": {
      sie: "Inserate von {firma} zeigt die Suche nicht mehr. Unter Suche einstellen können Sie die Firma wieder zeigen.",
      du: "Inserate von {firma} zeigt die Suche nicht mehr. Unter Suche einstellen kannst du die Firma wieder zeigen.",
      lehrstelle: "Lehrstellen von {firma} zeigt die Suche nicht mehr. Unter Suche einstellen kannst du den Lehrbetrieb wieder zeigen.",
    },
    "firmen.liste-hinweis": {
      sie: "Inserate dieser Firmen zeigt die Suche nicht mehr. Mit oder ohne AG oder GmbH, gross oder klein: Die App erkennt die Firma.",
      du: "Inserate dieser Firmen zeigt die Suche nicht mehr. Mit oder ohne AG oder GmbH, gross oder klein: Die App erkennt die Firma.",
      lehrstelle: "Lehrstellen dieser Lehrbetriebe zeigt die Suche nicht mehr. Mit oder ohne AG oder GmbH, gross oder klein: Die App erkennt den Lehrbetrieb.",
    },
    "firmen.alle": { sie: "Alle Firmen", du: "Alle Firmen", lehrstelle: "Alle Lehrbetriebe" },
    // the first two parts of the «·» line under the title on Firmen (#342)
    "firmen.zeile": {
      sie: "{anzahl} Firmen aus Treffern und Bewerbungen",
      du: "{anzahl} Firmen aus Treffern und Bewerbungen",
      lehrstelle: "{anzahl} Lehrbetriebe aus Treffern und Bewerbungen",
    },
    "firmen.zeile.gefunden": {
      sie: "{gefunden} bei kununu gefunden", du: "{gefunden} bei kununu gefunden", lehrstelle: "{gefunden} bei kununu gefunden",
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
      sie: "Ohne Einwilligung gehen keine Texte an die KI, auch nicht mit einem eigenen Schlüssel. Suche, Unterlagen und Versand funktionieren trotzdem. Mit dem Claude-Abo läuft die KI über Ihr eigenes Konto bei Anthropic; dafür gilt der Hinweis beim Claude-Abo.",
      du: "Ohne Einwilligung gehen keine Texte an die KI, auch nicht mit einem eigenen Schlüssel. Suche, Unterlagen und Versand funktionieren trotzdem. Mit dem Claude-Abo läuft die KI über dein eigenes Konto bei Anthropic; dafür gilt der Hinweis beim Claude-Abo.",
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
    // Card «Sprache» (G12, #94)
    "einstellungen.sprache-inserat": {
      sie: "Das Anschreiben entsteht in der Sprache des Inserats, wenn Sie sich in dieser Sprache bewerben.",
      du: "Das Anschreiben entsteht in der Sprache des Inserats, wenn du dich in dieser Sprache bewirbst.",
    },

    // Search (step 5)
    "suche.wie": {
      sie: "Die Erweiterung sucht in Ihrem Browser und nur, wenn Sie die Suche starten. Die KI schätzt jeden neuen Treffer als Note von 1 bis 6 ein.",
      du: "Die Erweiterung sucht in deinem Browser und nur, wenn du die Suche startest. Die KI schätzt jeden neuen Treffer als Note von 1 bis 6 ein.",
    },
    // #220: „Ihre Bewerbungen“ instead of „Register“
    "suche.schon-titel": { sie: "Schon in Ihren Bewerbungen", du: "Schon in deinen Bewerbungen" },
    "suche.schon-marke": { sie: "schon in Ihren Bewerbungen", du: "schon in deinen Bewerbungen" },
    // G109, #385: a recruiter's ad that may be a saved job, and what a run knew already
    "suche.vielleicht-titel": { sie: "Vielleicht schon in Ihren Bewerbungen", du: "Vielleicht schon in deinen Bewerbungen" },
    "suche.wieder-bewerbungen": { sie: "{anzahl} aus Ihren Bewerbungen", du: "{anzahl} aus deinen Bewerbungen" },
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
    "lebenslauf.ki-grenze": {
      sie: "Die KI stellt nur um und kürzt und fügt nichts hinzu, was nicht in Ihren Angaben steht.",
      du: "Die KI stellt nur um und kürzt und fügt nichts hinzu, was nicht in deinen Angaben steht.",
    },
    "lebenslauf.ki-titel": {
      sie: "Vorschläge der KI für diese Stelle", du: "Vorschläge der KI für diese Stelle",
      lehrstelle: "Vorschläge der KI für diese Lehrstelle",
    },
    "lebenslauf.ki-aus": {
      sie: "Mit KI schlägt die App für diese Stelle Stationen, Reihenfolge und Kurzprofil vor.",
      du: "Mit KI schlägt die App für diese Stelle Stationen, Reihenfolge und Kurzprofil vor.",
      lehrstelle: "Mit KI schlägt die App für diese Lehrstelle Stationen, Reihenfolge und Kurzprofil vor.",
    },
    "lebenslauf.ki-ohne-inserat": {
      sie: "Für Vorschläge der KI fehlt noch der Stellentext.", du: "Für Vorschläge der KI fehlt noch der Stellentext.",
    },
    "lebenslauf.ki-bereit": {
      sie: "Die KI kann für diese Stelle Stationen, Reihenfolge und Kurzprofil vorschlagen. Gespeichert wird erst mit «Lebenslauf übernehmen».",
      du: "Die KI kann für diese Stelle Stationen, Reihenfolge und Kurzprofil vorschlagen. Gespeichert wird erst mit «Lebenslauf übernehmen».",
      lehrstelle: "Die KI kann für diese Lehrstelle Stationen, Reihenfolge und Kurzprofil vorschlagen. Gespeichert wird erst mit «Lebenslauf übernehmen».",
    },
    "lebenslauf.ki-schaetzen": { sie: "Kosten und Dauer werden geschätzt …", du: "Kosten und Dauer werden geschätzt …" },
    "lebenslauf.ki-neu-schaetzen": { sie: "Neu schätzen", du: "Neu schätzen" },
    "lebenslauf.ki-gespeichert": {
      sie: "Für diese Bewerbung ist Ihre Auswahl gespeichert. Die KI kann neu vorschlagen; gespeichert wird erst mit «Lebenslauf übernehmen».",
      du: "Für diese Bewerbung ist deine Auswahl gespeichert. Die KI kann neu vorschlagen; gespeichert wird erst mit «Lebenslauf übernehmen».",
    },
    "lebenslauf.ki-angewendet": {
      sie: "Schon angewendet. Ohne Häkchen gilt eine Empfehlung als Ganzes nicht mehr.",
      du: "Schon angewendet. Ohne Häkchen gilt eine Empfehlung als Ganzes nicht mehr.",
    },
    "lebenslauf.ki-laeuft": { sie: "Die KI schlägt vor …", du: "Die KI schlägt vor …" },
    "lebenslauf.ki-holen": { sie: "Vorschläge holen", du: "Vorschläge holen" },
    "lebenslauf.ki-neu": { sie: "Neu vorschlagen lassen", du: "Neu vorschlagen lassen" },
    "lebenslauf.ki-nochmals": { sie: "Nochmals vorschlagen", du: "Nochmals vorschlagen" },
    "lebenslauf.ki-einschalten": { sie: "KI einschalten", du: "KI einschalten" },
    "lebenslauf.ki-zum-stellentext": { sie: "Zum Stellentext", du: "Zum Stellentext" },
    "lebenslauf.vorschau-hinweis": {
      sie: "Die Vorschau folgt Ihrer Wahl. Gespeichert wird erst mit «Lebenslauf übernehmen».",
      du: "Die Vorschau folgt deiner Wahl. Gespeichert wird erst mit «Lebenslauf übernehmen».",
    },
    "lebenslauf.vorschau-geaendert": {
      sie: "Meine Angaben haben sich inzwischen geändert. Öffnen Sie «Lebenslauf erstellen» neu, damit die Vorschau sie zeigt.",
      du: "Meine Angaben haben sich inzwischen geändert. Öffne «Lebenslauf erstellen» neu, damit die Vorschau sie zeigt.",
    },
    // Photo, colour and mark of the CV just created (G77)
    "lebenslauf.mit-foto": { sie: "Mit Foto", du: "Mit Foto" },
    "lebenslauf.foto-fehlt": {
      sie: "Noch kein Foto. Fotos fügen Sie unter «Lebenslauf und Dateien» hinzu.",
      du: "Noch kein Foto. Fotos fügst du unter «Lebenslauf und Dateien» hinzu.",
    },
    "lebenslauf.foto-einspaltig": { sie: "Einspaltig zeigt kein Foto.", du: "Einspaltig zeigt kein Foto." },
    "lebenslauf.farbe-zeichen": { sie: "Farbe und Zeichen ändern", du: "Farbe und Zeichen ändern" },
    "lebenslauf.zeichen-titel": { sie: "Zeichen", du: "Zeichen" },
    "lebenslauf.zeichen-hinweis": {
      sie: "Klein in der Fusszeile jeder Seite, aus Ihren Initialen oder Ihrem Logo.",
      du: "Klein in der Fusszeile jeder Seite, aus deinen Initialen oder deinem Logo.",
    },
    "lebenslauf.zeichen-ohne": { sie: "Ohne Zeichen", du: "Ohne Zeichen" },
    "lebenslauf.zeichen-logo": { sie: "Ihr Logo", du: "Dein Logo" },
    "lebenslauf.logo-fehlt": {
      sie: "Zuerst ein Logo hochladen, unter «Dossier gestalten».",
      du: "Zuerst ein Logo hochladen, unter «Dossier gestalten».",
    },
    "lebenslauf.farbe-titel": { sie: "Farbe", du: "Farbe" },
    "lebenslauf.farbe-hinweis": {
      sie: "Für Linien und Überschriften. Alle Farben sind gut lesbar.",
      du: "Für Linien und Überschriften. Alle Farben sind gut lesbar.",
    },
    "lebenslauf.farbe-passend": { sie: "Passend zum Design", du: "Passend zum Design" },
    "lebenslauf.farbe-passend-zeile": { sie: "passend zum Design", du: "passend zum Design" },
    "lebenslauf.aussehen-hinweis": {
      sie: "Gilt nur für diese Bewerbung. Ein Dossier hat Design, Farbe und Zeichen aus «Dossier gestalten»; das Foto nimmt es von hier.",
      du: "Gilt nur für diese Bewerbung. Ein Dossier hat Design, Farbe und Zeichen aus «Dossier gestalten»; das Foto nimmt es von hier.",
    },
    "lebenslauf.erstellen-titel": {
      sie: "Lebenslauf für diese Stelle", du: "Lebenslauf für diese Stelle", lehrstelle: "Lebenslauf für diese Lehrstelle",
    },
    "lebenslauf.erstellen-intro": {
      sie: "Die App baut ihn aus Ihren Angaben. Was drinsteht und wie er aussieht, wählen Sie getrennt. Danach steht er wie jede Variante zur Wahl.",
      du: "Die App baut ihn aus deinen Angaben. Was drinsteht und wie er aussieht, wählst du getrennt. Danach steht er wie jede Variante zur Wahl.",
    },
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
    // G92: a CV over its limit is cut or allowed three pages for this application, never kept with «So lassen»
    "bewerbung.kuerzen": {
      sie: "Der Lebenslauf ist zu lang, auch so eng wie möglich gesetzt. Wählen Sie unter «Unterlagen erstellen und prüfen», was für diese Bewerbung wegfällt, oder erlauben Sie drei Seiten.",
      du: "Der Lebenslauf ist zu lang, auch so eng wie möglich gesetzt. Wähle unter «Unterlagen erstellen und prüfen», was für diese Bewerbung wegfällt, oder erlaube drei Seiten.",
    },
    "kuerzen.hinweis": {
      sie: "Meine Angaben und Varianten bleiben, wie sie sind. Weggelassenes holen Sie im Schritt Lebenslauf zurück.",
      du: "Meine Angaben und Varianten bleiben, wie sie sind. Weggelassenes holst du im Schritt Lebenslauf zurück.",
    },
    // The letter editor in the step Anschreiben (G94, #332); an apprenticeship keeps «Anschreiben»
    "anschreiben.editor-intro": {
      sie: "Passen Sie den Text an die Stelle und die Firma an. Jeder Absatz hat ein eigenes Feld.",
      du: "Pass den Text an die Stelle und die Firma an. Jeder Absatz hat ein eigenes Feld.",
      lehrstelle: "Pass den Text an die Lehrstelle und den Lehrbetrieb an. Jeder Absatz hat ein eigenes Feld.",
    },
    "anschreiben.editor-freigabe": {
      sie: "Mit dem Speichern ist die Freigabe aufgehoben; geben Sie das Anschreiben danach neu frei.",
      du: "Mit dem Speichern ist die Freigabe aufgehoben; gib das Anschreiben danach neu frei.",
    },
    "anschreiben.editor-als-text": { sie: "Empfänger, Ort und Datum ändern Sie als Text.", du: "Empfänger, Ort und Datum änderst du als Text." },
    "anschreiben.gespeichert": {
      sie: "Gespeichert. Erstellen Sie die Unterlagen neu, damit PDF und Prüfung den neuen Text zeigen.",
      du: "Gespeichert. Erstelle die Unterlagen neu, damit PDF und Prüfung den neuen Text zeigen.",
    },
    "anschreiben.nicht-erreichbar": {
      sie: "Nicht gespeichert: Die App antwortet nicht. Der Text bleibt hier; versuchen Sie es nochmals.",
      du: "Nicht gespeichert: Die App antwortet nicht. Der Text bleibt hier; versuch es nochmals.",
    },
    "anschreiben.geaendert": {
      sie: "Nicht gespeichert: Das Anschreiben hat sich inzwischen geändert, etwa durch einen neuen Entwurf. Kopieren Sie, was Sie behalten möchten, und laden Sie die Seite neu.",
      du: "Nicht gespeichert: Das Anschreiben hat sich inzwischen geändert, etwa durch einen neuen Entwurf. Kopier, was du behalten möchtest, und lade die Seite neu.",
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
    "uebersicht.von-hand": { sie: "Stelle selbst erfassen", du: "Stelle selbst erfassen", lehrstelle: "Lehrstelle selbst erfassen" },
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
    "heute.gespraech.termin": { sie: "Termin fürs Gespräch eintragen", du: "Termin fürs Gespräch eintragen", lehrstelle: "Termin für die Einladung eintragen" },
    "heute.gespraech.ohne-termin": {
      sie: "{firma} hat Sie eingeladen. Mit dem Termin erinnert die App Sie rechtzeitig an die Vorbereitung.",
      du: "{firma} hat dich eingeladen. Mit dem Termin erinnert dich die App rechtzeitig an die Vorbereitung.",
    },
    "heute.stand": { sie: "Ihr Stand", du: "Dein Stand" },
    "heute.stand.neu": { sie: "Neue Stellen", du: "Neue Stellen", lehrstelle: "Neue Lehrstellen" },
    // the two parts of the «·» line of a pass through the saved jobs (#342)
    "heute.durchgang.anzahl": {
      sie: "{anzahl} gemerkte Stellen", du: "{anzahl} gemerkte Stellen", lehrstelle: "{anzahl} gemerkte Lehrstellen",
    },
    "heute.durchgang.unter": {
      sie: "bewerben oder verwerfen, eine nach der anderen",
      du: "bewerben oder verwerfen, eine nach der anderen",
      lehrstelle: "bewerben oder verwerfen, eine nach der anderen",
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
      sie: "Haben Sie einen Einladungscode? Er bringt ein Budget von CHF 5 pro Monat für die KI.",
      du: "Hast du einen Einladungscode? Er bringt ein Budget von CHF 5 pro Monat für die KI.",
    },
    "einrichtung.ki.ohne": {
      sie: "Ohne KI funktionieren Suche, Unterlagen und Versand trotzdem. Anschreiben laden Sie dann selbst hoch, und Treffer bekommen keine Note.",
      du: "Ohne KI funktionieren Suche, Unterlagen und Versand trotzdem. Anschreiben lädst du dann selbst hoch, und Treffer bekommen keine Note.",
    },
    "ki-fenster.abo": {
      sie: "Claude arbeitet dann mit Ihrem eigenen Konto bei Anthropic. Die Schritte dafür, mit den Skills und der Verbindung zu Claude Desktop, stehen in den Einstellungen.",
      du: "Claude arbeitet dann mit deinem eigenen Konto bei Anthropic. Die Schritte dafür, mit den Skills und der Verbindung zu Claude Desktop, stehen in den Einstellungen.",
    },
  };

  function satzOder(satz) {
    return SAETZE.includes(satz) ? satz : VORGABE;
  }

  // ---------- The app language (#414, docs/design/sprachen.md) ----------
  // The server names the language in <html lang> and hands the page the catalog of that language as /uebersetzung.js
  // (`Uebersetzung`). The German text is the key, so German needs no catalog and a missing entry shows German.
  const DEUTSCH = "de";
  // An apprenticeship falls back to du, du to Sie; English has no du, so it always lands on Sie.
  const RUECKFALL = { "lehrstelle-du": ["lehrstelle", "du", "sie"], "stelle-du": ["du", "sie"], "stelle-sie": ["sie"] };
  let gesetzteSprache = null;
  let gesetzterKatalog = null;

  /** For tests: a language and its catalog as /uebersetzung.js sets it; without arguments the page decides again. */
  function setzeSprache(sprache = null, katalog = null) {
    gesetzteSprache = sprache;
    gesetzterKatalog = katalog;
  }

  function aktuelleSprache() {
    if (gesetzteSprache) return gesetzteSprache;
    return String(global.document?.documentElement?.lang ?? "").slice(0, 2).toLowerCase() || DEUTSCH;
  }

  function katalog() {
    const sprache = aktuelleSprache();
    const gefunden = gesetzterKatalog ?? global.Uebersetzung;
    return sprache !== DEUTSCH && gefunden?.sprache === sprache ? gefunden : null;
  }

  // Own properties only: a German text such as „constructor“ must never find a property of Object.
  const eigener = (objekt, schluessel) =>
    objekt != null && Object.prototype.hasOwnProperty.call(objekt, schluessel) ? objekt[schluessel] : undefined;
  const fuelle = (roh, werte) => roh.replace(/\{(\w+)\}/g, (_, name) => String(werte[name] ?? ""));
  const form = (eintrag, satz) =>
    RUECKFALL[satz].map(name => eigener(eintrag, name)).find(wert => typeof wert === "string" && wert !== "");

  /** A German text in the app language, with {name} filled from `werte`: Texte.t("Abgabe bis {datum}", { datum }). */
  function t(deutsch, werte = {}) {
    const uebersetzt = eigener(katalog()?.texte, deutsch);
    return fuelle(typeof uebersetzt === "string" && uebersetzt !== "" ? uebersetzt : deutsch, werte);
  }

  /** The text of a key in a set and the app language, with {name} filled from `werte`. An unknown key is a programming error. */
  function text(schluessel, satz, werte = {}) {
    const eintrag = TEXTE[schluessel];
    if (!eintrag) throw new Error(`Unbekannter Text: ${schluessel}`);
    const gewaehlt = satzOder(satz);
    return fuelle(form(eigener(katalog()?.saetze, schluessel), gewaehlt) ?? form(eintrag, gewaehlt), werte);
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

  // Where a new invitation code is requested once its credit is used up (#315): the contact on the help page.
  const CODE_REQUEST_URL = "https://bewerbungsbegleiter.ch/hilfe.html#kontakt";
  // Whole word only, so „Anforderungen“ or „angefordert“ stay text; no lookbehind for older Safari.
  const REQUEST_WORD = /(^|[^\p{L}])(anfordern)(?![\p{L}])/u;
  const NEW_TAB = ", öffnet neuen Tab";

  /**
   * `sentence` as parts for App.el, with the first „anfordern“ as a link to CODE_REQUEST_URL. The app runs in the
   * system browser, so a new tab opens the website there. Without the word the sentence stays one part.
   */
  function withCodeRequestLink(sentence, el) {
    const value = String(sentence ?? "");
    const found = REQUEST_WORD.exec(value);
    if (!found) return value ? [value] : [];
    const start = found.index + found[1].length;
    const end = start + found[2].length;
    const link = el("a", { href: CODE_REQUEST_URL, target: "_blank", rel: "noopener" }, found[2],
      el("span", { class: "visually-hidden" }, NEW_TAB));
    return [value.slice(0, start), link, value.slice(end)].filter(part => part !== "");
  }

  // ---------- The monthly AI budget of the mediation (G98) ----------
  // Month and renewal come from the mediation (`monat`, `erneuert_am`); the pages only word them, so a wrong clock on
  // this computer never shows another month. Without them the mediation still counts a one-time credit (G80).
  const MONTH_NAMES = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                       "November", "Dezember"];
  const BUDGET_MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
  const RENEWAL_DAY = /^(\d{4})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/;
  // Day and month never part at the end of a line; screen readers read it as a space.
  const NBSP = "\u00a0";
  const chf = amount => `CHF${NBSP}${amount.toFixed(2)}`;
  const CREDIT_USED_ONCE = " Das Guthaben ist aufgebraucht: einen neuen Code anfordern und unter Einstellungen, KI, Budget und Sprache einlösen.";

  function realDay(found) {
    const [year, month, day] = [Number(found[1]), Number(found[2]), Number(found[3])];
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  }

  /**
   * { month: "November", renews: "1. Dezember" } from GET /api/ki/status or an estimate; null from a mediation that
   * names no renewal, or names it in a form the page cannot read.
   */
  function budgetMonth(answer) {
    const month = BUDGET_MONTH.exec(answer?.monat ?? "");
    const day = RENEWAL_DAY.exec(answer?.erneuert_am ?? "");
    if (!month || !day || !realDay(day)) return null;
    return { month: MONTH_NAMES[Number(month[1]) - 1], renews: `${Number(day[3])}.${NBSP}${MONTH_NAMES[Number(day[2]) - 1]}` };
  }

  /** The credit in the window „KI einrichten“ and on the page „KI“; empty without an amount of the mediation. */
  function budgetPart(status) {
    if (!status || typeof status.guthaben_chf !== "number") return "";
    const spent = Number(status.verbraucht_chf || 0);
    const usedUp = spent >= status.guthaben_chf;
    const used = `${chf(spent)} von ${chf(status.guthaben_chf)} verbraucht.`;
    const budget = budgetMonth(status);
    if (!budget) return ` Guthaben: ${used}${usedUp ? CREDIT_USED_ONCE : ""}`;
    return ` KI-Budget im ${budget.month}: ${used}${usedUp ? ` Es ist aufgebraucht; die KI geht wieder ab ${budget.renews}.` : ""}`;
  }

  const texte = { SAETZE, VORGABE, TEXTE, CODE_REQUEST_URL, satzOder, text, t, setzeSprache, anwenden, statusName,
                  notenText, withCodeRequestLink, budgetMonth, budgetPart };
  if (typeof module !== "undefined") module.exports = texte;
  else global.Texte = texte;
})(typeof window !== "undefined" ? window : globalThis);
