// Pure state handling of the template: building the saved bundle and reading one back.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");
const { validateBundle } = require("../src/validate.js");

const root = path.join(__dirname, "..");
const form = JSON.parse(fs.readFileSync(path.join(root, "form.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));
const NOW = new Date("2026-11-02T10:00:00Z");

test("a saved bundle of the example is valid and round-trips", () => {
  for (const track of ["job", "apprenticeship"]) {
    const state = model.stateFromBundle(form, cases.bases[track]);
    const bundle = model.collectBundle(form, state, NOW);
    assert.deepEqual(validateBundle(form, bundle), []);
    const expected = structuredClone(cases.bases[track].data);
    if (track === "job") delete expected.work[0].endDate; // blank values are not saved
    assert.deepEqual(bundle.data, expected);
    assert.equal(bundle.saved, "2026-11-02T10:00:00.000Z");
  }
});

test("collecting keeps only the current track", () => {
  const state = {
    track: "apprenticeship",
    data: { person: { name: "Lea", label: "Titel" }, searchJob: { home: "Bern" }, summary: { summary: "x" } },
  };
  const bundle = model.collectBundle(form, state, NOW);
  assert.deepEqual(bundle.data, { person: { name: "Lea" } });
});

test("collecting drops empty repeated items, blank list lines and blank fields", () => {
  const state = {
    track: "job",
    data: {
      work: [{ position: "", name: " " }, { position: "Entwicklerin", name: "Beispiel AG", startDate: "2019", highlights: ["", "A", "  "] }],
      person: { name: "Erika", phone: "" },
    },
  };
  const bundle = model.collectBundle(form, state, NOW);
  assert.deepEqual(bundle.data.work, [{ position: "Entwicklerin", name: "Beispiel AG", startDate: "2019", highlights: ["A"] }]);
  assert.deepEqual(bundle.data.person, { name: "Erika" });
});

test("reading a bundle ignores unknown sections, fields and wrong types", () => {
  const state = model.stateFromBundle(form, {
    format: form.format, version: 1, track: "job",
    data: { person: { name: "Erika", evil: "x", phone: 42 }, other: {}, work: "nope", skills: [{ keywords: "Python" }] },
  });
  assert.deepEqual(state.data.person, { name: "Erika" });
  assert.equal(state.data.other, undefined);
  assert.equal(state.data.work, undefined);
  assert.deepEqual(state.data.skills, [{}]);
});

test("reading something that is not a bundle of this version throws a German message", () => {
  assert.throws(() => model.stateFromBundle(form, { format: "x" }), model.BundleError);
  assert.throws(() => model.stateFromBundle(form, { format: form.format, version: 1, track: ["job"], data: {} }), /keine Einstiegsdatei/);
  assert.throws(() => model.stateFromBundle(form, { format: form.format, version: 1, track: "uni", data: {} }), /keine Einstiegsdatei/);
});

test("setting a value returns a new state and leaves the old one unchanged", () => {
  const before = { track: "job", data: { work: [{ position: "A" }] } };
  const after = model.setValue(before, ["work", 0, "position"], "B");
  assert.equal(before.data.work[0].position, "A");
  assert.equal(after.data.work[0].position, "B");
  const created = model.setValue(before, ["person", "name"], "Erika");
  assert.deepEqual(created.data.person, { name: "Erika" });
  assert.equal(before.data.person, undefined);
});

test("adding and removing repeated items is immutable", () => {
  const before = { track: "job", data: { work: [{ position: "A" }, { position: "B" }] } };
  const added = model.addItem(before, "work");
  const removed = model.removeItem(added, "work", 0);
  assert.equal(before.data.work.length, 2);
  assert.equal(added.data.work.length, 3);
  assert.deepEqual(removed.data.work, [{ position: "B" }, {}]);
});

test("list fields convert to and from text lines", () => {
  assert.deepEqual(model.linesToList("Python\n\nSQL\n"), ["Python", "", "SQL", ""]);
  assert.equal(model.listToLines(["Python", "SQL"]), "Python\nSQL");
  assert.equal(model.listToLines(undefined), "");
});

test("sections and fields for a track", () => {
  const ids = model.sectionsFor(form, "apprenticeship").map((s) => s.id);
  assert.ok(ids.includes("searchApprenticeship"));
  assert.ok(!ids.includes("searchJob"));
  const person = form.sections.find((s) => s.id === "person");
  assert.ok(!model.fieldsFor(person, "apprenticeship").some((f) => f.id === "label"));
});

test("the draft bundle keeps item positions and blank items are recognised", () => {
  const state = { track: "job", data: { work: [{ position: " " }, { position: "A", highlights: [""] }] } };
  const draft = model.draftBundle(form, state);
  assert.equal(draft.data.work.length, 2);
  assert.equal(model.isBlankItem(state.data.work[0]), true);
  assert.equal(model.isBlankItem({ highlights: ["", " "] }), true);
  assert.equal(model.isBlankItem(state.data.work[1]), false);
});
