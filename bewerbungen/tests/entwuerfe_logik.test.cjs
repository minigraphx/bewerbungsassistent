// Entwürfe und Versionen grouped by document (#120).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/entwuerfe-logik.js");

const version = (id, zeit) => ({ id, zeit, beschreibung: `Fassung ${id}`, datei: "cv.yaml" });
const gruppen = [
  { art: "lebenslauf", titel: "Lebenslauf", dokumente: [
    { datei: "cv.yaml", titel: "Lebenslauf", fassungen: [version("c", "2026-11-03"), version("b", "2026-11-02"), version("a", "2026-11-01")] },
    { datei: "jobs/daten.yaml", titel: "Lebenslauf-Zuschnitt daten", fassungen: [version("z", "2026-10-01")] },
  ] },
  { art: "anschreiben", titel: "Anschreiben", dokumente: [
    { datei: "bewerbungen/muster-ag/anschreiben.yaml", titel: "Anschreiben Muster AG", fassungen: [version("m", "2026-11-04")] },
  ] },
];

test("all groups show by default", () => {
  assert.deepEqual(logik.sichtbar(gruppen).map(g => g.art), ["lebenslauf", "anschreiben"]);
});

test("a filter keeps one kind of group", () => {
  assert.deepEqual(logik.sichtbar(gruppen, { art: "anschreiben" }).map(g => g.art), ["anschreiben"]);
});

test("a file from the link of an editor keeps only its document", () => {
  const shown = logik.sichtbar(gruppen, { datei: "jobs/daten.yaml" });
  assert.deepEqual(shown.map(g => g.dokumente.map(d => d.titel)), [["Lebenslauf-Zuschnitt daten"]]);
});

test("a file without drafts shows nothing", () => {
  assert.deepEqual(logik.sichtbar(gruppen, { datei: "suchprofil.md" }), []);
});

test("the filter counts documents per group", () => {
  assert.deepEqual(logik.filter(gruppen).map(f => [f.art, f.zahl]), [["alle", 3], ["lebenslauf", 2], ["anschreiben", 1]]);
});

test("the newest version shows and the older ones fold away", () => {
  const { neueste, aeltere } = logik.fassungen(gruppen[0].dokumente[0]);
  assert.equal(neueste.id, "c");
  assert.deepEqual(aeltere.map(v => v.id), ["b", "a"]);
  assert.equal(logik.aeltereTitel(aeltere), "Ältere Fassungen (2)");
});

test("a single version has nothing to fold", () => {
  const { neueste, aeltere } = logik.fassungen(gruppen[0].dokumente[1]);
  assert.equal(neueste.id, "z");
  assert.equal(logik.aeltereTitel(aeltere), null);
});
