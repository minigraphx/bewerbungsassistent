// Meine Angaben edits and adds every value an existing cv.yaml holds (#181, G30): two-language values, full dates,
// long texts, more entries, a station with its display only and a fluency in own words. All data is invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const model = require("../src/model.js");
const { validateBundle, fieldRules, entryLimit } = require("../src/validate.js");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));
const NOW = new Date("2026-11-13T10:00:00Z");
const page = loadScripts(["validate.js", "model.js", "dom.js"]);
const section = (id) => form.sections.find((s) => s.id === id);
const field = (sectionId, id) => section(sectionId).fields.find((f) => f.id === id);
const plain = (value) => JSON.parse(JSON.stringify(value));
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const byClass = (node, name) => findAll(node, (n) => String(n.className || "").split(" ").includes(name));
const buttonNamed = (node, pattern) => byTag(node, "button").find((b) => pattern.test(b.getAttribute("aria-label") || b.textContent));

const POSITION = { de: "Software-Entwicklerin", en: "Software developer" };
const LINE = { de: "Aufbau von Datenpipelines", en: "Built data pipelines" };
const TAGGED = { text: { de: "Schulungen intern", en: "Internal training" }, tags: ["bildung"] };

function view(sectionId, id, value, changes) {
  const rules = fieldRules(form, section(sectionId), field(sectionId, id));
  return page.fieldView(rules, {
    track: "job", value, path: `${sectionId}.0.${id}`, onChange: (v) => changes.push(plain(v)), onBlur: () => {},
  });
}

test("a two-language value shows one input per language, and each edit keeps both", () => {
  const changes = [];
  const shown = view("work", "position", POSITION, changes);

  const [german, english] = byTag(shown, "input");
  assert.equal(german.value, "Software-Entwicklerin");
  assert.equal(english.value, "Software developer");
  assert.match(german.getAttribute("aria-label"), /Deutsch/);
  assert.match(english.getAttribute("aria-label"), /Englisch/);

  english.oninput({ target: { value: "Senior developer" } });
  german.oninput({ target: { value: "Senior-Entwicklerin" } });
  assert.deepEqual(changes, [{ de: "Software-Entwicklerin", en: "Senior developer" }, { de: "Senior-Entwicklerin", en: "Senior developer" }]);
});

test("a plain text can get an English version, and a two-language one can drop it", () => {
  const changes = [];
  const shown = view("summary", "summary", "Entwicklerin mit Praxis.", changes);

  buttonNamed(shown, /Englisch ergänzen/).click();
  assert.deepEqual(changes.at(-1), { de: "Entwicklerin mit Praxis.", en: "" });
  const english = byTag(shown, "textarea")[1];
  english.oninput({ target: { value: "Developer with experience." } });
  assert.deepEqual(changes.at(-1), { de: "Entwicklerin mit Praxis.", en: "Developer with experience." });

  buttonNamed(shown, /Englisch entfernen/).click();
  assert.deepEqual(changes.at(-1), "Entwicklerin mit Praxis.");
  assert.equal(byTag(shown, "textarea").length, 1);
});

test("only fields of the CV offer a second language, and the name only edits one it has", () => {
  assert.ok(buttonNamed(view("work", "location", "Bern", []), /Englisch ergänzen/));
  assert.equal(buttonNamed(view("person", "name", "Erika Beispiel", []), /Englisch ergänzen/), undefined);
  assert.equal(buttonNamed(view("person", "email", "erika@example.ch", []), /Englisch ergänzen/), undefined);
  assert.equal(byTag(view("person", "name", { de: "Erika", en: "Erika" }, []), "input").length, 2);
});

test("a two-language highlight is edited in both languages and keeps its tags editable", () => {
  const changes = [];
  const shown = view("work", "highlights", [LINE, TAGGED, "Wartung der Plattform"], changes);
  const rows = byClass(shown, "tagged-line");

  const [german, english, tags] = byTag(rows[1], "input");
  assert.equal(german.value, "Schulungen intern");
  assert.equal(english.value, "Internal training");
  assert.notEqual(tags.disabled, true);

  english.oninput({ target: { value: "Team training" } });
  assert.deepEqual(changes.at(-1)[1], { text: { de: "Schulungen intern", en: "Team training" }, tags: ["bildung"] });
  tags.oninput({ target: { value: "bildung, team" } });
  assert.deepEqual(changes.at(-1)[1], { text: { de: "Schulungen intern", en: "Team training" }, tags: ["bildung", "team"] });
  assert.deepEqual(changes.at(-1)[0], LINE);
});

