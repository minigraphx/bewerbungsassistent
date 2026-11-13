// Tags on Meine Angaben (#161, G24): entries and highlights take tags, suggestions come from the app.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");
const { validateBundle, describe } = require("../src/validate.js");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));
const NOW = new Date("2026-11-08T10:00:00Z");
const page = loadScripts(["validate.js", "model.js", "dom.js"]);
const section = (id) => form.sections.find((s) => s.id === id);
const field = (sectionId, id) => section(sectionId).fields.find((f) => f.id === id);

// Values made inside the page's sandbox have its own prototypes; compare them as plain data.
const plain = (value) => JSON.parse(JSON.stringify(value));
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const optionValues = (node) => byTag(node, "option").map((o) => o.value);

function typeInto(input, value) {
  input.value = value;
  input.oninput({ target: input });
}

test("work entries, skills and certificates have a tags field, highlights take tags per line", () => {
  for (const id of ["work", "skills", "certificates"]) assert.equal(field(id, "tags").type, "tags");
  assert.equal(field("work", "highlights").tags, true);
  assert.equal(field("skills", "keywords").tags, undefined);
});

test("tags are typed with commas and read back as a list", () => {
  assert.deepEqual(model.parseTags(" web, daten ,, ki ,"), ["web", "daten", "ki"]);
  assert.deepEqual(model.parseTags(""), []);
  assert.equal(model.tagsToText(["web", "daten"]), "web, daten");
  assert.equal(model.tagsToText(undefined), "");
});

test("the bundle keeps tags trimmed and an edited line with its tags, even none", () => {
  const state = {
    track: "job",
    data: {
      work: [{
        position: "Entwicklerin", name: "Beispiel AG", startDate: "2019", tags: [" web ", "", "daten"],
        highlights: ["Plattform", { text: " Pipelines ", tags: ["daten", " "] }, { text: "Ohne", tags: [] }, { text: " ", tags: ["x"] }],
      }],
    },
  };

  const [work] = model.collectBundle(form, state, NOW).data.work;

  assert.deepEqual(work.tags, ["web", "daten"]);
  assert.deepEqual(work.highlights, ["Plattform", { text: "Pipelines", tags: ["daten"] }, { text: "Ohne", tags: [] }]);
});

test("lines of the wrong shape are not taken from a loaded file", () => {
  const state = model.stateFromBundle(form, {
    format: form.format, version: form.version, track: "job",
    data: { work: [{ position: "A", tags: ["web", 3], highlights: [{ text: "Gut", tags: ["x", 4] }, { text: 5 }, { tags: ["x"] }, 7] }],
      skills: [{ name: "Daten", keywords: ["Python", { text: "SQL", tags: ["daten"] }] }] },
  });

  assert.deepEqual(state.data.work[0].tags, ["web"]);
  assert.deepEqual(state.data.work[0].highlights, [{ text: "Gut", tags: ["x"] }]);
  assert.deepEqual(state.data.skills[0].keywords, ["Python"]);
});

test("a station with only an empty tagged line is blank, one with tags is not", () => {
  assert.equal(model.isBlankItem({ highlights: [{ text: " ", tags: [] }] }), true);
  assert.equal(model.isBlankItem({ tags: ["daten"] }), false);
});

test("the page opens with the tags of cv.yaml and keeps them in the bundle", () => {
  const cv = {
    work: [{ position: "Entwicklerin", name: "Beispiel AG", startDate: "2019-03", tags: ["web", "daten"],
      highlights: ["Plattform", { text: "Pipelines", tags: ["daten"] }] }],
    skills: [{ name: "Daten", keywords: ["pandas"], tags: ["daten"] }],
    certificates: [{ name: "Kurs", tags: ["ki"] }],
  };

  const state = model.fillFromCv(form, { track: "job", data: {} }, cv);
  const data = model.collectBundle(form, state, NOW).data;

  assert.deepEqual(data.work, cv.work);
  assert.deepEqual(data.skills, cv.skills);
  assert.deepEqual(data.certificates, cv.certificates);
});

test("a field only the form holds stays on a station with tags", () => {
  const stored = { track: "job", data: { work: [{ position: "A", name: "B", startDate: "2019", tags: ["alt"], evidence: "Zeugnis" }] } };
  const state = model.fillFromCv(form, stored, { work: [{ position: "A", name: "B", startDate: "2019", tags: ["alt"] }] });

  assert.equal(state.data.work[0].evidence, "Zeugnis");
});

