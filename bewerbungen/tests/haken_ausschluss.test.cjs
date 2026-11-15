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

test("the hint for the ad says such jobs still come into the list", () => {
  assert.equal(L.hinweis("titel_ausschluss"), "Ein Titel mit diesem Wort kommt bei der nächsten Suche nicht mehr in die Liste.");
  assert.equal(L.hinweis("ausschluss"),
    "Solche Stellen kommen weiter in die Liste. Die KI liest es bei jeder weiteren Einschätzung als Ausschluss mit.");
});

test("the confirmation says on which page and under which place the entry stands, and from when it counts", () => {
  assert.equal(L.uebernommen("titel_ausschluss", "Pikettdienst"),
    "«Pikettdienst» steht jetzt auf «Suche einstellen» unter «Im Titel». Gilt ab der nächsten Suche.");
  assert.equal(L.uebernommen("ausschluss", "Pikettdienst"),
    "«Pikettdienst» steht jetzt auf «Suche einstellen» unter «Im Inserat». Gilt ab der nächsten Einschätzung.");
  assert.equal(L.zurueck("ausschluss", "Pikettdienst"), "«Pikettdienst» steht nicht mehr auf «Suche einstellen» unter «Im Inserat».");
});

test("the intro names the card in the address of the set", () => {
  assert.equal(L.frage(Texte.text("einstellen.nicht", "stelle-sie"), false),
    "Die App trägt den Eintrag unten auf «Suche einstellen» unter «Was Sie nicht sehen wollen» ein. Sie können ihn vorher ändern.");
  assert.equal(L.frage(Texte.text("einstellen.nicht", "stelle-du"), true),
    "Die App trägt den Eintrag unten auf «Suche einstellen» unter «Was du nicht sehen willst» ein. Du kannst ihn vorher ändern.");
});

test("the form's words and the button's accessible name", () => {
  assert.equal(L.WO, "Wo eintragen?");
  assert.equal(L.FELD, "Was nicht vorkommen soll");
  assert.equal(L.knopfLabel("Pikettdienst alle vier Wochen"), "Künftig nicht zeigen: Pikettdienst alle vier Wochen");
});
