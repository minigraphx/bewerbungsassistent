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

// #291: search window, portals and the positive title terms come from the search profile as fields of their own.
const { findAll, loadScripts } = require("./fake_dom.cjs");
const { validateBundle, describe } = require("../src/validate.js");
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));
const page = loadScripts(["validate.js", "model.js", "dom.js"]);
const searchField = (id) => form.sections.find((s) => s.id === "searchJob").fields.find((f) => f.id === id);
const plain = (value) => JSON.parse(JSON.stringify(value));
const boxes = (node) => findAll(node, (n) => n.tagName === "input" && n.type === "checkbox");

test("window, portals switched off and positive title terms are taken from the search profile", () => {
  const read = { searchJob: { home: "Thun", window: "14", portalsOff: ["jobscout24"], titlePositive: ["Entwickler", "Data"] } };

  const filled = model.fillFromBasics(form, kept(), read);

  assert.deepEqual(filled.data.searchJob, read.searchJob);
});

test("the portals show as boxes ticked for every portal that searches", () => {
  const changes = [];
  const node = page.fieldView(searchField("portalsOff"), {
    track: "job", value: ["jobscout24"], path: "searchJob.portalsOff", onChange: (v) => changes.push(v), onBlur() {},
  });
  const shown = boxes(node);

  assert.deepEqual(shown.map((box) => [box.value, Boolean(box.checked)]),
    [["job-room", true], ["jobs.ch", true], ["jobscout24", false], ["ictjobs", true]]);
  shown[3].checked = false;
  shown[3].onchange({ target: shown[3] });
  assert.deepEqual(plain(changes.at(-1)), ["jobscout24", "ictjobs"]);
  shown[2].checked = true;
  shown[2].onchange({ target: shown[2] });
  assert.deepEqual(plain(changes.at(-1)), ["ictjobs"]);
});

test("a window the search cannot use and no portal left are refused with the search's own words", () => {
  const bundle = structuredClone(cases.bases.job);
  bundle.data.searchJob = { ...bundle.data.searchJob, window: "61", portalsOff: ["job-room", "jobs.ch", "jobscout24", "ictjobs"] };

  const errors = validateBundle(form, bundle);

  assert.deepEqual(errors.map((e) => [e.path, e.code]), [["searchJob.window", "format"], ["searchJob.portalsOff", "maxItems"]]);
  assert.equal(describe(form, "job", errors[1]),
    "Suche, Portale für die Suche: Mindestens ein Portal muss gewählt bleiben, sonst findet die Suche nichts.");
});
