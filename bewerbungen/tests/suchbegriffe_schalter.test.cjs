// One switch per term in the term proposal (#371, G102), without DOM: what a chip means in each state, how a change's
// checkbox follows its terms, the totals of each area and what the page announces. All terms are invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/suchbegriffe-logik.js");

const REPLACE = { nummer: 0, bereich: "positive", entfaellt: ["Engineer"], neu: ["Backend", "Frontend"] };
const ADD = { nummer: 1, bereich: "keywords", entfaellt: [], neu: ["Datenanalyst"] };
const START = { suchbegriffe: ["Python", "Datenanalyst"], positiv: ["Web", "Backend", "Frontend"], ausschluss: ["Praktikum"] };

test("a change shows what it removes, then what it adds, each in its area", () => {
  assert.deepEqual(L.chips(REPLACE), [
    { bereich: "positiv", begriff: "Engineer", art: "gone" },
    { bereich: "positiv", begriff: "Backend", art: "new" },
    { bereich: "positiv", begriff: "Frontend", art: "new" },
  ]);
});

test("a new or current term is on while it is in the result, a removed one while it goes away", () => {
  const [gone, backend] = L.chips(REPLACE);
  assert.equal(L.chipAn(START, gone), true, "Engineer goes away");
  assert.equal(L.chipAn(START, backend), true, "Backend is taken over");
  assert.equal(L.chipAn(START, { bereich: "positiv", begriff: "Web", art: "kept" }), true);
  const kept = L.schalteChip(START, gone, false);
  assert.deepEqual(kept.positiv, ["Web", "Backend", "Frontend", "Engineer"], "switched off, Engineer stays");
  assert.equal(L.chipAn(kept, gone), false);
  assert.deepEqual(START.positiv, ["Web", "Backend", "Frontend"], "the former state stays as it was");
});

test("removing a current term and dropping a proposed one both take it out of the result", () => {
  const off = L.schalteChip(L.schalteChip(START, { bereich: "positiv", begriff: "Web", art: "kept" }, false),
    { bereich: "positiv", begriff: "Frontend", art: "new" }, false);
  assert.deepEqual(off.positiv, ["Backend"]);
  assert.deepEqual(L.schalteChip(off, { bereich: "positiv", begriff: "Web", art: "kept" }, true).positiv, ["Backend", "Web"]);
});

test("the word of a chip says its state, so it never rests on colour", () => {
  assert.equal(L.chipWort({ art: "gone" }, true), "entfällt");
  assert.equal(L.chipWort({ art: "gone" }, false), "bleibt");
  assert.equal(L.chipWort({ art: "new" }, true), "neu");
  assert.equal(L.chipWort({ art: "new" }, false), "neu");
  assert.equal(L.chipWort({ art: "kept" }, true), "");
  assert.equal(L.chipWort({ art: "kept" }, false), "entfällt");
});

test("a change's checkbox is on, off or partly on, and switches its terms together", () => {
  assert.equal(L.karteStand(START, REPLACE), "alle");
  const partly = L.schalteChip(START, L.chips(REPLACE)[2], false);
  assert.equal(L.karteStand(partly, REPLACE), "teilweise");
  const none = L.schalteKarte(partly, REPLACE, false);
  assert.equal(L.karteStand(none, REPLACE), "keine");
  assert.deepEqual(none.positiv, ["Web", "Engineer"]);
  assert.deepEqual(L.schalteKarte(none, REPLACE, true).positiv, ["Web", "Backend", "Frontend"]);
  assert.equal(L.TEILWEISE, "Teilweise übernommen");
});

test("the current terms no change touches stand per area, in the order of the profile, empty areas left out", () => {
  const bereiche = L.bisherigeBereiche({ suchbegriffe: ["Python", "Java Entwickler"], positiv: [], ausschluss: ["Praktikum"] });
  assert.deepEqual(bereiche.map(b => [b.schluessel, b.name, b.chips.map(c => c.begriff)]), [
    ["suchbegriffe", "Suchbegriffe", ["Python", "Java Entwickler"]],
    ["ausschluss", "Titel enthält keines davon", ["Praktikum"]],
  ]);
  assert.ok(bereiche.every(b => b.chips.every(c => c.art === "kept" && c.bereich === b.schluessel)));
});

