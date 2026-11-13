// „Lebenslauf und Dateien“ (#264, A9, G55, G21): the choice of the CV, one list of certificates and references, photos.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const logic = require("../seiten/dateien-logik.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");

test("the app builds the CV unless an own PDF is there or chosen", () => {
  assert.equal(logic.cvChoice({ ownPdf: false }), "app");
  assert.equal(logic.cvChoice({ ownPdf: false, wantsOwn: true }), "eigen");
  assert.equal(logic.cvChoice({ ownPdf: true }), "eigen");
  assert.equal(logic.cvChoice({ ownPdf: true, wantsOwn: false }), "eigen", "only removing the PDF goes back to the app");
});

test("choosing the app while an own PDF is there asks before removing it", () => {
  assert.equal(logic.needsRemoval({ ownPdf: true, chosen: "app" }), true);
  assert.equal(logic.needsRemoval({ ownPdf: false, chosen: "app" }), false);
  assert.equal(logic.needsRemoval({ ownPdf: true, chosen: "eigen" }), false);
});

test("applications with a variant are named, none says nothing", () => {
  assert.equal(logic.variantNote(0), "");
  assert.equal(logic.variantNote(1), "1 Bewerbung hat eine eigene Variante, dort gilt sie.");
  assert.equal(logic.variantNote(3), "3 Bewerbungen haben eine eigene Variante, dort gilt sie.");
});

test("the kind of a new file is guessed from its name", () => {
  for (const name of ["Arbeitszeugnis Beispiel AG.pdf", "Zwischenzeugnis.png", "Schulzeugnis 2025.jpg",
                      "Referenz Muster.pdf", "Arbeitsbestätigung.pdf", "reference letter.pdf"]) {
    assert.equal(logic.guessKind(name), "zeugnis", name);
  }
  for (const name of ["Zertifikat Python.pdf", "Diplom Informatik.pdf", "Scrum Master.pdf", "Kurs.png"]) {
    assert.equal(logic.guessKind(name), "zertifikat", name);
  }
});

test("certificates and references are one list, sorted by name, each with its kind", () => {
  const rows = logic.oneList({
    lebenslauf: [{ datei: "dokumente/lebenslauf.pdf", name: "lebenslauf.pdf", groesse: 1 }],
    zertifikat: [{ datei: "dokumente/zertifikate/Zertifikat Python.pdf", name: "Zertifikat Python.pdf", groesse: 12000 }],
    zeugnis: [{ datei: "dokumente/zeugnisse/Arbeitszeugnis Beispiel AG.pdf", name: "Arbeitszeugnis Beispiel AG.pdf", groesse: 48000 }],
  });
  assert.deepEqual(rows.map(row => [row.name, row.art]),
                   [["Arbeitszeugnis Beispiel AG.pdf", "zeugnis"], ["Zertifikat Python.pdf", "zertifikat"]]);
});

test("sizes read as KB or MB with a decimal point", () => {
  assert.equal(logic.sizeText(12000), "12 KB");
  assert.equal(logic.sizeText(300), "1 KB");
  assert.equal(logic.sizeText(2500000), "2.5 MB");
});

test("the photo card says how many photos there are and which one is used", () => {
  assert.equal(logic.photoSummary([]), "Noch kein Foto. Ein Foto ist freiwillig.");
  assert.equal(logic.photoSummary([{ datei: "foto.jpg", aktiv: true }]), "1 Foto, es wird verwendet.");
  assert.equal(logic.photoSummary([{ datei: "foto.jpg", aktiv: true }, { datei: "fotos/b.jpg", aktiv: false }]),
               "2 Fotos, das umrandete wird verwendet.");
});

test("the page is one: CV choice, one list, photos and earlier versions", () => {
  const html = read("dateien.html");
  assert.match(html, /<title>Lebenslauf und Dateien<\/title>/);
  assert.match(html, /<h1>Lebenslauf und Dateien<\/h1>/);
  assert.match(html, /data-cv="app"[\s\S]*Die App erstellt ihn/);
  assert.match(html, /data-cv="eigen"[\s\S]*Ich nehme mein eigenes PDF/);
  assert.doesNotMatch(html, /class="rank"/, "the ranking is gone");
  assert.equal((html.match(/class="card eigene-dateien"/g) || []).length, 0, "no card per kind");
  assert.match(html, /id="nachweise"/);
  assert.match(html, /id="fotos"/);
  assert.match(html, /href="\/foto"[^>]*>Ausschnitt anpassen/);
  assert.match(html, /href="\/entwuerfe"[^>]*>Frühere Fassungen ansehen/);
  assert.ok(html.indexOf("/dateien-logik.js") < html.indexOf("/dateien.js"));
});

