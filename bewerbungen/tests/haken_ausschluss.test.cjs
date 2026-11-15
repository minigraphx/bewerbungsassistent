"use strict";
// The words for taking a point of the rating over as an exclusion on Stellen (#224, G83).
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/haken-ausschluss-logik.js");
const Texte = require("../seiten/texte.js");

test("the two places carry the names of the card Was Sie nicht sehen wollen", () => {
  assert.deepEqual(L.ARTEN.map(a => [a.art, a.text]), [["titel_ausschluss", "Im Titel"], ["ausschluss", "Im Inserat"]]);
  assert.equal(L.ort("ausschluss"), "Im Inserat");
});

test("the message says where the entry stands and from when it counts", () => {
  assert.equal(L.uebernommen("titel_ausschluss", "Pikettdienst"), "«Pikettdienst» steht jetzt unter «Im Titel». Gilt ab der nächsten Suche.");
  assert.equal(L.uebernommen("ausschluss", "Pikettdienst"), "«Pikettdienst» steht jetzt unter «Im Inserat». Gilt ab der nächsten Einschätzung.");
  assert.equal(L.zurueck("ausschluss", "Pikettdienst"), "«Pikettdienst» steht nicht mehr unter «Im Inserat».");
});

test("the intro names the card in the address of the set and the button names its point", () => {
  assert.equal(L.frage(Texte.text("einstellen.nicht", "stelle-sie"), false),
    "So trägt die App es auf «Suche einstellen» unter «Was Sie nicht sehen wollen» ein. Sie können es vorher ändern.");
  assert.equal(L.frage(Texte.text("einstellen.nicht", "stelle-du"), true),
    "So trägt die App es auf «Suche einstellen» unter «Was du nicht sehen willst» ein. Du kannst es vorher ändern.");
  assert.equal(L.knopfLabel("Pikettdienst"), "Künftig nicht zeigen: «Pikettdienst» als Ausschluss übernehmen");
});
