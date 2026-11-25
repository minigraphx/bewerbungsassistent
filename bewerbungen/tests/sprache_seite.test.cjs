// The card «Sprache» in a small stand-in DOM (G10, G12, #94): what the page shows after the server answers, and
// that a refused change goes back to the state the server last sent, without asking the server again.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SEITEN = path.join(__dirname, "..", "seiten");
const SUGGESTED = { app: "de", app_gewaehlt: false, bewerbung: ["de", "en"], bewerbung_gewaehlt: false,
                    vorschlag: [{ sprache: "de", stufe: "Muttersprache" }, { sprache: "en", stufe: "Fliessend" }] };
const CARD_IDS = ["sprache-app", "sprache-folgt", "sprache-bewerbung", "sprache-optionen", "sprache-meldung"];
const CHOSEN = { ...SUGGESTED, bewerbung: ["de", "en", "fr"], bewerbung_gewaehlt: true };

class FakeText {
  constructor(text) { this.data = String(text); this.parent = null; }
  get textContent() { return this.data; }
}

class FakeElement {
  constructor(tag) {
    Object.assign(this, { tagName: tag.toUpperCase(), attrs: new Map(), children: [], parent: null, listeners: {},
      value: "", checked: false, className: "" });
  }
  setAttribute(name, value) {
    this.attrs.set(name, String(value));
    if (name === "value") this.value = String(value);
  }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  hasAttribute(name) { return this.attrs.has(name); }
  removeAttribute(name) { this.attrs.delete(name); }
  get id() { return this.getAttribute("id") || ""; }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  get parentElement() { return this.parent; }
  append(...nodes) {
    for (const given of nodes) {
      const node = given instanceof FakeElement || given instanceof FakeText ? given : new FakeText(given);
      node.parent = this;
      this.children.push(node);
    }
  }
  replaceChildren(...nodes) {
    for (const child of this.children) child.parent = null;
    this.children = [];
    this.append(...nodes);
  }
  get textContent() { return this.children.map(child => child.textContent).join(""); }
  set textContent(text) { this.replaceChildren(...(String(text) ? [String(text)] : [])); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatch(type) {
    const event = { type, target: this };
    for (const handler of this.listeners[type] || []) handler(event);
  }
  focus() {}
  all() { return this.children.filter(c => c instanceof FakeElement).flatMap(c => [c, ...c.all()]); }
  matches(selector) {
    const named = /^input\[name="([^"]+)"\]$/.exec(selector);
    if (named) return this.tagName === "INPUT" && this.getAttribute("name") === named[1];
    if (selector.startsWith(".")) return this.className.split(/\s+/).includes(selector.slice(1));
    if (selector.startsWith("#")) return this.id === selector.slice(1);
    return this.tagName === selector.toUpperCase();
  }
  querySelector(selector) { return this.all().find(node => node.matches(selector)) || null; }
  querySelectorAll(selector) { return this.all().filter(node => node.matches(selector)); }
}

/** The card's fixed elements, the page script and its logic, with holen and senden answering from `answers`. */
function setup(answers) {
  const root = new FakeElement("section");
  for (const id of CARD_IDS) {
    const element = new FakeElement(id === "sprache-app" ? "select" : "div");
    element.setAttribute("id", id);
    root.append(element);
  }
  const doc = {
    createElement: tag => new FakeElement(tag),
    createTextNode: text => new FakeText(text),
    getElementById: id => root.querySelector(`#${id}`),
    querySelectorAll: selector => root.querySelectorAll(selector),
    listeners: {},
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    dispatchEvent(event) { for (const handler of this.listeners[event.type] || []) handler(event); return true; },
  };
  const calls = { holen: 0, senden: [], failures: [], statuses: [] };
  function el(tag, attributes = {}, ...children) {
    const element = doc.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (value === false || value === null || value === undefined) continue;
      if (name === "class") element.className = value;
      else element.setAttribute(name, value === true ? "" : value);
    }
    for (const child of children.flat()) if (child !== null && child !== undefined && child !== false) element.append(child);
    return element;
  }
  const answer = next => (next instanceof Error ? Promise.reject(next) : Promise.resolve(next));
  const window = {
    App: {
      el,
      holen: () => { calls.holen += 1; return answer(answers.holen.shift()); },
      senden: (route, body) => { calls.senden.push(JSON.parse(JSON.stringify(body))); return answer(answers.senden.shift()); },
      status: (line, text, kind) => calls.statuses.push([text, kind]),
    },
    Meldungen: {
      showFailure: (line, field, error) => calls.failures.push(error.message),
      clearInputError: () => {},
    },
    DotLine: require("../seiten/dot-line.js"),
    Texte: require("../seiten/texte.js"),  // loaded first on the page, as in einstellungen.html
  };
  class CustomEvent { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } }
  const context = { window, document: doc, console, CustomEvent };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "sprache-logik.js"), "utf8"), context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "sprache.js"), "utf8"), context);
  return { root, doc, calls, boxes: () => root.querySelectorAll('input[name="bewerbungssprache"]') };
}