test("no page names the old pages any more", () => {
  for (const name of fs.readdirSync(PAGES).filter(file => /\.(html|js)$/.test(file))) {
    assert.ok(!read(name).includes("Meine Dateien"), name);
  }
});

const texts = require("../seiten/texte.js");
const SIE_FORM = /\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b/;
const withoutTextElements = html => html.replace(/<(\w+)\b[^>]*\bdata-text="[^"]*"[^>]*>[\s\S]*?<\/\1>/g, "");

test("the page leaves its address to the text set", () => {
  assert.doesNotMatch(withoutTextElements(read("dateien.html")), SIE_FORM);
  assert.doesNotMatch(read("dateien.js"), SIE_FORM);
  assert.doesNotMatch(read("dateien-logik.js"), SIE_FORM);
});

test("each data-text of the page is known and starts as the Sie text", () => {
  const elements = [...read("dateien.html").matchAll(/<(\w+)\b[^>]*\bdata-text="([^"]*)"[^>]*>([\s\S]*?)<\/\1>/g)];
  assert.ok(elements.length >= 8);
  for (const [, , key, content] of elements) assert.equal(content, texts.text(key, "stelle-sie"), key);
});

test("with the photo switched off the card says new documents have none (G62)", () => {
  const one = [{ datei: "foto.jpg", aktiv: true }];
  const two = [...one, { datei: "fotos/b.jpg", aktiv: false }];
  assert.equal(logic.photoSummary(one, false), "1 Foto. Neue Unterlagen entstehen ohne Foto.");
  assert.equal(logic.photoSummary(two, false), "2 Fotos. Neue Unterlagen entstehen ohne Foto.");
  assert.equal(logic.photoSummary(one, true), "1 Foto, es wird verwendet.");
  assert.equal(logic.photoSummary([], false), "Noch kein Foto. Ein Foto ist freiwillig.");
});

test("the switch is there once a photo exists and starts on (G62)", () => {
  assert.equal(logic.photoSwitch([], undefined).visible, false);
  assert.deepEqual(logic.photoSwitch([{ datei: "foto.jpg", aktiv: true }], undefined), { visible: true, checked: true });
  assert.deepEqual(logic.photoSwitch([{ datei: "foto.jpg", aktiv: true }], false), { visible: true, checked: false });
  const html = read("dateien.html");
  assert.match(html, /<input type="checkbox" id="foto-zeigen"[^>]*>\s*<span>Im Lebenslauf zeigen<\/span>/);
  assert.ok(html.indexOf('id="fotos"') < html.indexOf('id="foto-zeigen"'), "the switch sits with the photos");
});

// G61 (#280): „Aussehen wählen“ picks the design the app builds the CV with.
test("the designs of the CV are two columns (preset) and one column", () => {
  assert.deepEqual(logic.DESIGNS.map(design => design.id), ["zweispaltig", "einspaltig"]);
  assert.equal(logic.PRESET_DESIGN, "zweispaltig");
  assert.equal(logic.designName("einspaltig"), "Einspaltig");
  assert.equal(logic.designName("unbekannt"), "Zweispaltig", "an unknown design reads as the preset");
  for (const design of logic.DESIGNS) assert.ok(design.text.length > 10, design.id);
});

test("only a changed design is saved, and only one the app knows", () => {
  assert.deepEqual(logic.designToSave("zweispaltig", "einspaltig"), { design: "einspaltig" });
  assert.equal(logic.designToSave("einspaltig", "einspaltig"), null);
  assert.throws(() => logic.designToSave("zweispaltig", "dossier-siegel"), /Zweispaltig oder Einspaltig/);
});

test("after saving, the page says that what exists stays as it is", () => {
  const text = logic.designSaved("einspaltig");
  assert.match(text, /Einspaltig/);
  assert.match(text, /bleibt/);
});

test("Aussehen wählen sits beside Ansehen and opens the choice of the design", () => {
  const html = read("dateien.html");
  assert.match(html, /id="cv-ansehen"[\s\S]*id="cv-aussehen"[^>]*>Aussehen wählen<[\s\S]*id="cv-anpassen"/);
  assert.match(html, /<dialog[^>]*id="aussehen-dialog"[\s\S]*role="radiogroup"[\s\S]*id="aussehen-ja"/);
  assert.match(html, /id="cv-design"/);
});
