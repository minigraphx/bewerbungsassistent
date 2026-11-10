// An optional field that #218 presets and the person emptied stays empty after saving and reopening (#230).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { collectBundle, stateFromBundle } = require("../src/model.js");
const { withPresets } = require("../src/presets.js");
const { validateBundle } = require("../src/validate.js");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const PERSON = { name: "Erika Beispiel", city: "Bern", email: "erika@example.ch" };

/** Save as the page does (file or take-over), read the saved answers again and show the steps once more. */
function reopen(state) {
  const saved = JSON.parse(JSON.stringify(collectBundle(form, state, new Date("2026-11-11T08:00:00Z"))));
  return withPresets(form, stateFromBundle(form, saved), null);
}

test("an emptied Ort im Datum stays empty after saving and reopening", () => {
  const shown = withPresets(form, { track: "job", data: { person: PERSON } }, null);
  assert.equal(shown.data.style.place, "Bern", "the preset fills it first");
  const emptied = { ...shown, data: { ...shown.data, style: { ...shown.data.style, place: "" } } };

  assert.equal(reopen(emptied).data.style.place, "");
});

test("a field the person never saw still gets its preset on reopening", () => {
  assert.equal(reopen({ track: "job", data: { person: PERSON } }).data.style.place, "Bern");
});

test("a typed value survives, and the kept empty value is no error", () => {
  const typed = withPresets(form, { track: "job", data: { person: PERSON, style: { place: "Thun" } } }, null);
  assert.equal(reopen(typed).data.style.place, "Thun");
  const emptied = { ...typed, data: { ...typed.data, style: { ...typed.data.style, place: "" } } };
  const errors = validateBundle(form, collectBundle(form, emptied, new Date("2026-11-11T08:00:00Z")));
  assert.deepEqual(errors.filter(e => e.path.startsWith("style.place")), []);
});

test("other empty values still leave the saved file", () => {
  const state = { track: "job", data: { person: { ...PERSON, phone: "  " } } };
  assert.equal("phone" in collectBundle(form, state, new Date()).data.person, false);
});