test("a plain highlight can get an English version", () => {
  const changes = [];
  const shown = view("work", "highlights", ["Wartung der Plattform"], changes);

  buttonNamed(shown, /Zeile 1 auf Englisch ergänzen/).click();
  const row = byClass(shown, "tagged-line")[0];
  const [, english] = byTag(row, "input");
  english.oninput({ target: { value: "Platform maintenance" } });

  assert.deepEqual(changes.at(-1), [{ text: { de: "Wartung der Plattform", en: "Platform maintenance" }, tags: [] }]);
});

test("two-language values go out trimmed, without empty languages, and an empty one counts as blank", () => {
  const state = { track: "job", data: {
    summary: { summary: { de: " Satz. ", en: "" } },
    work: [{ position: { de: "Entwicklerin", en: " Developer " }, name: "Beispiel AG", startDate: "2020",
      highlights: [{ text: { de: "Punkt", en: "Point " }, tags: [] }, { de: " ", en: "" }] }, { position: { de: "", en: "" } }],
  } };

  const data = model.collectBundle(form, state, NOW).data;

  assert.deepEqual(data.summary, { summary: { de: "Satz." } });
  assert.deepEqual(data.work, [{ position: { de: "Entwicklerin", en: "Developer" }, name: "Beispiel AG", startDate: "2020",
    highlights: [{ text: { de: "Punkt", en: "Point" }, tags: [] }] }]);
});

test("fields of the CV have no limit of length or count, the others keep theirs", () => {
  const position = fieldRules(form, section("work"), field("work", "position"));
  const highlights = fieldRules(form, section("work"), field("work", "highlights"));
  const strength = fieldRules(form, section("strengths"), field("strengths", "strength"));

  assert.equal(position.max, Infinity);
  assert.equal(highlights.maxItems, Infinity);
  assert.equal(entryLimit(form, section("languages")), Infinity);
  assert.equal(strength.max, 60);
  assert.equal(entryLimit(form, section("strengths")), 6);
  // tags keep their rules (G24)
  assert.equal(field("work", "tags").type, "tags");
});

test("a list of the CV offers another line beyond the old limit", () => {
  const lines = Array.from({ length: 9 }, (_, n) => `Punkt ${n + 1}`);
  const shown = view("work", "highlights", lines, []);

  assert.ok(byTag(shown, "button").some((b) => b.className === "add-line"));
});

test("the fluency takes the suggestions or own words", () => {
  const changes = [];
  const shown = view("languages", "fluency", "fliessend", changes);

  const [input] = byTag(shown, "input");
  const options = byTag(shown, "option").map((o) => o.value);
  assert.equal(input.value, "fliessend");
  assert.ok(options.includes("Muttersprache"));
  input.oninput({ target: { value: "Ferienkenntnisse" } });
  assert.deepEqual(changes, ["Ferienkenntnisse"]);
});

test("a station takes a display instead of its dates", () => {
  assert.ok(field("work", "x-display"));
  assert.equal(field("work", "startDate").requiredUnless, "x-display");
});

test("the values the file holds can be typed anew and pass", () => {
  const work = [{ position: { de: "Teamleiterin", en: "Team lead" }, name: "Neu AG", startDate: "2024-02-01", endDate: "2024-02",
    highlights: [{ de: "Team aufgebaut", en: "Built the team" }, { text: { de: "Budget", en: "Budget" }, tags: ["führung"] }, ..."123456789".split("")] },
  { position: "x".repeat(300), name: "Muster GmbH", "x-display": { de: "seit 2020", en: "since 2020" } }];
  const languages = Array.from({ length: 12 }, (_, n) => ({ language: `Sprache ${n}`, fluency: n ? "fliessend" : { de: "Gut", en: "Good" } }));
  const bundle = { ...cases.bases.job, data: { ...cases.bases.job.data, work, languages } };

  assert.deepEqual(validateBundle(form, bundle, []), []);
});
