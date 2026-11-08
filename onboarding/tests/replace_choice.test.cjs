// Taking over on „Meine Angaben“: one choice per existing Markdown file, kept unless replacing is picked,
// and the differences show before anything is replaced (G26, #163).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const page = loadScripts(["dom.js", "replacechoice.js"]);
const CHANGES = [
  { datei: "suchprofil.md", titel: "Suchprofil", zeilen: [] },
  { datei: "anschreiben/stil.md", titel: "Stilprofil", zeilen: [
    { art: "gleich", text: "# Stilprofil" },
    { art: "weg", text: "- Von Hand ergänzt" },
    { art: "neu", text: "- Aus den Angaben" },
    { art: "luecke", text: "" },
    { art: "gleich", text: "## Ton" },
  ] },
];

const radios = (node) => findAll(node, (n) => n.tagName === "input" && n.type === "radio");
const tagged = (node, tag) => findAll(node, (n) => n.tagName === tag);

test("every file starts as kept and shows no differences", () => {
  const choices = page.defaultReplaceChoices(CHANGES);
  const node = page.replaceChoiceView({ changes: CHANGES, choices, onChoose() {} });

  assert.deepEqual({ ...choices }, { "suchprofil.md": "keep", "anschreiben/stil.md": "keep" });
  const checked = radios(node).filter((r) => r.checked);
  assert.deepEqual(checked.map((r) => r.value), ["keep", "keep"]);
  assert.equal(tagged(node, "ins").length + tagged(node, "del").length, 0);
  assert.match(node.textContent, /Suchprofil/);
  assert.match(node.textContent, /Behalten/);
  assert.deepEqual([...page.chosenReplacements(choices)], []);
});

test("picking replace reports the file and shows its differences in place", () => {
  const picked = [];
  const node = page.replaceChoiceView({
    changes: CHANGES, choices: page.defaultReplaceChoices(CHANGES), onChoose: (file, value) => picked.push([file, value]),
  });

  const replace = radios(node).filter((r) => r.value === "replace")[1];
  replace.onchange({ target: replace });

  assert.deepEqual(picked, [["anschreiben/stil.md", "replace"]]);
  assert.deepEqual(tagged(node, "del").map((n) => n.textContent), ["- Von Hand ergänzt"]);
  const keep = radios(node).filter((r) => r.value === "keep")[1];
  keep.onchange({ target: keep });
  assert.equal(tagged(node, "del").length, 0);
  assert.deepEqual(picked.at(-1), ["anschreiben/stil.md", "keep"]);
});

test("a file chosen for replacing shows what goes and what comes", () => {
  const choices = { "suchprofil.md": "keep", "anschreiben/stil.md": "replace" };
  const node = page.replaceChoiceView({ changes: CHANGES, choices, onChoose() {} });

  assert.deepEqual(tagged(node, "del").map((n) => n.textContent), ["- Von Hand ergänzt"]);
  assert.deepEqual(tagged(node, "ins").map((n) => n.textContent), ["- Aus den Angaben"]);
  assert.match(node.textContent, /# Stilprofil/);
  assert.match(node.textContent, /…/);
  assert.deepEqual([...page.chosenReplacements(choices)], ["anschreiben/stil.md"]);
});

test("a file without differences says so when replacing is picked", () => {
  const node = page.replaceChoiceView({ changes: CHANGES, choices: { "suchprofil.md": "replace" }, onChoose() {} });

  assert.match(node.textContent, /Kein Unterschied/);
  assert.equal(tagged(node, "ins").length, 0);
  assert.doesNotMatch(node.textContent, /ß/);
});
