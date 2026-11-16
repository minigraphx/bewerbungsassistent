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

  // G39, G41: one design for all pages (Siegel without a choice), under «Design pro Seite» one per page
  const DESIGNS = ["siegel", "raster", "register"];
  const SEITEN = ["deckblatt", "anschreiben", "lebenslauf", "weitere"];

  function pruefeDesign(name) {
    if (!DESIGNS.includes(name)) throw new Error("Bitte Siegel, Raster oder Register wählen");
  }

  const design = b => b.dossier_design || DESIGNS[0];
  const abweichend = b => b.dossier_seiten || {};

  /** The design of each page as { seite: design }. */
  const seitenDesigns = b => Object.fromEntries(SEITEN.map(seite => [seite, abweichend(b)[seite] || design(b)]));

  /** Whether a page has a design of its own; then «Design pro Seite» shows open. */
  const gemischt = b => SEITEN.some(seite => seitenDesigns(b)[seite] !== design(b));

  // #322: the dialog «Dossier gestalten» keeps the designs as a draft { design, seiten } until «Übernehmen»
  const entwurf = b => ({ design: design(b), seiten: seitenDesigns(b) });

  /** One design for all pages: pages with their own design go back to it. */
  function entwurfDesign(draft, neu) {
    pruefeDesign(neu);
    return { design: neu, seiten: Object.fromEntries(SEITEN.map(seite => [seite, neu])) };
  }

  function entwurfSeite(draft, seite, neu) {
    pruefeDesign(neu);
    if (!SEITEN.includes(seite)) throw new Error(`Unbekannte Seite: ${seite}`);
    return { design: draft.design, seiten: { ...draft.seiten, [seite]: neu } };
  }

  /** Body for POST /api/bewerbung; pages with the common design are not stored apart. Null when nothing changes. */
  function entwurfSpeichern(b, draft) {
    const same = draft.design === design(b) && SEITEN.every(seite => draft.seiten[seite] === seitenDesigns(b)[seite]);
    if (same) return null;
    const eigene = Object.fromEntries(Object.entries(draft.seiten).filter(([, name]) => name !== draft.design));
    return { id: b.id, dossier_design: draft.design, dossier_seiten: eigene };
  }

  const logik = { VOREINSTELLUNG, WAHL, gewaehlt, zuSpeichern, rahmen, DESIGNS, SEITEN, design, seitenDesigns, gemischt,
                  entwurf, entwurfDesign, entwurfSeite, entwurfSpeichern };
  if (typeof module !== "undefined") module.exports = logik;
  else global.UnterlagenWahl = logik;
})(typeof window !== "undefined" ? window : globalThis);
