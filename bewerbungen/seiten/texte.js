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

  const texte = { SAETZE, VORGABE, TEXTE, satzOder, text, anwenden };
  if (typeof module !== "undefined") module.exports = texte;
  else global.Texte = texte;
})(typeof window !== "undefined" ? window : globalThis);
