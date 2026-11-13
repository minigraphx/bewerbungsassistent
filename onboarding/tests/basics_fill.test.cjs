// Meine Angaben opens with what search profile, style profile and building blocks hold (#217). All data is invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));

const kept = () => ({
  track: "job",
  data: {
    person: { name: "Erika Beispiel" },
    searchJob: { home: "Bern", workload: "80–100 %", keywords: ["Alt"] },
    strengths: [{ strength: "Alt", example: "Alt." }],
  },
});

test("the sections of the files replace what the page kept", () => {
  const read = { searchJob: { home: "Thun", workload: "60–80 %" }, strengths: [{ strength: "Geduld", example: "Erklärt." }] };

  const filled = model.fillFromBasics(form, kept(), read);

  assert.deepEqual(filled.data.searchJob, { home: "Thun", workload: "60–80 %" });
  assert.deepEqual(filled.data.strengths, [{ strength: "Geduld", example: "Erklärt." }]);
  assert.deepEqual(filled.data.person, { name: "Erika Beispiel" });
});

test("sections of files that do not exist stay as the page kept them", () => {
  const filled = model.fillFromBasics(form, kept(), { style: { tone: "Kurz und direkt" } });

  assert.deepEqual(filled.data.searchJob, kept().data.searchJob);
  assert.deepEqual(filled.data.style, { tone: "Kurz und direkt" });
});

test("without answers from the files nothing changes", () => {
  const state = kept();

  assert.equal(model.fillFromBasics(form, state, null), state);
  assert.equal(model.fillFromBasics(form, state, ["searchJob"]), state);
});

test("cv sections and unknown fields do not come from the basics", () => {
  const filled = model.fillFromBasics(form, kept(), { person: { name: "Fremd" }, searchJob: { home: "Biel", unknown: "x" } });

  assert.deepEqual(filled.data.person, { name: "Erika Beispiel" });
  assert.deepEqual(filled.data.searchJob, { home: "Biel" });
});

test("suggestions on a section taken from the files no longer apply", () => {
  const state = { ...kept(), suggested: { "searchJob.home": true, "person.name": true } };

  const filled = model.fillFromBasics(form, state, { searchJob: { home: "Thun" } });

  assert.deepEqual(filled.suggested, { "person.name": true });
});
