// Meine Angaben fills the CV steps from an existing cv.yaml (#160, G23); the app reads the file, the page places it.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const NOW = new Date("2026-11-08T10:00:00Z");

// What cv_read.form_data gives for a CV with one station: every CV section, empty ones included.
const fromCv = () => ({
  person: { name: "Erika Beispiel", city: "Bern", email: "erika@example.ch" },
  summary: {},
  work: [{ position: "Software-Entwicklerin", name: "Beispiel AG", startDate: "2019-03", highlights: ["Plattform"] }],
  education: [],
  certificates: [],
  languages: [{ language: "Deutsch", fluency: "Muttersprache" }],
  skills: [],
  interests: { interests: ["Wandern"] },
});

const stored = () => ({
  track: "job",
  data: {
    person: { name: "Alter Name", city: "Thun" },
    summary: { summary: "Ein Satz, der in cv.yaml inzwischen fehlt." },
    work: [
      { position: "Software-Entwicklerin", name: "Beispiel AG", startDate: "2019-03", highlights: ["Plattform"], evidence: "Arbeitszeugnis" },
      { position: "Junior-Entwicklerin", name: "Muster GmbH", startDate: "2015", evidence: "Zeugnis" },
    ],
    searchJob: { home: "Bern", workload: "80 %" },
    style: { tone: "Sachlich und freundlich" },
  },
  suggested: { "work.1": { file: "a.pdf", place: "Seite 1" }, style: { file: "a.pdf", place: "Seite 2" } },
});

test("the CV steps follow cv.yaml, the other steps stay", () => {
  const state = model.fillFromCv(form, stored(), fromCv());

  assert.deepEqual(state.data.person, { name: "Erika Beispiel", city: "Bern", email: "erika@example.ch" });
  assert.deepEqual(state.data.summary, {});
  assert.deepEqual(state.data.interests, { interests: ["Wandern"] });
  assert.deepEqual(state.data.searchJob, { home: "Bern", workload: "80 %" });
  assert.deepEqual(state.data.style, { tone: "Sachlich und freundlich" });
  assert.equal(state.track, "job");
});

test("fields cv.yaml does not hold stay on the matching entry", () => {
  const state = model.fillFromCv(form, stored(), fromCv());

  assert.deepEqual(state.data.work, [
    { position: "Software-Entwicklerin", name: "Beispiel AG", startDate: "2019-03", highlights: ["Plattform"], evidence: "Arbeitszeugnis" },
  ]);
});

test("a form field that cv.yaml holds is marked, and evidence is not", () => {
  const work = form.sections.find((s) => s.id === "work");
  assert.equal(work.cv, true);
  assert.equal(work.fields.find((f) => f.id === "evidence").cv, false);
  assert.deepEqual(form.sections.filter((s) => s.cv).map((s) => s.id),
    ["person", "summary", "work", "education", "certificates", "languages", "skills", "interests"]);
});

test("marks of suggestions in the CV steps go, others stay", () => {
  const state = model.fillFromCv(form, stored(), fromCv());

  assert.deepEqual(state.suggested, { style: { file: "a.pdf", place: "Seite 2" } });
});

test("filling an empty page gives a bundle with the CV's answers", () => {
  const state = model.fillFromCv(form, { track: "job", data: {} }, fromCv());
  const bundle = model.collectBundle(form, state, NOW);

  assert.deepEqual(bundle.data.work, fromCv().work);
  assert.deepEqual(bundle.data.person, fromCv().person);
  assert.equal("summary" in bundle.data, false);
});

test("without a readable CV nothing changes", () => {
  const before = stored();
  for (const cv of [null, undefined, "text", ["work"]]) {
    assert.equal(model.fillFromCv(form, before, cv), before);
  }
});

test("values of the wrong shape from the app are not taken", () => {
  const state = model.fillFromCv(form, { track: "job", data: {} },
    { ...fromCv(), work: [{ position: 3, name: "Beispiel AG", highlights: "Plattform" }], person: ["x"] });

  assert.deepEqual(state.data.work, [{ name: "Beispiel AG" }]);
  assert.deepEqual(state.data.person, {});
});
