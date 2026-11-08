// Setup step „Erweiterung“: only a hand-loaded extension can be told to reload (MIN-407).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/einrichtung-logik.js");

test("a hand-loaded extension with another version is told to reload", () => {
  assert.equal(logik.erweiterungZustand("0.2.11", "0.2.12", true), "veraltet");
});

test("a version from the store counts as ready, it lags behind the app after every release", () => {
  assert.equal(logik.erweiterungZustand("0.2.11", "0.2.12", false), "bereit");
});

test("the same version is ready, however it was loaded", () => {
  assert.equal(logik.erweiterungZustand("0.2.12", "0.2.12", true), "bereit");
  assert.equal(logik.erweiterungZustand("0.2.12", "0.2.12", false), "bereit");
});

test("without a version from the app there is nothing to compare", () => {
  assert.equal(logik.erweiterungZustand("0.2.12", null, true), "bereit");
  assert.equal(logik.erweiterungZustand("0.2.12", "", true), "bereit");
});

test("no extension is no extension", () => {
  assert.equal(logik.erweiterungZustand("", "0.2.12", false), "fehlt");
  assert.equal(logik.erweiterungZustand("", null, true), "fehlt");
});

// Step „Datei“: existing Markdown files are kept unless replacing is picked per file (G26, #163).

test("every existing file starts as kept, so nothing is replaced by default", () => {
  const wahl = logik.startWahl([{ datei: "suchprofil.md" }, { datei: "anschreiben/stil.md" }]);
  assert.deepEqual({ ...wahl }, { "suchprofil.md": "behalten", "anschreiben/stil.md": "behalten" });
  assert.deepEqual(logik.zuErsetzen(wahl), []);
});

test("only the files picked for replacing are sent", () => {
  assert.deepEqual(logik.zuErsetzen({ "suchprofil.md": "ersetzen", "anschreiben/stil.md": "behalten" }), ["suchprofil.md"]);
});

test("each line of the differences says whether it goes or comes", () => {
  assert.deepEqual(["gleich", "weg", "neu", "luecke"].map(art => logik.zeilenZeichen(art)), ["  ", "− ", "+ ", "…"]);
});
