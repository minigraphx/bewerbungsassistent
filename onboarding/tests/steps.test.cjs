// The five steps of the template hold every section of a track exactly once.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { sectionsFor } = require("../src/model.js");
const { STEP_GROUPS, stepGroups, groupOfSection } = require("../src/steps.js");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));

test("every section of a track is in exactly one step", () => {
  for (const track of Object.keys(form.tracks)) {
    const sections = sectionsFor(form, track);
    const grouped = stepGroups(sections, track).flatMap((g) => g.sections.map((s) => s.id));
    assert.deepEqual([...grouped].sort(), sections.map((s) => s.id).sort(), track);
    assert.equal(new Set(grouped).size, grouped.length, track);
  }
});

test("groups name only sections that exist", () => {
  const known = new Set(form.sections.map((s) => s.id));
  for (const group of STEP_GROUPS) {
    for (const ids of Object.values(group.sections)) ids.forEach((id) => assert.ok(known.has(id), id));
  }
});

test("each step has a title and a line below it for both tracks", () => {
  for (const track of Object.keys(form.tracks)) {
    for (const group of stepGroups(sectionsFor(form, track), track)) {
      assert.ok(group.title && group.meta, `${group.id} ${track}`);
      assert.ok(group.sections.length > 0, `${group.id} ${track}`);
    }
  }
});

test("a section leads to its step", () => {
  const groups = stepGroups(sectionsFor(form, "apprenticeship"), "apprenticeship");
  assert.equal(groups[groupOfSection(groups, "searchApprenticeship")].id, "search");
  assert.equal(groups[groupOfSection(groups, "education")].id, "career");
  assert.equal(groupOfSection(groups, "searchJob"), -1);
});
