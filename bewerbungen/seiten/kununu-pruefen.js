"use strict";
// „Prüfen“ for one company (G35, #189): with the extension it reads kununu in a tab and stores the value in the app;
// without it, kununu only opens in a new tab. Used by the pages Firmen and Stellen suchen.
(() => {
  const SEITE = "bewerbungsbegleiter-seite";
  const ERWEITERUNG = "bewerbungsbegleiter-erweiterung";
  const FRAGE = "kununu-pruefen";
  const WARTEN_MS = 120000;  // a search and a company page, each up to the load limit of the extension
  const KEINE_ANTWORT = "Die Erweiterung antwortet nicht. Bitte sie neu laden und es nochmals versuchen.";
  const hatErweiterung = () => Boolean(document.documentElement.dataset.bewerbungsbegleiterErweiterung);

  /** Resolves with the answer of the extension, or { geoeffnet: true } when there is none. */
  function pruefe(firma) {
    if (!hatErweiterung()) {
      window.open(window.FirmenLogik.pruefenLink(firma), "_blank", "noopener,noreferrer");
      return Promise.resolve({ geoeffnet: true });
    }
    return new Promise(resolve => {
      const fertig = antwort => {
        clearTimeout(uhr);
        window.removeEventListener("message", horchen);
        resolve(antwort);
      };
      const horchen = event => {
        const d = event.data;
        if (event.source !== window || event.origin !== location.origin || d?.quelle !== ERWEITERUNG) return;
        if (d.art === "antwort" && d.frage === FRAGE) fertig(d.antwort);
      };
      const uhr = setTimeout(() => fertig({ fehler: KEINE_ANTWORT }), WARTEN_MS);
      window.addEventListener("message", horchen);
      window.postMessage({ quelle: SEITE, art: FRAGE, firma: firma.schluessel, name: firma.name, link: firma.kununu?.link || null },
        location.origin);
    });
  }

  window.KununuPruefen = { pruefe };
})();
