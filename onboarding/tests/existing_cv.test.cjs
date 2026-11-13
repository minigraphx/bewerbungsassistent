// An existing cv.yaml the form's rules do not accept still opens and saves on Meine Angaben (#167, G23). All data is
// invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");
const { validateBundle } = require("../src/validate.js");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const NOW = new Date("2026-11-09T10:00:00Z");
const page = loadScripts(["validate.js", "model.js", "dom.js"]);
const field = (sectionId, id) => form.sections.find((s) => s.id === sectionId).fields.find((f) => f.id === id);
const plain = (value) => JSON.parse(JSON.stringify(value));
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const textOf = (node) => node.textContent;

const POSITION = { de: "Software-Entwicklerin", en: "Software developer" };
const LINE = { de: "Aufbau von Datenpipelines", en: "Built data pipelines" };
const TAGGED = { text: { de: "Schulungen intern", en: "Internal training" }, tags: ["bildung"] };

// What cv_read.form_data gives for a CV written by hand: every CV section, empty ones included.
const fromCv = () => ({
  person: { name: "Erika Beispiel", email: "erika@example.ch", city: "Bern" },
  summary: { summary: { de: "Entwicklerin mit Praxis.", en: "Developer with experience." } },
  work: [
    { position: POSITION, name: "Beispiel AG", startDate: "2022-06-01", endDate: "2023-01-15",
      highlights: [LINE, TAGGED, "Wartung der Plattform"] },
    { position: "Junior-Entwicklerin", name: "Muster GmbH" },
  ],
  teaching: [], projects: [], education: [], certificates: [],
  languages: [{ language: "Englisch", fluency: "fliessend" }],
  skills: [], interests: {},
});

const opened = () => model.fillFromCv(form, { track: "job", data: {} }, fromCv());

test("two-language values come into the page and go back as they are", () => {
  const data = model.collectBundle(form, opened(), NOW).data;

  assert.deepEqual(data.summary, fromCv().summary);
  assert.deepEqual(data.work[0].position, POSITION);
  assert.deepEqual(data.work[0].highlights, [LINE, TAGGED, "Wartung der Plattform"]);
});

test("the CV as opened passes against the CV, and without it fails only where the file misses a value", () => {
  const bundle = model.collectBundle(form, opened(), NOW);
  const cvSections = ["person", "summary", "work", "languages"];
  const only = { ...bundle, data: Object.fromEntries(cvSections.map((id) => [id, bundle.data[id]])) };
  const cvErrors = (errors) => errors.filter((e) => cvSections.includes(e.path.split(".")[0]));

  assert.deepEqual(cvErrors(validateBundle(form, only, [], fromCv())), []);
  // since G30 (#181) the rules take two languages, full dates and a fluency in own words
  assert.deepEqual(cvErrors(validateBundle(form, only, [])).map((e) => `${e.path}|${e.code}`).sort(), [
    "work.1.startDate|required",
  ]);
});

test("changing one field of an entry keeps its other values from the CV passing", () => {
  const state = model.setValue(opened(), ["work", 0, "name"], "Beispiel Software AG");
  const bundle = model.collectBundle(form, state, NOW);

  const errors = validateBundle(form, bundle, [], fromCv()).filter((e) => e.path.startsWith("work."));

  assert.deepEqual(errors, []);
});

// Since G30 (#181) the page edits both languages; full_cv_edit.test.cjs tests that in detail.
test("a two-language value shows both languages to edit", () => {
  const view = page.fieldView(field("work", "position"), { track: "job", value: POSITION, path: "work.0.position", onChange: () => {}, onBlur: () => {} });

  assert.deepEqual(byTag(view, "input").map((input) => input.value), ["Software-Entwicklerin", "Software developer"]);
  assert.doesNotMatch(textOf(view), /nicht änderbar/);
});

test("editing one language of a two-language value keeps the other", () => {
  const changes = [];
  const view = page.fieldView(field("summary", "summary"), {
    track: "job", value: fromCv().summary.summary, path: "summary.summary", onChange: (v) => changes.push(plain(v)), onBlur: () => {},
  });
  const [german] = byTag(view, "textarea");

  german.oninput({ target: { value: "Neuer Satz." } });

  assert.deepEqual(changes, [{ de: "Neuer Satz.", en: "Developer with experience." }]);
});

test("a two-language highlight shows both languages and keeps its tags when its text changes", () => {
  const changes = [];
  const view = page.fieldView(field("work", "highlights"), {
    track: "job", value: [LINE, TAGGED, "Wartung der Plattform"], path: "work.0.highlights",
    onChange: (v) => changes.push(plain(v)), onBlur: () => {},
  });

  const rows = findAll(view, (n) => n.className === "tagged-line");
  const [german, english, tags] = byTag(rows[1], "input");
  assert.equal(english.value, "Internal training");
  assert.notEqual(tags.disabled, true);

  german.oninput({ target: { value: "Schulungen für das Team" } });
  assert.deepEqual(changes.at(-1)[1], { text: { de: "Schulungen für das Team", en: "Internal training" }, tags: ["bildung"] });
  assert.deepEqual(changes.at(-1)[0], LINE);
});

test("a fluency outside the suggestions is shown as it is", () => {
  const view = page.fieldView(field("languages", "fluency"), { track: "job", value: "fliessend", path: "languages.0.fluency", onChange: () => {}, onBlur: () => {} });

  assert.equal(byTag(view, "input")[0].value, "fliessend");
});

test("an entry with only two-language values is not blank", () => {
  assert.equal(model.isBlankItem({ position: POSITION }), false);
  assert.equal(model.isBlankItem({ highlights: [LINE] }), false);
});

// The page scripts are inlined into one script: a name declared twice stops the whole page, which tests that load
// the files one by one do not notice.
test("each built page compiles its inlined scripts as one script", () => {
  const vm = require("node:vm");
  const pages = [path.join(__dirname, "..", "dist", "einstieg.html"), path.join(__dirname, "..", "..", "bewerbungen", "seiten", "angaben.html")];
  for (const page of pages) {
    const html = fs.readFileSync(page, "utf8");
    const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
    assert.ok(inline.length > 0, page);
    for (const code of inline) assert.doesNotThrow(() => new vm.Script(code), page);
  }
});
