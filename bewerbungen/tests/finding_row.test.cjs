// A finding of the check as a list line, the longest paragraph of a letter over one page and the focus after
// «So lassen» (G52, G94, #325), with a small stand-in DOM.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const logik = require("../seiten/bewerbung-logik.js");

const SEITEN = path.join(__dirname, "..", "seiten");

class FakeElement {
  constructor(doc, tag, attrs = {}) {
    Object.assign(this, { doc, tagName: tag.toUpperCase(), attrs: new Map(), children: [], listeners: {} });
    for (const [name, value] of Object.entries(attrs)) {
      if (value === false || value === null || value === undefined) continue;
      if (name.startsWith("on")) this.listeners[name.slice(2)] = value;
      else this.attrs.set(name, value === true ? "" : String(value));
    }
  }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  append(...nodes) { this.children.push(...nodes.flat().filter(n => n !== null && n !== undefined && n !== false)); }
  get elements() { return this.children.filter(c => c instanceof FakeElement); }
  get textContent() { return this.children.map(c => (c instanceof FakeElement ? c.textContent : String(c))).join(""); }
  all() { return this.elements.flatMap(c => [c, ...c.all()]); }
  querySelector(selector) { return this.all().find(e => e.tagName === selector.toUpperCase()) || null; }
  click() { if (this.listeners.click) this.listeners.click({ currentTarget: this, target: this }); }
  focus() { this.doc.activeElement = this; }
  get className() { return this.getAttribute("class") || ""; }
}

function setup() {
  const doc = { activeElement: null };
  const lines = [];
  const window = {
    BewerbungLogik: logik,
    App: { el: (tag, attrs, ...kids) => { const e = new FakeElement(doc, tag, attrs || {}); e.append(...kids); return e; } },
    Meldungen: {
      listenZeile(document, content, stufe, options = {}) {
        const li = new FakeElement(doc, "li", { "data-stufe": stufe });
        li.append(content);
        lines.push({ li, options });
        return li;
      },
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(SEITEN, "finding-row.js"), "utf8"), { window, document: doc });
  return { doc, lines, F: window.FindingRow, el: window.App.el };
}

const letterOver = {
  stufe: "fehler", schluessel: "abc:seiten:2", bestaetigt: false,
  text: "Anschreiben: 2 Seiten, erlaubt ist eine. Auch so eng wie möglich gesetzt sind es etwa 20 Zeilen zu viel.",
  letter_cut: { lines: 20, paragraph: 5, pages: 2 },
};
const breach = { stufe: "hinweis", text: "Lebenslauf, Seite 2: nur zu 20 % gefüllt.", schluessel: "abc:fuellung:2", bestaetigt: false };
const buttons = node => node.all().filter(e => e.tagName === "BUTTON");

test("a letter over one page has no «×»: it waits on a decision", () => {
  const { F, lines } = setup();
  F.row(letterOver, logik.befundZeile(letterOver), { onCut() {}, onKeep() {} });
  F.row(breach, logik.befundZeile(breach), { onCut() {}, onKeep() {} });
  assert.equal(lines[0].options.schliessbar, false);
  assert.notEqual(lines[1].options.schliessbar, false, "other findings keep their «×»");
});

test("the sentence stands as text, the two buttons on a row of their own, the cut first and primary", () => {
  const { F } = setup();
  const li = F.row(letterOver, logik.befundZeile(letterOver), { onCut() {}, onKeep() {} });
  const [content] = li.elements;
  const [sentence, row] = content.elements;
  assert.equal(sentence.textContent, letterOver.text);
  assert.match(row.className, /\bbtn-row\b/);
  assert.deepEqual(row.elements.map(b => [b.textContent, b.className]),
    [["Im Anschreiben kürzen", "btn btn--sm btn--primary"], ["So lassen", "btn btn--sm"]]);
});

test("the buttons call their actions; «So lassen» hands over its button", () => {
  const { F } = setup();
  const calls = [];
  const li = F.row(letterOver, logik.befundZeile(letterOver), { onCut: () => calls.push("cut"), onKeep: b => calls.push(b.textContent) });
  buttons(li).forEach(b => b.click());
  assert.deepEqual(calls, ["cut", "So lassen"]);
});

const cvOver = {
  stufe: "hinweis", schluessel: "abc:seiten:4", bestaetigt: false, cv_over: { lines: 7, pages: 4 },
  text: "Lebenslauf: 4 Seiten, erlaubt sind höchstens 3. Auch so eng wie möglich gesetzt sind es etwa 7 Zeilen zu viel. Weiter kürzen lässt sich mit «Lebenslauf erstellen», nur für diese Bewerbung, oder unter «Meine Angaben», für alle.",
};

