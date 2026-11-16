// Dossier or cover letter and CV (G40, G41): which choice counts, what to save and which PDFs the page shows.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const wahl = require("../seiten/unterlagen-wahl.js");
const logik = require("../seiten/bewerbung-logik.js");

const entry = (fields = {}) => ({ id: "a", firma: "Muster AG", stelle: "Sachbearbeiterin", status: "Bewerben", ...fields });

test("without a choice the two files are preset", () => {
  assert.equal(wahl.gewaehlt(entry()), "einzeln");
  assert.equal(wahl.gewaehlt(entry({ unterlagen: "einzeln" })), "einzeln");
  assert.equal(wahl.gewaehlt(entry({ unterlagen: "dossier" })), "dossier");
});

test("only a changed choice is saved", () => {
  assert.equal(wahl.zuSpeichern(entry(), "einzeln"), null);
  assert.deepEqual(wahl.zuSpeichern(entry(), "dossier"), { id: "a", unterlagen: "dossier" });
  assert.deepEqual(wahl.zuSpeichern(entry({ unterlagen: "dossier" }), "einzeln"), { id: "a", unterlagen: "einzeln" });
  assert.throws(() => wahl.zuSpeichern(entry(), "mappe"), /Dossier/);
});

test("the page shows the dossier first, then the single files", () => {
  const all = { lebenslauf: true, anschreiben: true, dossier: true };
  assert.deepEqual(wahl.rahmen(all, "dossier").map(([art]) => art), ["dossier", "anschreiben", "lebenslauf"]);
  assert.deepEqual(wahl.rahmen(all, "einzeln").map(([art]) => art), ["lebenslauf", "anschreiben"]);
  assert.deepEqual(wahl.rahmen({ lebenslauf: true, anschreiben: false }, "einzeln").map(([art]) => art), ["lebenslauf"]);
});

test("with the dossier chosen the documents are built only once the dossier is there", () => {
  const daten = (unterlagen, pdfs) => ({
    bewerbung: entry({ unterlagen, variante: "x" }), stellentext: "Wir suchen …", varianten: [{ id: "x" }],
    hat_anschreiben: true, eigenes_anschreiben: false, anschreiben_freigabe: { noetig: false }, pdfs,
  });
  const step = d => logik.schritte(d, { befunde: [] }).find(s => s.id === "pruefen");
  const singles = { lebenslauf: true, anschreiben: true };

  assert.equal(step(daten(undefined, singles)).erledigt, true);
  assert.equal(step(daten("dossier", { ...singles, dossier: false })).erledigt, false);
  assert.equal(logik.naechster(daten("dossier", { ...singles, dossier: false })).art, "erstellen");
  assert.equal(step(daten("dossier", { ...singles, dossier: true })).erledigt, true);
});

test("without a design every page is Siegel and „Erweitert“ stays closed", () => {
  assert.deepEqual(wahl.seitenDesigns(entry()), { deckblatt: "siegel", anschreiben: "siegel", lebenslauf: "siegel", weitere: "siegel" });
  assert.equal(wahl.gemischt(entry()), false);
});

// #322: the dialog «Dossier gestalten» keeps the choice as a draft and saves it with «Übernehmen»
const ALL_RASTER = { deckblatt: "raster", anschreiben: "raster", lebenslauf: "raster", weitere: "raster" };

test("the draft starts from the application", () => {
  const mixed = entry({ dossier_design: "register", dossier_seiten: { lebenslauf: "raster" } });
  assert.deepEqual(wahl.entwurf(mixed), { design: "register",
    seiten: { deckblatt: "register", anschreiben: "register", lebenslauf: "raster", weitere: "register" } });
});

test("one design for all pages in the draft puts pages with their own design back to it", () => {
  const mixed = wahl.entwurf(entry({ dossier_design: "siegel", dossier_seiten: { anschreiben: "register" } }));
  assert.deepEqual(wahl.entwurfDesign(mixed, "raster"), { design: "raster", seiten: ALL_RASTER });
  assert.deepEqual(mixed.seiten.anschreiben, "register", "the draft before stays as it was");
  assert.throws(() => wahl.entwurfDesign(mixed, "bunt"), /Siegel, Raster oder Register/);
});

test("one page of the draft gets its own design", () => {
  const draft = wahl.entwurf(entry({ dossier_design: "register" }));
  const changed = wahl.entwurfSeite(draft, "lebenslauf", "raster");
  assert.equal(changed.seiten.lebenslauf, "raster");
  assert.equal(draft.seiten.lebenslauf, "register", "the draft before stays as it was");
  assert.throws(() => wahl.entwurfSeite(draft, "rueckseite", "raster"), /Seite/);
  assert.throws(() => wahl.entwurfSeite(draft, "lebenslauf", "bunt"), /Siegel, Raster oder Register/);
});

test("«Übernehmen» saves the draft only when it differs, each page apart only where it differs", () => {
  const b = entry({ dossier_design: "register" });
  assert.equal(wahl.entwurfSpeichern(b, wahl.entwurf(b)), null);
  assert.deepEqual(wahl.entwurfSpeichern(entry(), wahl.entwurfDesign(wahl.entwurf(entry()), "raster")),
    { id: "a", dossier_design: "raster", dossier_seiten: {} });
  assert.deepEqual(wahl.entwurfSpeichern(b, wahl.entwurfSeite(wahl.entwurf(b), "lebenslauf", "raster")),
    { id: "a", dossier_design: "register", dossier_seiten: { lebenslauf: "raster" } });
  const mixed = entry({ dossier_design: "register", dossier_seiten: { lebenslauf: "raster", anschreiben: "siegel" } });
  assert.deepEqual(wahl.entwurfSpeichern(mixed, wahl.entwurfSeite(wahl.entwurf(mixed), "lebenslauf", "register")),
    { id: "a", dossier_design: "register", dossier_seiten: { anschreiben: "siegel" } });
  assert.equal(wahl.gemischt(mixed), true);
  assert.deepEqual(wahl.seitenDesigns(mixed), { deckblatt: "register", anschreiben: "siegel", lebenslauf: "raster", weitere: "register" });
});