// G23: what the form does not send stays in cv.yaml. A missing tags key keeps the tags of the file, an empty list
// removes them; so the page sends the key wherever the person changed tags, and leaves it out where it never knew them.

test("the bundle sends the tags an entry has on the page, an empty list included, and leaves out unknown ones", () => {
  const state = { track: "job", data: { certificates: [{ name: "Kurs", tags: [] }, { name: "Alt" }, { name: "Neu", tags: [" ki "] }] } };

  const data = model.collectBundle(form, state, NOW).data;

  assert.deepEqual(data.certificates, [{ name: "Kurs", tags: [] }, { name: "Alt" }, { name: "Neu", tags: ["ki"] }]);
});

test("an entry with nothing but an empty list of tags is blank and not sent", () => {
  const state = { track: "job", data: { certificates: [{ tags: [] }, { name: "Kurs" }], work: [{ highlights: [{ text: " ", tags: [] }], tags: [] }] } };

  assert.equal(model.isBlankItem({ tags: [] }), true);
  const data = model.collectBundle(form, state, NOW).data;
  assert.deepEqual(data.certificates, [{ name: "Kurs" }]);
  assert.equal("work" in data, false);
});

test("removing a tag on the page sends an empty list for the entry and for the line", () => {
  const cv = { certificates: [{ name: "Kurs", tags: ["ki"] }],
    work: [{ position: "A", name: "B", startDate: "2019", highlights: [{ text: "Pipelines", tags: ["daten"] }] }] };
  let state = model.fillFromCv(form, { track: "job", data: {} }, cv);

  state = model.setValue(state, ["certificates", 0, "tags"], model.parseTags(""));
  state = model.setValue(state, ["work", 0, "highlights"], [model.taggedLine("Pipelines", [])]);
  const data = model.collectBundle(form, state, NOW).data;

  assert.deepEqual(data.certificates, [{ name: "Kurs", tags: [] }]);
  assert.deepEqual(data.work[0].highlights, [{ text: "Pipelines", tags: [] }]);
  assert.deepEqual(validateBundle(form, { ...cases.bases.job, data: { ...cases.bases.job.data, ...data } }), []);
});

test("suggestions are the tags of the app and those already typed, each once and sorted", () => {
  const state = { track: "job", data: { work: [{ tags: ["web", "Daten"], highlights: ["x", { text: "y", tags: ["neu"] }] }],
    certificates: [{ tags: ["ki"] }] } };

  const long = "x".repeat(form.limits.tag + 1);
  assert.deepEqual(model.knownTags(form, state, ["daten", "web", 5, "zwei Wörter", "a,b", "a\tb", long]),
    ["Daten", "daten", "ki", "neu", "web", long, "zwei Wörter"]);
  assert.deepEqual(model.knownTags(form, { track: "job", data: {} }, undefined), []);
});

test("the shared cases cover tags", () => {
  assert.ok(cases.cases.filter((c) => c.name.includes("tag")).length >= 10);
});

test("tags already in the data folder pass beyond the limits, typed ones do not", () => {
  const bundle = structuredClone(cases.bases.job);
  const many = Array.from({ length: 12 }, (_, i) => `thema ${i + 1}`);
  bundle.data.work[0].tags = many;
  bundle.data.work[0].highlights[0] = { text: "Modelle", tags: ["machine learning", "x".repeat(41)] };

  assert.deepEqual(validateBundle(form, bundle, [...many, "machine learning", "x".repeat(41)]), []);
  assert.deepEqual(validateBundle(form, bundle, many).map((e) => `${e.path} ${e.code}`), ["work.0.highlights.0.tags.1 max"]);
  assert.deepEqual(validateBundle(form, bundle).map((e) => `${e.path} ${e.code}`).sort(),
    ["work.0.highlights.0.tags.1 max", "work.0.tags maxItems"]);
});

test("messages about tags name the tag and its limits", () => {
  assert.equal(describe(form, "job", { path: "work.0.tags.2", code: "max" }),
    "Berufliche Stationen, Station 1, Tags, Tag 3: Zu lang (höchstens 40 Zeichen).");
  const line = describe(form, "job", { path: "work.0.highlights.1.tags.0", code: "format" });
  assert.ok(line.startsWith("Berufliche Stationen, Station 1, Tätigkeiten und Erfolge, Zeile 2, Tags, Tag 1: "), line);
  assert.ok(line.endsWith("daten."), line);
  assert.ok(describe(form, "job", { path: "work.0.highlights.1.tags", code: "maxItems" }).endsWith("(höchstens 10)."));
});