test("the total of an area says how many are on and how many too many", () => {
  const many = { suchbegriffe: Array.from({ length: 34 }, (_, i) => `Begriff${i}`), positiv: ["Web"], ausschluss: [] };
  const counted = L.zaehlung(many, { suchbegriffe: 31, positiv: 30, ausschluss: 30 });
  assert.deepEqual(counted.map(z => [z.schluessel, z.anzahl, z.zuViel]), [["suchbegriffe", 34, 3], ["positiv", 1, 0], ["ausschluss", 0, 0]]);
  assert.deepEqual(L.legendeTeile(counted[0]), ["Suchbegriffe", "danach 34 eingeschaltet, 3 zu viel"]);
  assert.deepEqual(L.legendeTeile({ ...counted[0], anzahl: 31, zuViel: 0 }), ["Suchbegriffe", "danach 31 eingeschaltet"]);
});

test("the outcome closes with what goes, the success names what is new and what goes", () => {
  assert.equal(L.entfaelltZeile(["Trainer", "Python"]), "Entfällt: Trainer, Python");
  assert.equal(L.entfaelltZeile([]), "");
  const tail = " Die nächste Suche sucht danach. Der bisherige Stand bleibt unter Entwürfe erhalten.";
  assert.equal(L.uebernommen(2, 3), `Übernommen: 2 Begriffe neu, 3 entfallen.${tail}`);
  assert.equal(L.uebernommen(1, 1), `Übernommen: 1 Begriff neu, 1 entfällt.${tail}`);
  assert.equal(L.uebernommen(2, 0), `Übernommen: 2 Begriffe neu.${tail}`);
  assert.equal(L.uebernommen(0, 3), `Übernommen: 3 Begriffe entfallen.${tail}`);
  assert.equal(L.HAUPTKNOPF, "Auswahl übernehmen");
});

const OPEN = { gesperrt: null, zu_viel: { suchbegriffe: 0, positiv: 0, ausschluss: 0 } };
const over = n => ({ gesperrt: "Mit dieser Auswahl wären es …", zu_viel: { suchbegriffe: n, positiv: 0, ausschluss: 0 } });

test("the page announces only when the choice becomes blocked or free, and how many are still too many", () => {
  assert.equal(L.ansage(null, over(3)), "", "nothing on the first answer");
  assert.equal(L.ansage(OPEN, OPEN), "");
  assert.equal(L.ansage(OPEN, over(3)), "Noch 3 Suchbegriffe zu viel");
  assert.equal(L.ansage(over(3), over(2)), "Noch 2 Suchbegriffe zu viel");
  assert.equal(L.ansage(over(2), over(2)), "");
  assert.equal(L.ansage(over(2), over(1)), "Noch 1 Suchbegriff zu viel");
  assert.equal(L.ansage(over(1), OPEN), L.FREI);
  const title = { gesperrt: "…", zu_viel: { suchbegriffe: 0, positiv: 0, ausschluss: 3 } };
  assert.equal(L.ansage(OPEN, title), "Noch 3 Begriffe zu viel in «Titel enthält keines davon»");
  const none = { ...OPEN, gesperrt: "Danach stünde kein Suchbegriff mehr in der Suche. Bitte mindestens einen einschalten." };
  assert.equal(L.ansage(OPEN, none), none.gesperrt, "another reason is announced as it stands");
});

test("arrow keys move within a group of chips, Home and End to its ends, other keys stay with the browser", () => {
  assert.equal(L.rovingZiel("ArrowRight", 0, 3), 1);
  assert.equal(L.rovingZiel("ArrowDown", 2, 3), 2);
  assert.equal(L.rovingZiel("ArrowLeft", 0, 3), 0);
  assert.equal(L.rovingZiel("ArrowUp", 2, 3), 1);
  assert.equal(L.rovingZiel("Home", 2, 3), 0);
  assert.equal(L.rovingZiel("End", 0, 3), 2);
  assert.equal(L.rovingZiel(" ", 1, 3), null);
  assert.equal(L.rovingZiel("Tab", 1, 3), null);
});

test("the sentence over the current terms speaks like the page", () => {
  assert.equal(L.texte("stelle-sie").bisherige, "Alle sind eingeschaltet. Was Sie ausschalten, entfällt beim Übernehmen.");
  assert.equal(L.texte("stelle-du").bisherige, "Alle sind eingeschaltet. Was du ausschaltest, entfällt beim Übernehmen.");
  assert.equal(L.BISHERIGE_OBEN, "Begriffe, die eine Änderung oben betrifft, stehen dort.");
});
