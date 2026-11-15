// Keywords and interests take two languages on Meine Angaben (#299, G30), like the other values since #181: a line
// in German and English has an input per language, a plain one can get English. All data is invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");
const { fieldRules } = require("../src/validate.js");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const NOW = new Date("2026-11-15T10:00:00Z");
const page = loadScripts(["validate.js", "model.js", "dom.js"]);
const section = (id) => form.sections.find((s) => s.id === id);
const field = (sectionId, id) => section(sectionId).fields.find((f) => f.id === id);
const plain = (value) => JSON.parse(JSON.stringify(value));
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const byClass = (node, name) => findAll(node, (n) => String(n.className || "").split(" ").includes(name));
const buttonNamed = (node, pattern) => byTag(node, "button").find((b) => pattern.test(b.getAttribute("aria-label") || b.textContent));

const ACCOUNTING = { de: "Buchhaltung", en: "Accounting" };
const PAYROLL = { text: { de: "Lohnwesen", en: "Payroll" }, level: "4" };
const HIKING = { de: "Wandern", en: "Hiking" };

function view(sectionId, id, value, changes) {
  const rules = fieldRules(form, section(sectionId), field(sectionId, id));
  return page.fieldView(rules, {
    track: "job", value, path: `${sectionId}.0.${id}`, onChange: (v) => changes.push(plain(v)), onBlur: () => {},
  });
}

test("a two-language keyword shows an input per language and keeps its level", () => {
  const changes = [];
  const shown = view("skills", "keywords", [ACCOUNTING, PAYROLL, "Excel"], changes);
  const rows = byClass(shown, "tagged-line");

  const [german, english] = byTag(rows[1], "input");
  const [level] = byTag(rows[1], "select");
  assert.equal(german.value, "Lohnwesen");
  assert.equal(english.value, "Payroll");
  assert.match(english.getAttribute("aria-label"), /Englisch/);
  assert.equal(byTag(level, "option").find((o) => o.selected).value, "4");

  english.oninput({ target: { value: "Payroll accounting" } });
  assert.deepEqual(changes.at(-1)[1], { text: { de: "Lohnwesen", en: "Payroll accounting" }, level: "4" });
  assert.deepEqual(changes.at(-1)[0], ACCOUNTING);
  byTag(rows[0], "input")[1].oninput({ target: { value: "Bookkeeping" } });
  assert.deepEqual(changes.at(-1)[0], { text: { de: "Buchhaltung", en: "Bookkeeping" }, level: "" });
});

test("a plain keyword can get English and drop it again", () => {
  const changes = [];
  const shown = view("skills", "keywords", ["Excel"], changes);

  buttonNamed(shown, /Zeile 1 auf Englisch ergänzen/).click();
  const [, english] = byTag(byClass(shown, "tagged-line")[0], "input");
  english.oninput({ target: { value: "Excel spreadsheets" } });
  assert.deepEqual(changes.at(-1), [{ text: { de: "Excel", en: "Excel spreadsheets" }, level: "" }]);

  buttonNamed(shown, /Englisch aus Zeile 1 entfernen/).click();
  assert.deepEqual(changes.at(-1), [{ text: "Excel", level: "" }]);
});

test("interests show a row per line, with an input per language for a two-language one", () => {
  const changes = [];
  const shown = view("interests", "interests", [HIKING, "Lesen"], changes);
  const rows = byClass(shown, "tagged-line");

  const [german, english] = byTag(rows[0], "input");
  assert.equal(german.value, "Wandern");
  assert.equal(english.value, "Hiking");
  english.oninput({ target: { value: "Hiking trips" } });
  assert.deepEqual(changes.at(-1), [{ de: "Wandern", en: "Hiking trips" }, "Lesen"]);

  byTag(rows[1], "input")[0].oninput({ target: { value: "Lesen und Schreiben" } });
  assert.deepEqual(changes.at(-1), [{ de: "Wandern", en: "Hiking trips" }, "Lesen und Schreiben"]);
});

test("a plain interest can get English", () => {
  const changes = [];
  const shown = view("interests", "interests", ["Lesen"], changes);

  buttonNamed(shown, /Zeile 1 auf Englisch ergänzen/).click();
  const [, english] = byTag(byClass(shown, "tagged-line")[0], "input");
  english.oninput({ target: { value: "Reading" } });

  assert.deepEqual(changes.at(-1), [{ de: "Lesen", en: "Reading" }]);
});

test("two-language keywords and interests go out trimmed, and an empty one counts as blank", () => {
  const state = { track: "job", data: {
    skills: [{ name: "Finanzen", keywords: [{ text: { de: " Lohnwesen ", en: "" }, level: "4" }, { de: "Buchhaltung", en: " Accounting " },
      { text: { de: " ", en: "" }, level: "" }] }],
    interests: { interests: [{ de: " Wandern", en: "Hiking " }, { de: "", en: " " }, " Lesen "] },
  } };

  const data = model.collectBundle(form, state, NOW).data;

  assert.deepEqual(data.skills, [{ name: "Finanzen", keywords: [{ text: { de: "Lohnwesen" }, level: "4" }, ACCOUNTING] }]);
  assert.deepEqual(data.interests, { interests: [HIKING, "Lesen"] });
});

test("the page opens on two-language keywords and interests read from cv.yaml", () => {
  const cv = { skills: [{ name: "Finanzen", keywords: [ACCOUNTING, PAYROLL, "Excel"] }], interests: { interests: [HIKING, "Lesen"] } };

  const state = model.fillFromCv(form, { track: "job", data: {} }, cv);

  assert.deepEqual(state.data.skills, cv.skills);
  assert.deepEqual(state.data.interests, cv.interests);
});
