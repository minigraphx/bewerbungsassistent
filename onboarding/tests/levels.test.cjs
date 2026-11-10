// Levels on Meine Angaben (#123, G20): each keyword line takes an optional level, languages an optional x-level.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");
const { validateBundle } = require("../src/validate.js");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));
const NOW = new Date("2026-11-10T10:00:00Z");
const page = loadScripts(["validate.js", "model.js", "dom.js"]);
const field = (sectionId, id) => form.sections.find((s) => s.id === sectionId).fields.find((f) => f.id === id);
const plain = (value) => JSON.parse(JSON.stringify(value));
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const rows = (node) => findAll(node, (n) => n.className === "tagged-line");

function keywordsView(value, changes) {
  return page.fieldView(field("skills", "keywords"), {
    track: "job", value, path: "skills.0.keywords", onChange: (v) => changes.push(v), onBlur() {},
  });
}

function choose(select, value) {
  select.value = value;
  select.onchange({ target: select });
}

test("the shared cases cover levels", () => {
  assert.ok(cases.cases.some((c) => c.name.includes("#123")));
});

test("the bundle keeps a level, an empty one included, and leaves plain lines as text", () => {
  const state = {
    track: "job",
    data: { skills: [{ name: "Programme", keywords: [" SQL ", { text: " Python ", level: "4" }, { text: "Git", level: "" }, { text: " ", level: "2" }] }] },
  };

  const [skill] = model.collectBundle(form, state, NOW).data.skills;

  assert.deepEqual(skill.keywords, ["SQL", { text: "Python", level: "4" }, { text: "Git", level: "" }]);
});

test("a bundle with levels passes, a level outside 1 to 6 does not", () => {
  const state = {
    track: "job",
    data: { skills: [{ name: "Programme", keywords: [{ text: "Python", level: "6" }] }],
      languages: [{ language: "Deutsch", fluency: "Muttersprache", "x-level": "C2" }] },
  };
  const bundle = model.collectBundle(form, state, NOW);
  const errors = validateBundle(form, bundle).filter((e) => /skills|languages/.test(e.path));
  assert.deepEqual(errors, []);

  bundle.data.skills[0].keywords[0].level = "0";
  assert.deepEqual(validateBundle(form, bundle).filter((e) => /skills/.test(e.path)), [{ path: "skills.0.keywords.0.level", code: "option" }]);
});

test("each keyword row has its text and an optional level, without a preset", () => {
  const node = keywordsView(["SQL", { text: "Python", level: "5" }], []);
  const [first, second] = rows(node);

  assert.equal(rows(node).length, 2);
  const select = byTag(first, "select")[0];
  assert.deepEqual(byTag(select, "option").map((o) => o.value), ["", "1", "2", "3", "4", "5", "6"]);
  assert.equal(byTag(select, "option")[0].textContent, "ohne Stufe");
  const chosen = (row) => byTag(row, "option").filter((o) => o.selected).map((o) => o.value);
  assert.deepEqual(chosen(first), [""]);
  assert.deepEqual(chosen(second), ["5"]);
  assert.match(select["aria-label"] || select.getAttribute?.("aria-label") || "", /Stufe zu Zeile 1/);
});

test("choosing a level sets it, ohne Stufe clears it, typing keeps it", () => {
  const changes = [];
  const node = keywordsView(["SQL", { text: "Python", level: "5" }], changes);
  const [first, second] = rows(node);

  choose(byTag(first, "select")[0], "3");
  assert.deepEqual(plain(changes.at(-1)), [{ text: "SQL", level: "3" }, { text: "Python", level: "5" }]);

  choose(byTag(second, "select")[0], "");
  assert.deepEqual(plain(changes.at(-1)), [{ text: "SQL", level: "3" }, { text: "Python", level: "" }]);

  const input = byTag(first, "input")[0];
  input.value = "SQL und dbt";
  input.oninput({ target: input });
  assert.deepEqual(plain(changes.at(-1)), [{ text: "SQL und dbt", level: "3" }, { text: "Python", level: "" }]);
});

test("languages offer an optional level from A1 to C2", () => {
  const node = page.fieldView(field("languages", "x-level"), {
    track: "job", value: "", path: "languages.0.x-level", onChange() {}, onBlur() {},
  });

  assert.deepEqual(byTag(node, "option").map((o) => o.value), ["", "A1", "A2", "B1", "B2", "C1", "C2"]);
  assert.equal(byTag(node, "option")[0].textContent, "ohne Stufe");
});