test("a valid bundle with tags passes", () => {
  const bundle = structuredClone(cases.bases.job);
  bundle.data.work[0].tags = ["web"];
  bundle.data.work[0].highlights[0] = { text: "Plattform", tags: ["web"] };
  assert.deepEqual(validateBundle(form, bundle), []);
});

function tagsView(value, suggestions, changes) {
  return page.fieldView(field("work", "tags"), {
    track: "job", value, path: "work.0.tags", tagSuggestions: suggestions,
    onChange: (v) => changes.push(v), onBlur() {},
  });
}

test("the tags field shows the tags and offers the suggestions", () => {
  const node = tagsView(["web"], ["daten", "web"], []);
  const [input] = byTag(node, "input");
  const [list] = byTag(node, "datalist");

  assert.equal(input.value, "web");
  assert.equal(input.list, undefined);
  assert.equal(input.getAttribute("list"), list.id);
  assert.deepEqual(optionValues(list), ["web, daten"]);
});

test("typing in the tags field gives the list and completes the last tag", () => {
  const changes = [];
  const node = tagsView([], ["daten", "design", "web"], changes);
  const [input] = byTag(node, "input");
  const [list] = byTag(node, "datalist");

  typeInto(input, "web, d");

  assert.deepEqual(plain(changes.at(-1)), ["web", "d"]);
  assert.deepEqual(optionValues(list), ["web, daten", "web, design"]);
});

function linesView(value, changes) {
  return page.fieldView(field("work", "highlights"), {
    track: "job", value, path: "work.0.highlights", tagSuggestions: ["daten"],
    onChange: (v) => changes.push(v), onBlur() {},
  });
}

const lineRows = (node) => findAll(node, (n) => n.className === "tagged-line");

test("highlights show one row per line with its tags, and an empty row to begin with", () => {
  const node = linesView(["Plattform", { text: "Pipelines", tags: ["daten"] }], []);
  const rows = lineRows(node);

  assert.equal(rows.length, 2);
  assert.deepEqual(rows.map((row) => byTag(row, "input").map((i) => i.value)), [["Plattform", ""], ["Pipelines", "daten"]]);
  assert.equal(lineRows(linesView(undefined, [])).length, 1);
});

test("editing a row changes its line, tags make it text and tags", () => {
  const changes = [];
  const node = linesView(["Plattform", { text: "Pipelines", tags: ["daten"] }], changes);
  const [first, second] = lineRows(node);

  typeInto(byTag(first, "input")[1], "web");
  assert.deepEqual(plain(changes.at(-1)), [{ text: "Plattform", tags: ["web"] }, { text: "Pipelines", tags: ["daten"] }]);

  typeInto(byTag(second, "input")[0], "Pipelines mit dbt");
  assert.deepEqual(plain(changes.at(-1)), [{ text: "Plattform", tags: ["web"] }, { text: "Pipelines mit dbt", tags: ["daten"] }]);

  typeInto(byTag(second, "input")[1], "");
  assert.deepEqual(plain(changes.at(-1)), [{ text: "Plattform", tags: ["web"] }, { text: "Pipelines mit dbt", tags: [] }]);
});

test("rows are added up to the limit and removed with their tags", () => {
  const changes = [];
  const node = linesView(["Eins", { text: "Zwei", tags: ["daten"] }], changes);
  const add = findAll(node, (n) => n.tagName === "button" && n.className === "add-line")[0];

  add.click();
  assert.equal(lineRows(node).length, 3);
  assert.deepEqual(plain(changes.at(-1)), ["Eins", { text: "Zwei", tags: ["daten"] }, ""]);

  const remove = findAll(lineRows(node)[1], (n) => n.tagName === "button" && n.className === "remove-line")[0];
  remove.click();
  assert.equal(lineRows(node).length, 2);
  assert.deepEqual(plain(changes.at(-1)), ["Eins", ""]);

  const full = linesView(Array.from({ length: field("work", "highlights").maxItems }, (_, i) => `Zeile ${i}`), []);
  assert.equal(findAll(full, (n) => n.className === "add-line").length, 0);
});
