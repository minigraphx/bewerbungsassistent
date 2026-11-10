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
