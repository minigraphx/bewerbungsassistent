// The categories of documents stop offering more files once their limit is reached (#155).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const page = loadScripts(["validate.js", "model.js", "dom.js", "documents.js", "uploads.js", "prefill.js"]);
const category = (id) => form.documents.categories.find((c) => c.id === id);
const cvs = (count) => Array.from({ length: count }, (_, i) => ({ category: "lebenslauf-bisher", name: `cv${i}.pdf`, size: 10 }));

function view(track, uploads, id) {
  const ctx = { form, track, uploads, messages: [], kept: true, onAdd() {}, onRemove() {}, onSkip() {} };
  return page.categoryView(ctx, category(id), vm.runInContext("UPLOAD_TEXT", page)[track]);
}

const addButton = (node) => findAll(node, (n) => n.tagName === "button" && n.className === "add")[0];
const limitNote = (node) => findAll(node, (n) => n.className === "hint limit-note")[0];

test("the CV takes up to ten files", () => {
  assert.equal(category("lebenslauf-bisher").maxFiles, 10);
});

test("below the limit the add button is offered without a note", () => {
  const node = view("job", cvs(9), "lebenslauf-bisher");
  assert.equal(addButton(node).disabled, undefined);
  assert.equal(limitNote(node), undefined);
});

test("at the limit the add button is disabled with a note naming the limit, in every category", () => {
  for (const { id, maxFiles } of form.documents.categories) {
    for (const track of ["job", "apprenticeship"]) {
      const uploads = Array.from({ length: maxFiles }, (_, i) => ({ category: id, name: `datei${i}.pdf`, size: 10 }));
      const node = view(track, uploads, id);
      const button = addButton(node);
      const note = limitNote(node);
      assert.equal(button.disabled, true, `${id} ${track}`);
      assert.ok(note, `${id} ${track}`);
      assert.match(note.textContent, new RegExp(`höchstens ${maxFiles} Dateien`, "i"));
      assert.equal(button.getAttribute("aria-describedby"), note.id);
    }
  }
});

test("files of other categories do not count against the limit", () => {
  const others = Array.from({ length: 10 }, (_, i) => ({ category: "anschreiben-bisher", name: `a${i}.pdf`, size: 10 }));
  assert.equal(addButton(view("job", others, "lebenslauf-bisher")).disabled, undefined);
});
