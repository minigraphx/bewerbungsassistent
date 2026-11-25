// Einrichtung and the language switch (#435): a reload for the new language keeps what the first step has not saved
// yet, and after the folder is chosen the switch reads that folder's language again, with the note when it differs.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const logik = require("../seiten/einrichtung-logik.js");

const STORED = { gesucht: "stelle", anrede: "sie", rav: false, gewaehlt: false };
const script = fs.readFileSync(path.join(__dirname, "..", "seiten", "einrichtung.js"), "utf8");

test("an unsaved choice of the first step comes back after the reload", () => {
  const kept = logik.keptChoice(STORED, { gesucht: "lehrstelle", anrede: "du", rav: true, ravBeruehrt: true, ordner: "/tmp/Bewerbung" });
  assert.deepEqual(kept, { wahl: { ...STORED, gesucht: "lehrstelle", anrede: "du", rav: true }, ravBeruehrt: true,
                           ordner: "/tmp/Bewerbung" });
});

test("without a kept choice the stored one stays", () => {
  assert.deepEqual(logik.keptChoice(STORED, null), { wahl: STORED, ravBeruehrt: false, ordner: null });
  assert.deepEqual(logik.keptChoice(STORED, "garbled"), { wahl: STORED, ravBeruehrt: false, ordner: null });
});

test("strange values from the browser's storage are left out one by one", () => {
  const kept = logik.keptChoice(STORED, { gesucht: "kaffee", anrede: "ihr", rav: "ja", ravBeruehrt: "x", ordner: 7 });
  assert.deepEqual(kept, { wahl: STORED, ravBeruehrt: false, ordner: null });
});

test("Einrichtung keeps its unsaved choice when the switch reloads the page", () => {
  assert.match(script, /document\.addEventListener\("sprachwahl-neuladen", /);
  assert.match(script, /L\.keptChoice\(/);
});

test("after the folder is chosen or comes back the switch reads that folder's language again", () => {
  assert.match(script, /info = await senden\("\/api\/app\/datenordner", \{ pfad: ordnerPfad\(\) \}\);\n\s*window\.Sprachwahl\?\.refresh\(info\.sprache\);/);
  assert.match(script, /if \(info\?\.sprache\) window\.Sprachwahl\?\.refresh\(info\.sprache\);/);
});
