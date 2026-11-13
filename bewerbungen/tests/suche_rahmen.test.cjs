// Region, Pensum, exclusions and title filter on Suche einstellen (#286, G64): what each card sends, without DOM.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/suche-rahmen-logik.js");

test("a list field holds one entry per line, without empty lines", () => {
  assert.deepEqual(L.zeilen("  Praktikum \n\nEntwickler/Developer\n  \n"), ["Praktikum", "Entwickler/Developer"]);
  assert.deepEqual(L.zeilen(""), []);
  assert.equal(L.alsText(["Praktikum", "Sales"]), "Praktikum\nSales");
  assert.equal(L.alsText(undefined), "");
});

test("the region card sends workload for a job and the radius for an apprenticeship", () => {
  const felder = { wohnort: " Bern ", kantone: ["BE", "SO"], umkreis: "50", pensum: "80 %" };
  assert.deepEqual(L.koerper("region", felder, false), { wohnort: "Bern", kantone: ["BE", "SO"], pensum: "80 %" });
  assert.deepEqual(L.koerper("region", felder, true), { wohnort: "Bern", kantone: ["BE", "SO"], umkreis_km: 50 });
});

test("the cards for exclusions and title filter send their lists", () => {
  assert.deepEqual(L.koerper("nicht", { inserat: "Schicht\nPikett", titel: "Praktikum" }, false),
    { ausschluss: ["Schicht", "Pikett"], titel_ausschluss: ["Praktikum"] });
  assert.deepEqual(L.koerper("titelfilter", { positiv: "Python\n", ausschluss: "" }, false),
    { titel_positiv: ["Python"], titel_ausschluss: [] });
});

test("the radius offers the usual distances and keeps one the profile has", () => {
  assert.deepEqual(L.umkreisWahl(null).map(w => w.wert), [10, 25, 50]);
  assert.deepEqual(L.umkreisWahl(30).map(w => w.text), ["10 km", "25 km", "30 km", "50 km"]);
  assert.equal(L.umkreisGewaehlt(null), 25);
  assert.equal(L.umkreisGewaehlt(30), 30);
});

test("the cantons hint says what an empty choice means for each kind", () => {
  assert.match(L.kantoneHinweis(false), /ganzen Schweiz/);
  assert.match(L.kantoneHinweis(true), /Umkreis/);
});

test("the title filter line says when there is none", () => {
  assert.equal(L.titelfilterLeer, "Kein Titelfilter");
});

test("the excluded companies go as one list, one per line (#226, G65)", () => {
  assert.deepEqual(L.firmenKoerper("Muster Bau AG\n\n  Beispiel Holz  \n"), { firmen: ["Muster Bau AG", "Beispiel Holz"] });
  assert.deepEqual(L.firmenKoerper(""), { firmen: [] });
});

test("an apprenticeship's Was nicht saves only the companies, not the profile", () => {
  assert.equal(L.mitProfil("nicht", false), true);
  assert.equal(L.mitProfil("nicht", true), false);
  assert.equal(L.mitProfil("region", true), true);
});
