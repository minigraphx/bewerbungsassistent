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

  // G39, G41: one design for all pages (Siegel without a choice), under „Erweitert“ one per page
  const DESIGNS = ["siegel", "raster", "register"];
  const SEITEN = ["deckblatt", "anschreiben", "lebenslauf", "weitere"];

  function pruefeDesign(name) {
    if (!DESIGNS.includes(name)) throw new Error("Bitte Siegel, Raster oder Register wählen");
  }

  const design = b => b.dossier_design || DESIGNS[0];
  const abweichend = b => b.dossier_seiten || {};

  /** The design of each page as { seite: design }. */
  const seitenDesigns = b => Object.fromEntries(SEITEN.map(seite => [seite, abweichend(b)[seite] || design(b)]));

  /** Whether a page has a design of its own; then „Erweitert“ shows open. */
  const gemischt = b => SEITEN.some(seite => seitenDesigns(b)[seite] !== design(b));

  /** Body for one design for all pages: pages with their own design go back to it. Null when nothing changes. */
  function designSpeichern(b, neu) {
    pruefeDesign(neu);
    if (neu === design(b) && !gemischt(b)) return null;
    return { id: b.id, dossier_design: neu, dossier_seiten: {} };
  }

  /** Body for the design of one page; pages with the common design are not stored apart. Null when unchanged. */
  function seiteSpeichern(b, seite, neu) {
    pruefeDesign(neu);
    if (!SEITEN.includes(seite)) throw new Error(`Unbekannte Seite: ${seite}`);
    if (seitenDesigns(b)[seite] === neu) return null;
    const alle = { ...seitenDesigns(b), [seite]: neu };
    const eigene = Object.fromEntries(Object.entries(alle).filter(([, name]) => name !== design(b)));
    return { id: b.id, dossier_seiten: eigene };
  }

  const logik = { VOREINSTELLUNG, WAHL, gewaehlt, zuSpeichern, rahmen, DESIGNS, SEITEN, design, seitenDesigns, gemischt,
                  designSpeichern, seiteSpeichern };
  if (typeof module !== "undefined") module.exports = logik;
  else global.UnterlagenWahl = logik;
})(typeof window !== "undefined" ? window : globalThis);
