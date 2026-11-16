// The letter editor without DOM (G94, #332): line estimate, longest paragraph, goal line, dirty compare and payload.
// Invented texts only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/letter-editor-logik.js");

const CPL = 99;

test("a paragraph needs about ceil(characters / characters per line) lines; an empty one none", () => {
  assert.equal(L.lineCount("", CPL), 0);
  assert.equal(L.lineCount("   \n ", CPL), 0);
  assert.equal(L.lineCount("x".repeat(99), CPL), 1);
  assert.equal(L.lineCount("x".repeat(100), CPL), 2);
  assert.equal(L.lineCount("x".repeat(217), CPL), 3);
  assert.equal(L.lineCount("  a  \n  b  ", 1), 3, "white space folds as the build sets it: «a b»");
});

test("the hint under a field says the lines, or that an empty field falls away", () => {
  assert.equal(L.lineHint("Kurz.", CPL), "etwa 1 Zeile");
  assert.equal(L.lineHint("x".repeat(250), CPL), "etwa 3 Zeilen");
  assert.equal(L.lineHint("  ", CPL), "Leer: fällt beim Speichern weg.");
});

test("the longest paragraph by characters; on a tie the first one", () => {
  assert.equal(L.longestIndex(["ab", "abcd", "abc"]), 1);
  assert.equal(L.longestIndex(["abcd", "x", "abcd"]), 0);
  assert.equal(L.longestIndex(["", " "]), 0);
  assert.equal(L.longestIndex([]), -1);
});

test("the goal line names the lines too many, then what was saved so far", () => {
  assert.equal(L.goalLine(null, 10, 8), "");
  assert.equal(L.goalLine({ lines: 4 }, 12, 12), "Die Prüfung fand etwa 4 Zeilen zu viel.");
  assert.equal(L.goalLine({ lines: 1 }, 12, 12), "Die Prüfung fand etwa 1 Zeile zu viel.");
  assert.equal(L.goalLine({ lines: 4 }, 12, 13), "Die Prüfung fand etwa 4 Zeilen zu viel.", "longer is no progress");
  assert.equal(L.goalLine({ lines: 4 }, 12, 10), "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 2 Zeilen weniger.");
  assert.equal(L.goalLine({ lines: 4 }, 12, 11), "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 1 Zeile weniger.");
  assert.equal(L.goalLine({ lines: 4 }, 12, 7),
    "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 5 Zeilen weniger; ob es reicht, zeigt erst «Unterlagen erstellen».");
  assert.equal(L.goalLine({ lines: 4 }, 12, 8),
    "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 4 Zeilen weniger; ob es reicht, zeigt erst «Unterlagen erstellen».");
});

test("with no lines counted the goal line only says the letter is over one page", () => {
  assert.equal(L.goalLine({ lines: 0 }, 9, 9), "Die Prüfung fand: Das Anschreiben ist länger als eine Seite.");
  assert.equal(L.goalLine({ lines: 0 }, 9, 7), "Die Prüfung fand: Das Anschreiben ist länger als eine Seite. Bisher etwa 2 Zeilen weniger.");
});

test("the total lines sum the paragraphs", () => {
  assert.equal(L.totalLines(["x".repeat(100), "", "y"], CPL), 3);
});

const loaded = { betreff: "Bewerbung als Testerin", anrede: "Guten Tag", absaetze: ["Eins zwei.", "Drei vier."], gruss: "Freundliche Grüsse" };

test("unchanged or only white space is not dirty; a changed word, a split or a dropped paragraph is", () => {
  assert.equal(L.isDirty(loaded, loaded), false);
  assert.equal(L.isDirty(loaded, { ...loaded, betreff: " Bewerbung als Testerin ", absaetze: ["Eins\nzwei.", "Drei  vier. ", ""] }), false);
  assert.equal(L.isDirty(loaded, { ...loaded, anrede: "Hallo" }), true);
  assert.equal(L.isDirty(loaded, { ...loaded, absaetze: ["Eins.\n\nzwei.", "Drei vier."] }), true);
  assert.equal(L.isDirty(loaded, { ...loaded, absaetze: ["Eins zwei."] }), true);
  assert.equal(L.isDirty(loaded, { ...loaded, absaetze: ["Drei vier.", "Eins zwei."] }), true);
});

test("the paragraphs split at blank lines and fold the rest, as the build reads the text", () => {
  assert.deepEqual(L.paragraphsOf(["  Eins\nzwei ", "Drei.\n  \nVier.", "", "Fünf.\n\n\nSechs."]),
    ["Eins zwei", "Drei.", "Vier.", "Fünf.", "Sechs."]);
});

test("a letter with no paragraph left is empty", () => {
  assert.equal(L.isEmpty({ ...loaded, absaetze: ["", "  \n "] }), true);
  assert.equal(L.isEmpty(loaded), false);
});

test("the payload trims the fields, drops empty paragraphs and carries the fingerprint", () => {
  assert.deepEqual(L.payload({ betreff: " B ", anrede: "A ", absaetze: [" Eins. ", "", "Zwei.\n\nDrei."], gruss: " G" }, "f1"),
    { betreff: "B", anrede: "A", absaetze: ["Eins.", "Zwei.\n\nDrei."], gruss: "G", fingerabdruck: "f1" });
});

test("after removing, the focus goes to the next field, or to the one before when it was the last", () => {
  assert.equal(L.focusAfterRemove(0, 2), 0);
  assert.equal(L.focusAfterRemove(1, 2), 1);
  assert.equal(L.focusAfterRemove(2, 2), 1);
});

test("a refusal names the reason once, without a doubled full stop", () => {
  assert.equal(L.refusedText("Diese Bewerbung ist schon versendet."), "Nicht gespeichert: Diese Bewerbung ist schon versendet. Der Text bleibt hier.");
  assert.equal(L.refusedText("Im Anschreiben fehlen: betreff"), "Nicht gespeichert: Im Anschreiben fehlen: betreff. Der Text bleibt hier.");
});

test("a failed save is a conflict (409), an app that does not answer, or a refusal", () => {
  assert.equal(L.failure(Object.assign(new Error("x"), { status: 409 })), "conflict");
  assert.equal(L.failure(new TypeError("Failed to fetch")), "unreachable");
  assert.equal(L.failure(Object.assign(new Error("x"), { status: 400 })), "refused");
});
