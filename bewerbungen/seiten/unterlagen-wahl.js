"use strict";
// Dossier or cover letter and CV (G40, G41): which choice counts, what to save and which PDFs the page shows.
// Preset is the two files, so whoever does not choose has nothing to do. No DOM (tests/unterlagen_wahl.test.cjs).
(function (global) {
  const VOREINSTELLUNG = "einzeln";
  const WAHL = [VOREINSTELLUNG, "dossier"];
  const NAMEN = { dossier: "Dossier", anschreiben: "Anschreiben", lebenslauf: "Lebenslauf" };
  const REIHENFOLGE = { dossier: ["dossier", "anschreiben", "lebenslauf"], einzeln: ["lebenslauf", "anschreiben"] };

  /** The choice that counts for an application: the stored one, otherwise the preset. */
  const gewaehlt = b => (b.unterlagen === "dossier" ? "dossier" : VOREINSTELLUNG);

  /** The body for POST /api/bewerbung, or null when the choice did not change. */
  function zuSpeichern(b, neu) {
    if (!WAHL.includes(neu)) throw new Error("Bitte Dossier oder Anschreiben und Lebenslauf wählen");
    return neu === gewaehlt(b) ? null : { id: b.id, unterlagen: neu };
  }

  /** The built PDFs to show as [art, name], in the order of the choice. */
  const rahmen = (pdfs, wahl) => REIHENFOLGE[wahl].filter(art => pdfs[art]).map(art => [art, NAMEN[art]]);

  const logik = { VOREINSTELLUNG, WAHL, gewaehlt, zuSpeichern, rahmen };
  if (typeof module !== "undefined") module.exports = logik;
  else global.UnterlagenWahl = logik;
})(typeof window !== "undefined" ? window : globalThis);
