// Niche searches and the region on Suche einstellen and /suchbegriffe (G111, #387), without DOM: the row «Nischen» of
// the region card, the hint under the cantons, the niche row of «Was die Orte bringen» with its places, and the counts.
// Invented terms; the cantons and towns are those of the invented template profile, or far from it.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const Anzeige = require("../seiten/suche-anzeige.js");
const Rahmen = require("../seiten/suche-rahmen-logik.js");
const Ertrag = require("../seiten/suche-ertrag-logik.js");
const Begriffe = require("../seiten/suchbegriffe-logik.js");

const REGION = { kantone: ["BE", "SO"], orte: ["Bern"], umkreis_km: 20, schweizweit: false, nischen: 2 };

test("the region card says what happens to the niches, with and without cantons", () => {
  assert.equal(Anzeige.nischenText(REGION, false), "Ohne Ort gesucht. Behalten werden Stellen in BE und SO, an Ihren Orten oder mit Remote.");
  assert.equal(Anzeige.nischenText(REGION, false, true), "Ohne Ort gesucht. Behalten werden Stellen in BE und SO, an deinen Orten oder mit Remote.");
  assert.equal(Anzeige.nischenText({ ...REGION, kantone: ["BE", "FR", "SO"] }, false),
    "Ohne Ort gesucht. Behalten werden Stellen in BE, FR und SO, an Ihren Orten oder mit Remote.");
  assert.equal(Anzeige.nischenText({ ...REGION, kantone: [], schweizweit: true }, false), "Ohne Ort gesucht, in der ganzen Schweiz.");
});

test("without niches or for an apprenticeship there is no row", () => {
  assert.equal(Anzeige.nischenText({ ...REGION, nischen: 0 }, false), "");
  assert.equal(Anzeige.nischenText(REGION, true), "");
  assert.equal(Anzeige.nischenText(null, false), "");
});

test("the hint under the cantons adds the niche rule only in a job profile with niches", () => {
  const ohne = "Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst.";
  assert.equal(Rahmen.kantoneHinweis(false), ohne);
  assert.equal(Rahmen.kantoneHinweis(false, 2), `${ohne} Nischen sucht die App ohne Ort; Stellen ausserhalb dieser Kantone `
    + "behält sie nur, wenn das Inserat Remote nennt.");
  assert.match(Rahmen.kantoneHinweis(true, 2), /^Gesucht wird im Umkreis/);
});

const NISCHE = { portal: "", ort: "", ort_name: "", nischen: true, suchen: 30, treffer: 15, neu: 4, ab_note_4: 1, aussortiert: 0,
  ausserhalb_region: 31, ohne_ertrag: false,
  ausserhalb_orte: [{ ort: "Lugano", anzahl: 12 }, { ort: "St. Gallen", anzahl: 7 }, { ort: "Chur", anzahl: 4 }], ausserhalb_andere: 8 };

test("the niche row of «Was die Orte bringen» counts the hits outside the region", () => {
  assert.equal(Ertrag.ortName(NISCHE), "Ohne Ort (Nischen)");
  assert.deepEqual(Ertrag.teile(NISCHE), ["30 Suchen", "15 Treffer", "4 neu", "1 ab Note 4", "31 ausserhalb der Region"]);
  assert.deepEqual(Ertrag.teile({ ...NISCHE, ausserhalb_region: undefined }), ["30 Suchen", "15 Treffer", "4 neu", "1 ab Note 4"]);
});

test("the caption under it names at most three places and the rest", () => {
  assert.equal(Ertrag.ausserhalbOrte(NISCHE), "Ausserhalb der Region, ohne Remote: Lugano 12, St. Gallen 7, Chur 4, andere 8");
  assert.equal(Ertrag.ausserhalbOrte({ ...NISCHE, ausserhalb_orte: [{ ort: "Lugano", anzahl: 2 }], ausserhalb_andere: 0 }),
    "Ausserhalb der Region, ohne Remote: Lugano 2");
  assert.equal(Ertrag.ausserhalbOrte({ ...NISCHE, ausserhalb_orte: undefined }), "");
});

test("the first line explains «Ausserhalb der Region» only when it occurs, in the person's form of address", () => {
  const vorher = "Aus den letzten 3 Suchläufen, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen.";
  assert.equal(Ertrag.ortHinweis(3), vorher);
  assert.equal(Ertrag.ortHinweis(3, true), `${vorher} „Ausserhalb der Region“: Die Stelle liegt ausserhalb Ihrer Kantone und Orte, `
    + "und das Inserat nennt kein Remote.");
  assert.equal(Ertrag.ortHinweis(3, true, true), `${vorher} „Ausserhalb der Region“: Die Stelle liegt ausserhalb deiner Kantone und Orte, `
    + "und das Inserat nennt kein Remote.");
});

test("the niche row of the term table names its hits outside the region, counted in «aussortiert»", () => {
  const nische = { begriff: "Lernatelier", suchen: 6, treffer_portale: 9, aussortiert: 9, ausserhalb_region: 9, treffer: 0, nur_hier: 0,
    ab_note_4: 0, marke: null };
  const [zeile] = Begriffe.tabellenZeilen({ laeufe: 3, noetig: 3, genug: true, begriffe: [], nischen: [nische] });
  assert.deepEqual(zeile, { begriff: "Lernatelier (Nische)", marke: "", zahlen: [6, 9, 9, 0, 0], zusatz: "9 ausserhalb der Region" });
});

test("«ohne Ertrag» names hits outside the region like those without a required word", () => {
  const begriff = { begriff: "Lernatelier", suchen: 3, treffer_portale: 24, aussortiert: 24, treffer: 0, nur_hier: 0, ab_note_4: 0,
    marke: "ohne_ertrag" };
  const rest = fields => Begriffe.markiert({ laeufe: 3, noetig: 3, genug: true, begriffe: [{ ...begriff, ...fields }] })[0].rest;
  assert.equal(rest({ ausserhalb_region: 24 }), ": 3 Suchen, 24 Treffer, alle ausserhalb der Region aussortiert.");
  assert.equal(rest({ ausserhalb_region: 4, ohne_pflichtbezug: 2 }),
    ": 3 Suchen, 24 Treffer, alle aussortiert: 18 vom Titelfilter, 2 ohne Pflichtbezug, 4 ausserhalb der Region.");
  assert.equal(rest({ ohne_pflichtbezug: 18 }), ": 3 Suchen, 24 Treffer, alle aussortiert: 6 vom Titelfilter, 18 ohne Pflichtbezug.");
});
