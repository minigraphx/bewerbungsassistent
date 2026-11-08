// Projects, teaching, free texts and the website on Meine Angaben (#162, G25, tags per G24).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");
const { validateBundle, describe } = require("../src/validate.js");
const { stepGroups } = require("../src/steps.js");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));
const NOW = new Date("2026-11-08T10:00:00Z");
const page = loadScripts(["validate.js", "model.js", "dom.js"]);
const section = (id) => form.sections.find((s) => s.id === id);
const field = (sectionId, id) => section(sectionId).fields.find((f) => f.id === id);
const plain = (value) => JSON.parse(JSON.stringify(value));
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);

// What cv_read.form_data gives for a CV with projects, teaching, free texts and a website.
const fromCv = () => ({
  person: { name: "Erika Beispiel", city: "Bern", email: "erika@example.ch", url: "www.example.ch" },
  summary: {},
  work: [],
  projects: [{ name: "datenatlas", description: "Offene Verkehrsdaten", tags: ["daten"] }, { name: "Spiel", group: "more" }],
  teaching: [{ position: "Kursleiterin", name: "Volkshochschule Beispiel", startDate: "2020", "x-display": "seit 2020",
    highlights: ["Python", { text: "pandas", tags: ["daten"] }], tags: ["bildung"] }],
  education: [{ text: "Matura, Gymnasium Beispiel, 2010" }],
  certificates: [{ name: "Scrum Master", text: "Scrum Master, 2022" }],
  languages: [],
  skills: [],
  interests: {},
});

test("projects and teaching take the tags field of work, teaching highlights take tags per line", () => {
  for (const id of ["projects", "teaching"]) assert.deepEqual(field(id, "tags"), field("work", "tags"));
  assert.equal(field("teaching", "highlights").tags, true);
  assert.deepEqual(field("projects", "group").options, ["main", "more"]);
});

test("the page opens with projects, teaching, free texts and the website and sends them back", () => {
  const cv = fromCv();
  const state = model.fillFromCv(form, { track: "job", data: {} }, cv);
  const data = model.collectBundle(form, state, NOW).data;

  assert.deepEqual(data.person, cv.person);
  for (const id of ["projects", "teaching", "education", "certificates"]) assert.deepEqual(data[id], cv[id], id);
  assert.deepEqual(validateBundle(form, { ...cases.bases.job, data: { ...cases.bases.job.data, ...data } }), []);
});

test("the apprenticeship track sends no projects, teaching or website", () => {
  const state = model.fillFromCv(form, { track: "apprenticeship", data: {} }, fromCv());
  const data = model.collectBundle(form, state, NOW).data;

  assert.equal("projects" in data || "teaching" in data, false);
  assert.equal("url" in data.person, false);
  assert.deepEqual(data.education, [{ text: "Matura, Gymnasium Beispiel, 2010" }]);
});

test("tags of projects and teaching are offered on every tags field", () => {
  const state = model.fillFromCv(form, { track: "job", data: {} }, fromCv());

  assert.deepEqual(model.knownTags(form, state, []), ["bildung", "daten"]);
});

test("a free text or a display stands in for what it replaces", () => {
  const bundle = structuredClone(cases.bases.job);
  bundle.data.education = [{ text: "Matura" }, {}];
  bundle.data.teaching = [{ position: "Mentorin", name: "Verein Beispiel", "x-display": "gelegentlich" }, { position: "A", name: "B" }];

  const found = validateBundle(form, bundle).map((e) => `${e.path} ${e.code}`).sort();

  assert.deepEqual(found, ["education.1.institution required", "education.1.studyType required", "teaching.1.startDate required"]);
});

test("messages name the new sections and fields", () => {
  assert.equal(describe(form, "job", { path: "projects.0.group", code: "option" }),
    "Projekte, Projekt 1, Gruppe: Bitte einen der vorgeschlagenen Werte wählen.");
  assert.ok(describe(form, "job", { path: "teaching.1.x-display", code: "max" }).startsWith("Lehre und Training, Lehrtätigkeit 2, Anzeige statt Zeitraum: "));
  assert.ok(describe(form, "job", { path: "person.url", code: "format" }).startsWith("Person und Kontakt, Eigene Webseite: "));
});

test("the group shows German names and keeps the values of the file", () => {
  const changes = [];
  const node = page.fieldView(field("projects", "group"), {
    track: "job", value: "more", path: "projects.0.group", onChange: (v) => changes.push(v), onBlur() {},
  });
  const options = byTag(node, "option");

  assert.deepEqual(options.map((o) => [o.value, o.textContent]),
    [["", "– bitte wählen –"], ["main", "Hauptprojekte"], ["more", "Weitere Projekte"]]);
  assert.equal(options.find((o) => o.selected).value, "more");
  const [select] = byTag(node, "select");
  select.onchange({ target: { value: "main" } });
  assert.deepEqual(plain(changes), ["main"]);
});

test("teaching highlights are rows with tags", () => {
  const node = page.fieldView(field("teaching", "highlights"), {
    track: "job", value: ["Python", { text: "pandas", tags: ["daten"] }], path: "teaching.0.highlights",
    tagSuggestions: ["daten"], onChange() {}, onBlur() {},
  });
  const rows = findAll(node, (n) => n.className === "tagged-line");

  assert.deepEqual(rows.map((row) => byTag(row, "input").map((i) => i.value)), [["Python", ""], ["pandas", "daten"]]);
});

test("projects and teaching are in the step of the career, the job track only", () => {
  const job = stepGroups(model.sectionsFor(form, "job"), "job").find((g) => g.id === "career");
  const apprenticeship = stepGroups(model.sectionsFor(form, "apprenticeship"), "apprenticeship").find((g) => g.id === "career");

  assert.deepEqual(job.sections.map((s) => s.id), ["work", "teaching", "projects", "education", "certificates"]);
  assert.deepEqual(apprenticeship.sections.map((s) => s.id), ["education", "work", "certificates"]);
});