const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const refusal = message => Object.assign(new Error(message), { status: 400 });

test("a refused change redraws the state the server last sent, without asking the server again", async () => {
  const answers = { holen: [SUGGESTED, new Error("the server is gone")], senden: [refusal("Bitte mindestens eine Sprache.")] };
  const page = setup(answers);
  await settle();
  const [, english] = page.boxes();
  assert.equal(english.checked, true, "the suggestion is drawn");

  english.checked = false;
  english.dispatch("change");
  await settle();

  assert.deepEqual(page.calls.senden, [{ bewerbung: ["de"] }]);
  assert.deepEqual(page.calls.failures, ["Bitte mindestens eine Sprache."]);
  assert.equal(page.calls.holen, 1, "the stored state comes from the last answer, not from a new request");
  assert.deepEqual(page.boxes().map(box => box.checked), [true, true, false], "the boxes show the stored choice again");
});

test("a suggested language has its note on its own line, described by it, not inside the label", async () => {
  const page = setup({ holen: [SUGGESTED], senden: [] });
  await settle();
  const [german, english, french] = page.boxes();
  const note = page.root.querySelector("#sprache-hinweis-en");

  assert.equal(note.textContent, "vorgeschlagen: im Lebenslauf «Fliessend»");
  assert.equal(note.hidden, false);
  assert.ok(note.className.split(" ").includes("field__hint"), "hint style");
  assert.equal(english.getAttribute("aria-describedby"), "sprache-hinweis-en");
  assert.equal(english.parentElement.tagName, "LABEL");
  assert.equal(english.parentElement.textContent, "Englisch", "the label names the language only");
  assert.ok(!english.parentElement.all().includes(note), "the note stands outside the label");
  for (const box of [german, french]) {
    assert.equal(box.getAttribute("aria-describedby"), null);
    assert.equal(page.root.querySelector(`#sprache-hinweis-${box.value}`).hidden, true);
  }
});

test("the first change to a box saves every visible box, and the notes go away", async () => {
  const page = setup({ holen: [SUGGESTED], senden: [CHOSEN] });
  await settle();
  const french = page.boxes()[2];

  french.checked = true;
  french.dispatch("change");
  await settle();

  assert.deepEqual(page.calls.senden, [{ bewerbung: ["de", "en", "fr"] }]);
  assert.deepEqual(page.calls.statuses, [["Bewerbungssprachen gespeichert.", "ok"]]);
  assert.deepEqual(page.boxes().map(box => box.checked), [true, true, true]);
  for (const box of page.boxes()) {
    assert.equal(box.getAttribute("aria-describedby"), null);
    assert.equal(page.root.querySelector(`#sprache-hinweis-${box.value}`).hidden, true);
  }
});

test("the translation line speaks the chosen language and carries its lang, German shows none", async () => {
  const french = { ...SUGGESTED, app: "fr", app_gewaehlt: true };
  const page = setup({ holen: [french], senden: [{ ...french, app: "de" }] });
  await settle();
  const line = page.root.querySelector("#sprache-folgt");

  assert.equal(line.textContent, "La traduction arrive bientôt. D'ici là, l'application reste en allemand.");
  assert.equal(line.getAttribute("lang"), "fr");
  assert.equal(line.hidden, false);

  const select = page.root.querySelector("#sprache-app");
  select.value = "de";
  select.dispatch("change");
  await settle();

  assert.deepEqual(page.calls.senden, [{ app: "de" }]);
  assert.equal(line.hidden, true);
  assert.equal(line.textContent, "");
  assert.equal(line.getAttribute("lang"), null);
});

test("the card tells the language switch what it saved and follows a choice made there (#435)", async () => {
  const french = { ...SUGGESTED, app: "fr", app_gewaehlt: true };
  const page = setup({ holen: [SUGGESTED], senden: [french] });
  const told = [];
  page.doc.addEventListener("sprache-gespeichert", event => told.push(event.detail.app));
  await settle();

  const select = page.root.querySelector("#sprache-app");
  select.value = "fr";
  select.dispatch("change");
  await settle();
  assert.deepEqual(told, ["fr"]);

  page.doc.dispatchEvent({ type: "sprache-gespeichert", detail: { ...SUGGESTED, app: "en", app_gewaehlt: true } });
  assert.equal(select.value, "en");
  assert.equal(page.root.querySelector("#sprache-folgt").getAttribute("lang"), "en");
});
