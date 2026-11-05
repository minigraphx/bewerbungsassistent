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
    // Search (step 5)
    "suche.wie": {
      sie: "Die Erweiterung sucht in Ihrem Browser und nur, wenn Sie die Suche starten. Die KI schätzt jeden neuen Treffer als Note von 1 bis 6 ein.",
      du: "Die Erweiterung sucht in deinem Browser und nur, wenn du die Suche startest. Die KI schätzt jeden neuen Treffer als Note von 1 bis 6 ein.",
    },
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
      sie: "Noch keine Bewerbungen. Übernehmen Sie eine Stelle aus der Suche oder erfassen Sie eine von Hand.",
      du: "Noch keine Bewerbungen. Übernimm eine Stelle aus der Suche oder erfasse eine von Hand.",
      lehrstelle: "Noch keine Bewerbungen. Übernimm eine Lehrstelle aus der Suche oder erfasse eine von Hand.",
    },
    "uebersicht.leer.titel": { sie: "Erste Stellen suchen", du: "Erste Stellen suchen", lehrstelle: "Erste Lehrstellen suchen" },
    "uebersicht.leer.text": {
      sie: "Ihre Angaben sind übernommen. Die Erweiterung sucht jetzt auf den Portalen, die KI schätzt jeden Treffer ein. Ein Suchlauf dauert einige Minuten.",
      du: "Deine Angaben sind übernommen. Die Erweiterung sucht jetzt auf den Portalen, die KI schätzt jeden Treffer ein. Ein Suchlauf dauert einige Minuten.",
    },
    "uebersicht.start.text": {
      sie: "Der Assistent hilft Ihnen, passende Stellen zu finden und Unterlagen vorzubereiten. Abschicken und entscheiden bleibt immer bei Ihnen.",
      du: "Der Assistent hilft dir, passende Stellen zu finden und Unterlagen vorzubereiten. Abschicken und entscheiden bleibt immer bei dir.",
      lehrstelle: "Der Assistent hilft dir, passende Lehrstellen und Schnupperlehren zu finden und deine Unterlagen vorzubereiten. Abschicken und entscheiden bleibt immer bei dir.",
    },
    "uebersicht.start.karte": {
      sie: "Lebenslauf, gesuchte Stellen und wie Sie schreiben. Das dauert etwa 20 Minuten. Sie können jederzeit unterbrechen, nichts geht verloren.",
      du: "Lebenslauf, gesuchte Stellen und wie du schreibst. Das dauert etwa 20 Minuten. Du kannst jederzeit unterbrechen, nichts geht verloren.",
      lehrstelle: "Schule, gesuchte Berufe und wie du schreibst. Das dauert etwa 20 Minuten. Du kannst jederzeit unterbrechen, nichts geht verloren.",
    },
    "uebersicht.start.fuss": { sie: "Ihre Angaben bleiben auf diesem Computer.", du: "Deine Angaben bleiben auf diesem Computer." },
    "uebersicht.start.unterlagen": {
      sie: "Lebenslauf und Anschreiben pro Stelle", du: "Lebenslauf und Anschreiben pro Stelle", lehrstelle: "Lebenslauf und Anschreiben pro Lehrstelle",
    },
    "uebersicht.start.abschicken": {
      sie: "machen Sie selbst, das Formular ist vorausgefüllt", du: "machst du selbst, das Formular ist vorausgefüllt",
    },
    "uebersicht.start.festhalten-rav": { sie: "für Sie und fürs RAV", du: "für dich und fürs RAV" },
    "uebersicht.start.festhalten": { sie: "damit Sie den Überblick behalten", du: "damit du den Überblick behältst" },
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

    // Setup (step 2 of the redesign)
    "einrichtung.ordner.frage": {
      sie: "Wo sollen Ihre Unterlagen liegen?",
      du: "Wo sollen deine Unterlagen liegen?",
    },
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

  const texte = { SAETZE, VORGABE, TEXTE, satzOder, text, anwenden, statusName };
  if (typeof module !== "undefined") module.exports = texte;
  else global.Texte = texte;
})(typeof window !== "undefined" ? window : globalThis);
