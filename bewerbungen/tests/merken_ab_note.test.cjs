// „Alle ab Note … merken“ on Stellen (#214, A3): the grade to choose and what the page says before and after.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const logik = require("../seiten/merken-ab-note-logik.js");

const read = name => fs.readFileSync(path.join(__dirname, "..", "seiten", name), "utf8");

test("the grades go from 3 to 6 in half steps, 4.5 by default as in A3", () => {
  assert.deepEqual(logik.NOTEN, [3, 3.5, 4, 4.5, 5, 5.5, 6]);
  assert.equal(logik.gueltigeNote("4"), 4);
  assert.equal(logik.gueltigeNote(3.5), 3.5);
  for (const wert of [undefined, "", "4.2", 7, "vier"]) assert.equal(logik.gueltigeNote(wert), 4.5);
});

test("the button names the chosen grade", () => {
  assert.equal(logik.knopfText(4.5), "Alle ab Note 4.5 merken");
  assert.equal(logik.knopfText(4), "Alle ab Note 4 merken");
});

test("the question names how many hits and which ones, and what stays", () => {
  const frage = logik.bestaetigung({ note: 4, anzahl: 2, treffer: [
    { id: "a", stelle: "Data Engineer", firma: "Muster Daten AG", note: 5.5 },
    { id: "b", stelle: "Python Entwicklerin", firma: "", note: 4 },
  ] });
  assert.equal(frage.titel, "2 Treffer ab Note 4 merken?");
  // each row as the parts of a «·» line (#342)
  assert.deepEqual(frage.zeilen, [["Data Engineer, Muster Daten AG", "Note 5.5"], ["Python Entwicklerin", "Note 4"]]);
  assert.match(frage.nachsatz, /ohne Note/);
  assert.equal(frage.ok, "2 Treffer merken");
  assert.equal(logik.bestaetigung({ note: 5, anzahl: 1, treffer: [{ stelle: "X", firma: "Y", note: 5 }] }).einleitung,
    "Dieser Treffer kommt unter Gemerkt:");
});

test("the message after saving names hits that changed in between", () => {
  assert.equal(logik.ergebnisText({ gemerkt: ["a", "b"], uebersprungen: [] }), "2 Treffer gemerkt.");
  assert.equal(logik.ergebnisText({ gemerkt: ["a"], uebersprungen: ["b"] }),
    "1 Treffer gemerkt. 1 Treffer hat sich inzwischen geändert und bleibt, wie er ist.");
  assert.equal(logik.keinerText(5.5), "Keine neuen Treffer mit Note 5.5 oder besser.");
});

test("a failure names the step and the grade before the reason", () => {
  assert.equal(logik.fehlerText("fragen", 4.5, "Keine Verbindung."),
    "Die Treffer ab Note 4.5 liessen sich nicht laden: Keine Verbindung.");
  assert.equal(logik.fehlerText("merken", 4, "Keine Verbindung."),
    "Die Treffer ab Note 4 liessen sich nicht merken: Keine Verbindung.");
});

test("the page asks before saving and never uses ß", () => {
  const html = read("treffer.html");
  assert.match(html, /<dialog class="dialog" id="ab-note-dialog"/);
  assert.match(html, /<script src="\/merken-ab-note-logik.js"><\/script>\s*<script src="\/merken-ab-note.js"><\/script>/);
  const skript = read("merken-ab-note.js");
  assert.match(skript, /holen\("\/api\/suche\/ab-note"/);
  assert.match(skript, /showModal\(\)/);
  for (const text of [html, skript, read("merken-ab-note-logik.js")]) assert.doesNotMatch(text, /ß/);
});
