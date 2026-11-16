// Cut with one click or allow three pages (G92, #323), without a page: the rows, what is sent and what is said.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const K = require("../seiten/kuerzen-logik.js");
const texte = require("../seiten/texte.js");

const kuerzen = {
  zeilen: 7,
  optionen: [
    { id: "stichpunkte:a", text: "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)" },
    { id: "abschnitt:interests", text: "Abschnitt «Interessen»" },
  ],
  drei_seiten: true,
};

test("the first cut is preselected, the others are not", () => {
  assert.deepEqual(K.rows(kuerzen).map(row => [row.id, row.text, row.checked]), [
    ["stichpunkte:a", "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)", true],
    ["abschnitt:interests", "Abschnitt «Interessen»", false],
  ]);
});

test("the main button comes first, «Drei Seiten erlauben» only where it is offered, and there is no «So lassen»", () => {
  assert.deepEqual(K.buttons(kuerzen).map(b => [b.action, b.text, b.primary]),
    [["kuerzen", "Gekürzt neu erstellen", true], ["drei-seiten", "Drei Seiten erlauben", false]]);
  assert.deepEqual(K.buttons({ ...kuerzen, drei_seiten: false }).map(b => b.action), ["kuerzen"]);
  assert.deepEqual(K.buttons({ ...kuerzen, optionen: [] }).map(b => b.action), ["drei-seiten"]);
  const words = JSON.stringify([K.buttons(kuerzen), K.LEGEND]);
  assert.doesNotMatch(words, /So lassen/);
});

test("what is sent: the ticked cuts, or three pages", () => {
  assert.deepEqual(K.body("a-1", "kuerzen", ["stichpunkte:a"]), { id: "a-1", weglassen: ["stichpunkte:a"] });
  assert.deepEqual(K.body("a-1", "drei-seiten", ["stichpunkte:a"]), { id: "a-1", drei_seiten: true });
  assert.equal(K.body("a-1", "kuerzen", []), null, "nothing ticked sends nothing");
});

test("the note says that Meine Angaben stay and where cuts come back, in both forms", () => {
  assert.equal(texte.text("kuerzen.hinweis", "stelle-sie"),
    "Meine Angaben bleiben, wie sie sind. Weggelassenes holen Sie im Schritt Lebenslauf zurück.");
  assert.equal(texte.text("kuerzen.hinweis", "stelle-du"),
    "Meine Angaben bleiben, wie sie sind. Weggelassenes holst du im Schritt Lebenslauf zurück.");
});

test("the next step for a CV over its limit names the choice, not «So lassen»", () => {
  for (const satz of ["stelle-sie", "stelle-du", "lehrstelle-du"]) {
    const text = texte.text("bewerbung.kuerzen", satz);
    assert.match(text, /drei Seiten/);
    assert.doesNotMatch(text, /So lassen/);
  }
  const page = fs.readFileSync(path.join(__dirname, "..", "seiten", "bewerbung.js"), "utf8");
  assert.match(page, /kuerzen: \[K\.NEXT_TITLE, t\("bewerbung\.kuerzen"\)/);
});

test("what is left out is listed with «Zurückholen», three pages with «Zurücknehmen»", () => {
  const rows = K.leftOut({ weggelassen: [{ id: "stichpunkte:a", text: "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)" }], drei_seiten: true });
  assert.deepEqual(rows.map(r => [r.id, r.text, r.button]), [
    ["stichpunkte:a", "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)", "Zurückholen"],
    ["drei-seiten", "Drei Seiten erlaubt", "Zurücknehmen"],
  ]);
  assert.deepEqual(K.leftOut({ weggelassen: [], drei_seiten: false }), []);
  assert.deepEqual(K.leftOut(undefined), []);
});

test("the message after building anew says what happened", () => {
  assert.equal(K.doneMessage("kuerzen", { neu_erstellt: true }), "Gekürzt und neu erstellt.");
  assert.equal(K.doneMessage("drei-seiten", { neu_erstellt: true }), "Drei Seiten erlaubt und neu erstellt.");
  assert.equal(K.doneMessage("zurueck", { neu_erstellt: true }), "Zurückgeholt und neu erstellt.");
  assert.equal(K.doneMessage("kuerzen", { neu_erstellt: false, fehler: "Variante fehlt." }),
    "Gespeichert, aber nicht neu erstellt: Variante fehlt.");
});
