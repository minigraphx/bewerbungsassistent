// G43: what the page Stellen says before a long run and while the search runs in stages.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/suchlauf-logik.js");

const TEXT = "Diese Suche dauert etwa 23 Minuten: 193 Suchen in 7 Etappen, mit je einer Minute Pause dazwischen.";

test("a long run is announced under the button, a short one is not", () => {
  assert.equal(logik.umfangText({ lang: true, text: TEXT }, ""), TEXT);
  assert.equal(logik.umfangText({ lang: false, text: "" }, ""), "");
  assert.equal(logik.umfangText(null, ""), "");
});

test("no announcement while the button says why the search cannot start", () => {
  assert.equal(logik.umfangText({ lang: true, text: TEXT }, "Zuerst Meine Angaben abschliessen."), "");
});

// The progress line comes as the parts of a «·» line (#342), the page joins them with dot-line.js.
test("the progress names the search, its stage and the pause between stages", () => {
  const step = { portal: "jobs.ch", phase: "suche", stichwort: "Begriff13", seite: 1, nummer: 32, abfragen: 193, etappe: 2, etappen: 7 };
  assert.deepEqual(logik.laufZeile(step), ["jobs.ch: suche „Begriff13“, Seite 1", "Suche 32 von 193, Etappe 2 von 7 …"]);
  assert.deepEqual(logik.laufZeile({ ...step, nummer: 2, abfragen: 4, etappe: 1, etappen: 1 }), ["jobs.ch: suche „Begriff13“, Seite 1", "Suche 2 von 4 …"]);
  assert.deepEqual(logik.laufZeile({ portal: "jobs.ch", phase: "pause", etappe: 3, etappen: 7, sekunden: 50 }),
    ["jobs.ch: Pause vor Etappe 3 von 7, noch 50 Sekunden …"]);
});

test("the progress names the place being searched, a query without place stays as it was", () => {
  const step = { portal: "jobs.ch", phase: "suche", stichwort: "Begriff13", ort: "Nordstadt", seite: 1, nummer: 32, abfragen: 193, etappe: 2, etappen: 7 };
  assert.deepEqual(logik.laufZeile(step), ["jobs.ch: suche „Begriff13“ in Nordstadt, Seite 1", "Suche 32 von 193, Etappe 2 von 7 …"]);
  assert.deepEqual(logik.laufZeile({ ...step, ort: "" }), ["jobs.ch: suche „Begriff13“, Seite 1", "Suche 32 von 193, Etappe 2 von 7 …"]);
});

test("the progress of an older extension without counts still reads", () => {
  assert.deepEqual(logik.laufZeile({ portal: "jobs.ch", phase: "suche", stichwort: "Begriff1", seite: 2 }), ["jobs.ch: suche „Begriff1“, Seite 2 …"]);
  assert.deepEqual(logik.laufZeile({ portal: "jobs.ch", phase: "texte", fertig: 3, von: 9 }), ["jobs.ch: lese Inserat 4 von 9 …"]);
  assert.deepEqual(logik.laufZeile({}), ["Suche startet …"]);
});
