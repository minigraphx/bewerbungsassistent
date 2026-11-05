"use strict";
// What the form of an application sends (MIN-377): only what the person changed, so a page left open overwrites nothing
// that Claude wrote in the meantime. No DOM, so it can be tested.
(function (global) {
  const alsText = wert => (wert === null || wert === undefined || wert === false ? "" : String(wert));

  /** The fields whose value differs from what the page loaded; a form shows numbers and missing values as text. */
  function geaenderteFelder(geladen, werte) {
    return Object.fromEntries(Object.entries(werte).filter(([feld, wert]) => alsText(wert) !== alsText(geladen[feld])));
  }

  /** Only with no letter at all: a draft, a built PDF or an own letter stay, and a sent application is done. */
  const fehltAnschreiben = daten => !daten.hat_anschreiben && !daten.eigenes_anschreiben && !daten.bewerbung.versand;

  /** The same ad can get another grade from the AI: the person sees both and decides. */
  function notenHinweis(bisher, neu) {
    if (alsText(bisher) === "") return "";
    if (Number(bisher) === neu) return "Das ist auch die eingetragene Note.";
    return `Bisher eingetragen: Note ${bisher}. Eine KI-Note ist eine Einschätzung und kann von Lauf zu Lauf abweichen. Die eingetragene Note ändert sich erst mit „Note übernehmen“.`;
  }

  const logik = { fehltAnschreiben, geaenderteFelder, notenHinweis };
  if (typeof module !== "undefined") module.exports = logik;
  else global.FormularLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
