// G43 (#284): „Alle prüfen“ says which hits the AI rates now and which ad the extension loads, without a page.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/treffer-logik.js");

test("the line names the hits of the package the AI rates now", () => {
  assert.equal(logik.pruefSchritt({ bewertet: 10, von: 25 }, ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"], 0),
    "Stellen 11 bis 20 von 25 prüfen …");
  assert.equal(logik.pruefSchritt({ bewertet: 24, von: 25 }, ["y"], 1), "Stelle 25 von 25 prüfen …");
});

test("a package that takes longer says how long it runs, so the line keeps changing", () => {
  assert.equal(logik.pruefSchritt({ bewertet: 0, von: 3 }, ["a", "b", "c"], 12), "Stellen 1 bis 3 von 3 prüfen, seit 12 Sekunden …");
});

test("the run says before each package which hits go out", async () => {
  const begun = [];
  const stand = await logik.bewerteAlle(["a", "b", "c"], {
    paket: 2,
    sende: async (ids) => ({ bewertet: ids.map((id) => ({ id })), offen: [] }),
    angehalten: () => false,
    fortschritt: () => {},
    beginnt: (zwischen, gruppe) => begun.push([zwischen.bewertet, gruppe]),
  });
  assert.deepEqual(begun, [[0, ["a", "b"]], [2, ["c"]]]);
  assert.equal(stand.bewertet, 3);
});

test("while the extension loads the missing ads, the line names the ad it loads now", () => {
  assert.equal(logik.inseratSchritt({ fertig: 3, von: 9 }), "Inserat 4 von 9 holen …");
  assert.equal(logik.inseratSchritt({}), "");
});
