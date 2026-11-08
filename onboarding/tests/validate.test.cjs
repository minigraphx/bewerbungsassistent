// Runs the shared cases of cases.json against src/validate.js (same cases as test_validation.py).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { validateBundle, describe } = require("../src/validate.js");

const root = path.join(__dirname, "..");
const form = JSON.parse(fs.readFileSync(path.join(root, "form.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));

const expand = (v) => (v && typeof v === "object" && "$repeat" in v ? v.$repeat.repeat(v.times) : v);
const expandAll = (v) => {
  if (Array.isArray(v)) return v.map(expandAll);
  if (v && typeof v === "object" && !("$repeat" in v)) return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, expandAll(x)]));
  return expand(v);
};
const walk = (obj, keys) => keys.reduce((o, k) => (Array.isArray(o) ? o[Number(k)] : o[k]), obj);

function applyCase(c) {
  const bundle = structuredClone(cases.bases[c.base]);
  for (const [p, value] of c.set || []) {
    const keys = p.split(".");
    const last = keys.pop();
    const target = walk(bundle, keys);
    target[Array.isArray(target) ? Number(last) : last] = expand(value);
  }
  for (const p of c.remove || []) {
    const keys = p.split(".");
    const last = keys.pop();
    delete walk(bundle, keys)[last];
  }
  return bundle;
}

const key = (e) => `${e.path}|${e.code}`;

for (const c of cases.cases) {
  test(c.name, () => {
    const found = validateBundle(form, applyCase(c), (c.known || []).map(expand), c.loaded ? expandAll(c.loaded) : undefined).map(key).sort();
    assert.deepEqual(found, c.errors.map(key).sort());
  });
}

test("messages are German and name the field", () => {
  const bundle = structuredClone(cases.bases.job);
  bundle.data.work[1].endDate = "2014";
  const [error] = validateBundle(form, bundle);
  assert.ok(describe(form, "job", error).startsWith("Berufliche Stationen, Station 2, Bis"));
});
