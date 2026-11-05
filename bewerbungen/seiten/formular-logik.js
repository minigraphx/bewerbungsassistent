"use strict";
// What the form of an application sends (MIN-377): only what the person changed, so a page left open overwrites nothing
// that Claude wrote in the meantime. No DOM, so it can be tested.
(function (global) {
  const alsText = wert => (wert === null || wert === undefined || wert === false ? "" : String(wert));

  /** The fields whose value differs from what the page loaded; a form shows numbers and missing values as text. */
  function geaenderteFelder(geladen, werte) {
    return Object.fromEntries(Object.entries(werte).filter(([feld, wert]) => alsText(wert) !== alsText(geladen[feld])));
  }

  const logik = { geaenderteFelder };
  if (typeof module !== "undefined") module.exports = logik;
  else global.FormularLogik = logik;
})(typeof window !== "undefined" ? window : globalThis);