test("a CV over three pages with no cut left has no «×» and «So lassen» alone on its own row (#330)", () => {
  const { F, lines } = setup();
  const kept = [];
  const li = F.row(cvOver, logik.befundZeile(cvOver), { onCut() { kept.push("cut"); }, onKeep: b => kept.push(b.textContent) });
  assert.equal(lines[0].options.schliessbar, false);
  const [content] = li.elements;
  const [sentence, row] = content.elements;
  assert.equal(sentence.textContent, cvOver.text);
  assert.match(row.className, /\bbtn-row\b/);
  assert.deepEqual(row.elements.map(b => [b.textContent, b.className]), [["So lassen", "btn btn--sm"]]);
  buttons(li).forEach(b => b.click());
  assert.deepEqual(kept, ["So lassen"]);
  assert.equal(li.getAttribute("data-offen"), "", "it waits, so the focus can come to it after another «So lassen»");
});

test("confirmed, the CV over three pages is a hint line that takes the focus", () => {
  const { F, el, doc, lines } = setup();
  const done = { ...cvOver, bestaetigt: true };
  const list = el("ul", {}, F.row(done, logik.befundZeile(done), { onCut() {}, onKeep() {} }));
  assert.equal(lines[0].li.getAttribute("data-stufe"), "hinweis");
  assert.equal(list.elements[0].textContent, "Lebenslauf: 4 Seiten, etwa 7 Zeilen zu viel. Bestätigt: so lassen.");
  F.focusAfterConfirm(list, done.schluessel);
  assert.equal(doc.activeElement, list.elements[0]);
});

test("the longest paragraph: the group named by its label, then the paragraph, then «Anschreiben ändern»", () => {
  const { F, el } = setup();
  const paragraph = el("p", {}, "Bei der Beispiel GmbH habe ich eine Plattform für Kundendaten aufgebaut.");
  const opened = [];
  const group = F.longest(paragraph, () => opened.push("editor"));
  assert.equal(group.getAttribute("role"), "group");
  assert.equal(group.getAttribute("tabindex"), "-1");
  const [label, text, link] = group.elements;
  assert.equal(group.getAttribute("aria-labelledby"), label.getAttribute("id"));
  assert.equal(label.textContent, "Längster Absatz");
  assert.equal(label.getAttribute("aria-hidden"), "true");
  assert.equal(text, paragraph);
  assert.equal(link.tagName, "BUTTON", "it opens the editor in the step (#332), no link to /inhalte");
  assert.equal(link.getAttribute("type"), "button");
  assert.equal(link.textContent, "Anschreiben ändern");
  assert.equal(link.getAttribute("href"), null);
  assert.equal(link.className, "btn btn--sm btn--quiet letter-longest__edit");
  link.click();
  assert.deepEqual(opened, ["editor"]);
});

test("after «So lassen» the focus goes to the first button of the next open finding", () => {
  const { F, el, doc } = setup();
  const done = { ...breach, bestaetigt: true };
  const list = el("ul", {}, ...[letterOver, done, { ...breach, schluessel: "abc:rand:1" }]
    .map(b => F.row(b, logik.befundZeile(b), { onCut() {}, onKeep() {} })));
  F.focusAfterConfirm(list, done.schluessel);
  assert.equal(doc.activeElement.textContent, "So lassen");
  assert.equal(doc.activeElement, buttons(list.elements[2])[0], "the finding after the confirmed one");
});

test("with no later finding open, the focus goes to the first open one before", () => {
  const { F, el, doc } = setup();
  const done = { ...breach, bestaetigt: true };
  const list = el("ul", {}, ...[letterOver, done].map(b => F.row(b, logik.befundZeile(b), { onCut() {}, onKeep() {} })));
  F.focusAfterConfirm(list, done.schluessel);
  assert.equal(doc.activeElement.textContent, "Im Anschreiben kürzen");
});

test("with nothing open, the confirmed line itself takes the focus", () => {
  const { F, el, doc } = setup();
  const done = { ...letterOver, stufe: "hinweis", bestaetigt: true };
  const list = el("ul", {}, F.row(done, logik.befundZeile(done), { onCut() {}, onKeep() {} }));
  F.focusAfterConfirm(list, done.schluessel);
  assert.equal(doc.activeElement, list.elements[0]);
  assert.equal(doc.activeElement.getAttribute("tabindex"), "-1");
  assert.equal(doc.activeElement.getAttribute("data-schluessel"), done.schluessel);
});

test("the page of the application draws its findings and the marked paragraph with it", () => {
  const html = fs.readFileSync(path.join(SEITEN, "bewerbung.html"), "utf8");
  const page = fs.readFileSync(path.join(SEITEN, "bewerbung.js"), "utf8");
  assert.ok(html.indexOf('src="/finding-row.js"') > 0 && html.indexOf('src="/finding-row.js"') < html.indexOf('src="/bewerbung.js"'));
  const app = fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8");
  assert.match(app, /"\/finding-row\.js": "finding-row\.js"/, "the server hands out the script");
  assert.match(page, /FindingRow\.row\(b, zeile, /);
  assert.match(page, /FindingRow\.longest\(/);
  assert.match(page, /zeigeBefunde\(\);\s*if \(daten\) zeigeAlles\(\);\s*FindingRow\.focusAfterConfirm\(\$\("befunde"\), schluessel\);/);
});

test("the label of the longest paragraph is 14 px", () => {
  const css = fs.readFileSync(path.join(SEITEN, "stil.css"), "utf8");
  assert.match(css, /\.letter-longest__label \{[^}]*font-size: 14px;/);
});
