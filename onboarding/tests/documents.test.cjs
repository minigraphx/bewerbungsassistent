// Runs the shared document cases of cases.json against src/documents.js (same cases as test_documents.py).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { validateDocuments, describeDocument, safeDocumentName } = require("../src/documents.js");

const root = path.join(__dirname, "..");
const form = JSON.parse(fs.readFileSync(path.join(root, "form.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "cases.json"), "utf8"));
const key = (e) => `${e.path}|${e.code}`;

for (const c of cases.documentCases) {
  test(c.name, () => {
    assert.deepEqual(validateDocuments(form, c.documents).map(key).sort(), c.errors.map(key).sort());
  });
}

test("documents must be a list", () => {
  assert.deepEqual(validateDocuments(form, { a: 1 }).map(key), ["documents|type"]);
});

test("messages name category and file", () => {
  const entries = [{ category: "zeugnisse", name: "gross.pdf", size: 20000000 }];
  const [error] = validateDocuments(form, entries);
  assert.equal(describeDocument(form, "job", entries, error), "Arbeitszeugnisse, gross.pdf: Die Datei ist zu gross (höchstens 15 MB).");
});

test("a wrong type names what the category accepts", () => {
  for (const [category, expected] of [
    ["anschreiben-bisher", "Erlaubt sind PDF, Word (.docx, .doc) und Textdateien (.txt)."],
    ["zertifikate", "Erlaubt sind PDF, Word (.docx, .doc), Textdateien (.txt) und Bilder (.jpg, .png)."],
  ]) {
    const entries = [{ category, name: "datei.exe", size: 10 }];
    const [error] = validateDocuments(form, entries);
    assert.ok(describeDocument(form, "job", entries, error).endsWith(`Dieser Dateityp geht nicht. ${expected}`));
  }
});

test("chosen file names are made safe and keep their extension", () => {
  assert.equal(safeDocumentName("../Zeugnis: Beispiel AG?.pdf"), "Zeugnis- Beispiel AG-.pdf");
  assert.equal(safeDocumentName(".versteckt.pdf"), "versteckt.pdf");
  assert.equal(safeDocumentName("Lebenslauf. "), "Lebenslauf");
  const long = safeDocumentName("ä".repeat(200) + ".pdf");
  assert.equal(Array.from(long).length, 120);
  assert.ok(long.endsWith(".pdf"));
  assert.equal(safeDocumentName("\u0007"), "unterlage");
});

test("safe names pass the name rule", () => {
  for (const raw of ["../a?.pdf", ".x.docx", "a\\b.txt", "x".repeat(300) + ".doc"]) {
    const name = safeDocumentName(raw);
    assert.deepEqual(validateDocuments(form, [{ category: "zeugnisse", name, size: 1 }]), [], name);
  }
});

const docs = require("../src/documents.js");

test("chosen files are checked together with those already there", () => {
  const current = [{ category: "lebenslauf-bisher", name: "cv.pdf", size: 10 }, { category: "lebenslauf-bisher", name: "cv2.pdf", size: 10 }];
  const chosen = [{ name: "C:\\Users\\x\\cv.pdf", size: 10 }, { name: "neu.docx", size: 10 }, { name: "bild.png", size: 10 }];
  const { accepted, messages } = docs.planUploads(form, "job", current, "lebenslauf-bisher", chosen);
  assert.deepEqual(accepted, [{ index: 1, category: "lebenslauf-bisher", name: "neu.docx", size: 10 }]);
  assert.equal(messages.length, 2);
  assert.match(messages[0], /schon dabei/);
  assert.match(messages[1], /Dateityp/);
});

test("more files than fit: those that fit are added, one message says how many were left out", () => {
  const current = Array.from({ length: 8 }, (_, i) => ({ category: "lebenslauf-bisher", name: `cv${i}.pdf`, size: 10 }));
  const chosen = ["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"].map((name) => ({ name, size: 10 }));
  const { accepted, messages } = docs.planUploads(form, "job", current, "lebenslauf-bisher", chosen);
  assert.deepEqual(accepted.map((a) => a.name), ["a.pdf", "b.pdf"]);
  assert.deepEqual(messages, ["Bisheriger Lebenslauf: höchstens 10 Dateien. 3 Dateien wurden nicht hinzugefügt."]);
});

test("one file left out is named in the singular", () => {
  const current = Array.from({ length: 10 }, (_, i) => ({ category: "lebenslauf-bisher", name: `cv${i}.pdf`, size: 10 }));
  const { accepted, messages } = docs.planUploads(form, "apprenticeship", current, "lebenslauf-bisher", [{ name: "x.pdf", size: 10 }]);
  assert.deepEqual(accepted, []);
  assert.deepEqual(messages, ["Bisheriger Lebenslauf: höchstens 10 Dateien. Eine Datei wurde nicht hinzugefügt."]);
});

test("images are taken for certificates", () => {
  const { accepted, messages } = docs.planUploads(form, "job", [], "zertifikate", [{ name: "Diplom.JPG", size: 10 }]);
  assert.deepEqual(messages, []);
  assert.equal(accepted[0].name, "Diplom.JPG");
});

test("upload ZIP entries split back into answers and uploads", () => {
  const bundle = new TextEncoder().encode("{}");
  const uploads = [{ category: "zeugnisse", name: "Zeugnis.pdf", size: 3, data: new Uint8Array([1, 2, 3]) }];
  const entries = docs.uploadZipEntries(bundle, uploads);
  assert.deepEqual(entries.map((e) => e.name), ["einstieg.json", "dokumente/zeugnisse/Zeugnis.pdf"]);
  const split = docs.splitUploadZip(form, entries);
  assert.deepEqual(split.bundle, bundle);
  assert.deepEqual(split.uploads, uploads);
});

test("a loaded ZIP with unexpected content is refused", () => {
  const data = new Uint8Array([1]);
  const bundle = { name: "einstieg.json", data };
  for (const [entries, message] of [
    [[{ name: "dokumente/zeugnisse/a.pdf", data }], /genau eine einstieg.json/],
    [[bundle, { name: "../a.pdf", data }], /Unerwarteter Inhalt/],
    [[bundle, { name: "dokumente/zeugnisse/x/a.pdf", data }], /Unerwarteter Inhalt/],
    [[bundle, { name: "dokumente/geheim/a.pdf", data }], /Unbekannte Art/],
    [[bundle, { name: "dokumente/zeugnisse/a.exe", data }], /Dateityp/],
  ]) {
    assert.throws(() => docs.splitUploadZip(form, entries), (e) => e instanceof docs.UploadError && message.test(e.message));
  }
});

test("a saved ZIP may hold the answers and the most files of every category", () => {
  assert.equal(docs.maxUploadEntries(form), 1 + 10 + 20 + 30 + 10);
});
