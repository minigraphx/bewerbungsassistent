"use strict";
// „Lebenslauf anpassen“ where the CV is shown (#119): a chosen variant leads to its content, otherwise
// „Meine Angaben“; a finished PDF (own upload or a variant that is a PDF) is used as it is, so it gets a note
// instead of the button. No DOM (tests/lebenslauf_anpassen.test.cjs).
(function (global) {
  const ANGABEN = "/angaben";

  /** { href } of the button, or { wieEsIst: "eigenes" | "variante" } for a PDF used as it is. */
  function ziel({ variante = null, eigenesPdf = false } = {}) {
    if (variante) {
      if (!variante.quelle) return { wieEsIst: "variante" };
      return { href: "/inhalte?" + new URLSearchParams({ datei: variante.quelle, ansicht: "text" }) };
    }
    return eigenesPdf ? { wieEsIst: "eigenes" } : { href: ANGABEN };
  }

  const logik = { ziel };
  if (typeof module !== "undefined") module.exports = logik;
  else global.LebenslaufAnpassen = logik;
})(typeof window !== "undefined" ? window : globalThis);
