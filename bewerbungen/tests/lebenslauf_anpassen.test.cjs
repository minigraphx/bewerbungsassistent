// „Lebenslauf anpassen“ where the CV is shown (#119): Meine Angaben, the chosen variant, or a PDF used as it is.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { ziel } = require("../seiten/lebenslauf-anpassen.js");

test("without a variant it leads to Meine Angaben", () => {
  assert.deepEqual(ziel({}), { href: "/angaben" });
  assert.deepEqual(ziel({ variante: null, eigenesPdf: false }), { href: "/angaben" });
});

test("with a chosen variant it leads to its content", () => {
  const found = ziel({ variante: { id: "daten", quelle: "jobs/daten.yaml" } });
  assert.equal(found.href, "/inhalte?datei=jobs%2Fdaten.yaml&ansicht=text");
});

test("an own PDF has no button but the note that it is used as it is", () => {
  assert.deepEqual(ziel({ eigenesPdf: true }), { wieEsIst: "eigenes" });
});

test("a variant that is a finished PDF is used as it is too", () => {
  assert.deepEqual(ziel({ variante: { id: "fertig", datei: "fertig.pdf" } }), { wieEsIst: "variante" });
  assert.deepEqual(ziel({ variante: { id: "aussen", extern: "Personalbüro" } }), { wieEsIst: "variante" });
  assert.deepEqual(ziel({ variante: { id: "daten", quelle: "jobs/daten.yaml" }, eigenesPdf: true }).href,
    "/inhalte?datei=jobs%2Fdaten.yaml&ansicht=text", "a chosen variant goes before the own PDF");
});
