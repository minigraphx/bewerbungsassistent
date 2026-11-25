// The language switch beside the card (#435, G10): Deutsch, Français, English in the sidebar of every page and on
// Einrichtung, in a small stand-in DOM. It writes the same setting as the card (/api/sprachen, app); until #434
// switches the translation on it stores, moves the marking and says the translation is coming, without reloading.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SEITEN = path.join(__dirname, "..", "seiten");
const logic = require("../seiten/sprache-logik.js");
const LABEL = "Sprache · Langue · Language";
const GERMAN = { app: "de", app_gewaehlt: false, bewerbung: ["de"], bewerbung_gewaehlt: false, vorschlag: [], uebersetzung: false };
const FRENCH = { ...GERMAN, app: "fr", app_gewaehlt: true };
const ENGLISH = { ...GERMAN, app: "en", app_gewaehlt: true };

class FakeText {
  constructor(text) { this.data = String(text); this.parent = null; }
  get textContent() { return this.data; }
}

class FakeElement {
  constructor(tag, doc) {
    Object.assign(this, { tagName: tag.toUpperCase(), attrs: new Map(), children: [], parent: null, listeners: {},
      className: "", doc });
  }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  hasAttribute(name) { return this.attrs.has(name); }
  removeAttribute(name) { this.attrs.delete(name); }
  get id() { return this.getAttribute("id") || ""; }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  get dataset() {
    const element = this;
    return new Proxy({}, { get: (_, key) => element.getAttribute(`data-${String(key)}`) ?? undefined });
  }
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
  click() { for (const handler of this.listeners.click || []) handler({ type: "click", target: this }); }
  focus() { this.doc.activeElement = this; }
  all() { return this.children.filter(c => c instanceof FakeElement).flatMap(c => [c, ...c.all()]); }
  matches(selector) {
    if (selector.startsWith(".")) return this.className.split(/\s+/).includes(selector.slice(1));
    if (selector.startsWith("#")) return this.id === selector.slice(1);
    return this.tagName === selector.toUpperCase();
  }
  querySelector(selector) { return this.all().find(node => node.matches(selector)) || null; }
  querySelectorAll(selector) { return this.all().filter(node => node.matches(selector)); }
}

/**
 * A page with the sidebar's switch and, with `setup`, the copy in the header of Einrichtung; the logic and the switch
 * script, with holen and senden answering from `answers` and a sessionStorage that can be preset or blocked.
 */
function page(answers, { setup = false, pathname = "/", stored = {}, blocked = false } = {}) {
  const doc = { activeElement: null, listeners: {} };
  const root = new FakeElement("body", doc);
  const host = (id, className) => {
    const group = new FakeElement("div", doc);
    group.setAttribute("id", id);
    group.className = className;
    group.setAttribute("role", "group");
    group.hidden = true;
    const icon = new FakeElement("svg", doc);
    icon.setAttribute("aria-hidden", "true");
    group.append(icon);
    const line = new FakeElement("div", doc);
    line.setAttribute("id", `${id}-status`);
    line.setAttribute("role", "status");
    root.append(group, line);
    return group;
  };
  const nav = host("nav-language", "app-nav__language language-switch");
  const header = setup ? host("setup-language", "language-switch") : null;
  Object.assign(doc, {
    createElement: tag => new FakeElement(tag, doc),
    createTextNode: text => new FakeText(text),
    getElementById: id => root.querySelector(`#${id}`),
    querySelector: selector => root.querySelector(selector),
    addEventListener: (type, handler) => { (doc.listeners[type] ||= []).push(handler); },
    dispatchEvent: event => { for (const handler of doc.listeners[event.type] || []) handler(event); return true; },
  });
  const calls = { holen: [], senden: [], failures: [], shown: [], reloads: 0, events: [] };
  doc.addEventListener("sprachwahl-neuladen", event => calls.events.push(event.type));
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
  const storage = new Map(Object.entries(stored));
  const sessionStorage = {
    getItem: key => { if (blocked) throw new Error("blocked"); return storage.has(key) ? storage.get(key) : null; },
    setItem: (key, value) => { if (blocked) throw new Error("blocked"); storage.set(key, String(value)); },
    removeItem: key => { if (blocked) throw new Error("blocked"); storage.delete(key); },
  };
  const location = { pathname, hash: "#gesucht", reload: () => { calls.reloads += 1; } };
  class Event { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } }
  const window = {
    App: {
      el,
      holen: route => { calls.holen.push(route); return answer(answers.holen.shift()); },
      senden: (route, body) => { calls.senden.push([route, JSON.parse(JSON.stringify(body))]); return answer(answers.senden.shift()); },
    },
    Meldungen: {
      leere: line => line.replaceChildren(),
      zeige: (line, text, level) => { calls.shown.push([text, level]); line.replaceChildren(el("span", { class: "status__text" }, text)); },
      showFailure: (line, field, error) => { calls.failures.push([field.id, error.message]); line.replaceChildren(error.message); },
    },
    Texte: require("../seiten/texte.js"),
  };
  const context = { window, document: doc, location, sessionStorage, Event, CustomEvent: Event, console };
  window.SpracheLogik = logic;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "sprachwahl.js"), "utf8"), context);
  const options = group => group.querySelectorAll(".language-switch__option");
  return { doc, nav, header, calls, storage, window, options, line: group => doc.getElementById(`${group.id}-status`) };
}

const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const pressed = buttons => buttons.map(button => button.getAttribute("aria-pressed"));

// Logic

test("the switch names each language in its own language and marks the stored one", () => {
  const view = logic.switchView(FRENCH);
  assert.equal(view.app, "fr");
  assert.deepEqual(view.options.map(({ value, label, lang, pressed: on }) => [value, label, lang, on]),
                   [["de", "Deutsch", "de", false], ["fr", "Français", "fr", true], ["en", "English", "en", false]]);
  assert.equal(logic.switchView({ app: "it" }).app, "de", "an unknown value counts as German");
  assert.equal(logic.switchView(null).app, "de");
});

test("the group label is the same in the three languages and is no catalog text", () => {
  assert.equal(logic.SWITCH_LABEL, LABEL);
});

test("until the translation is on, French and English say in their language that it is coming", () => {
  assert.deepEqual(logic.switchView(FRENCH).pending, logic.PENDING_TRANSLATION.fr);
  assert.deepEqual(logic.switchView(ENGLISH).pending, logic.PENDING_TRANSLATION.en);
  assert.equal(logic.switchView(GERMAN).pending, null);
  assert.equal(logic.switchView({ ...FRENCH, uebersetzung: true }).pending, null, "after #434 the page itself is French");
  assert.equal(logic.switchView(FRENCH).translated, false);
  assert.equal(logic.switchView({ ...FRENCH, uebersetzung: true }).translated, true);
});

test("a data folder that keeps its own app language says so, naming it in its own language", () => {
  assert.equal(logic.folderNote({ ergebnis: "eigene", app: "en" }),
               "In diesem Ordner war schon eine Sprache der App gespeichert: English. Sie gilt jetzt.");
  assert.equal(logic.folderNote({ ergebnis: "uebernommen", app: "fr" }), null, "a carried language needs no note");
  assert.equal(logic.folderNote(null), null);
  assert.equal(logic.folderNote({ ergebnis: "eigene", app: "it" }), null);
});

// The switch on a page

test("the sidebar shows the three languages as buttons in a labelled group, the stored one pressed", async () => {
  const shown = page({ holen: [FRENCH], senden: [] });
  await settle();
  const buttons = shown.options(shown.nav);
  assert.equal(shown.nav.hidden, false);
  assert.equal(shown.nav.getAttribute("aria-label"), LABEL);
  assert.equal(shown.nav.getAttribute("role"), "group");
  assert.equal(shown.nav.querySelector("svg").getAttribute("aria-hidden"), "true", "the globe stays, hidden");
  assert.deepEqual(buttons.map(button => [button.textContent, button.getAttribute("lang"), button.tagName, button.getAttribute("type")]),
                   [["Deutsch", "de", "BUTTON", "button"], ["Français", "fr", "BUTTON", "button"], ["English", "en", "BUTTON", "button"]]);
  assert.deepEqual(pressed(buttons), ["false", "true", "false"]);
  assert.ok(buttons.every(button => !button.hasAttribute("disabled")), "the current language is never disabled");
  assert.deepEqual(shown.calls.holen, ["/api/sprachen"]);
});

test("on Einrichtung the switch sits in the header and the sidebar copy stays hidden", async () => {
  const shown = page({ holen: [GERMAN], senden: [] }, { setup: true, pathname: "/einrichtung" });
  await settle();
  assert.equal(shown.header.hidden, false);
  assert.equal(shown.header.getAttribute("aria-label"), LABEL);
  assert.equal(shown.options(shown.header).length, 3);
  assert.equal(shown.nav.hidden, true);
  assert.equal(shown.options(shown.nav).length, 0, "never two switches");
});

test("the switch stays hidden when the setting cannot be read", async () => {
  const shown = page({ holen: [new Error("the app is closing")], senden: [] });
  await settle();
  assert.equal(shown.nav.hidden, true);
});

test("before #434 a click stores the language, moves the marking and says the translation is coming, without reload", async () => {
  const shown = page({ holen: [GERMAN], senden: [FRENCH, GERMAN] });
  await settle();
  const [german, french] = shown.options(shown.nav);

  french.click();
  await settle();

  assert.deepEqual(shown.calls.senden, [["/api/sprachen", { app: "fr" }]], "the same route and setting as the card");
  assert.equal(shown.calls.reloads, 0);
  assert.deepEqual(pressed(shown.options(shown.nav)), ["false", "true", "false"]);
  const line = shown.line(shown.nav);
  assert.equal(line.textContent, logic.PENDING_TRANSLATION.fr.text);
  assert.equal(line.querySelector(".status__text").getAttribute("lang"), "fr");

  german.click();
  await settle();
  assert.deepEqual(shown.calls.senden[1], ["/api/sprachen", { app: "de" }]);
  assert.equal(line.textContent, "", "choosing Deutsch clears the line");
  assert.deepEqual(pressed(shown.options(shown.nav)), ["true", "false", "false"]);
});

test("a stored French choice shows its line on every page, as the card does", async () => {
  const shown = page({ holen: [FRENCH], senden: [] });
  await settle();
  assert.equal(shown.line(shown.nav).textContent, logic.PENDING_TRANSLATION.fr.text);
});

test("clicking the current language sends nothing", async () => {
  const shown = page({ holen: [ENGLISH], senden: [] });
  await settle();
  shown.options(shown.nav)[2].click();
  await settle();
  assert.deepEqual(shown.calls.senden, []);
});

test("a failed save keeps the old marking, says why in the status line and does not reload", async () => {
  const shown = page({ holen: [GERMAN], senden: [Object.assign(new Error("Die App antwortet nicht."), { status: 500 })] });
  await settle();
  shown.options(shown.nav)[2].click();
  await settle();
  assert.deepEqual(pressed(shown.options(shown.nav)), ["true", "false", "false"]);
  assert.deepEqual(shown.calls.failures, [["nav-language", "Die App antwortet nicht."]]);
  assert.equal(shown.line(shown.nav).textContent, "Die App antwortet nicht.");
  assert.equal(shown.calls.reloads, 0);
});

test("after #434 a saved choice reloads the page, after telling the page and leaving a one-shot mark", async () => {
  const shown = page({ holen: [{ ...GERMAN, uebersetzung: true }], senden: [{ ...ENGLISH, uebersetzung: true }] },
                     { pathname: "/treffer" });
  await settle();
  shown.options(shown.nav)[2].click();
  await settle();
  assert.equal(shown.calls.reloads, 1);
  assert.deepEqual(shown.calls.events, ["sprachwahl-neuladen"], "Einrichtung keeps what is not saved yet");
  assert.equal(shown.storage.get("bewerbungsbegleiter.sprachwahl"), "/treffer");
});

test("after the reload the focus goes to the now current language, once", async () => {
  const shown = page({ holen: [{ ...ENGLISH, uebersetzung: true }], senden: [] },
                     { pathname: "/treffer", stored: { "bewerbungsbegleiter.sprachwahl": "/treffer" } });
  await settle();
  assert.equal(shown.doc.activeElement, shown.options(shown.nav)[2]);
  assert.equal(shown.storage.has("bewerbungsbegleiter.sprachwahl"), false);

  const other = page({ holen: [ENGLISH], senden: [] }, { pathname: "/", stored: { "bewerbungsbegleiter.sprachwahl": "/treffer" } });
  await settle();
  assert.equal(other.doc.activeElement, null, "a mark from another page moves no focus");
});

test("blocked storage neither breaks the switch nor the reload", async () => {
  const shown = page({ holen: [{ ...GERMAN, uebersetzung: true }], senden: [{ ...FRENCH, uebersetzung: true }] }, { blocked: true });
  await settle();
  assert.equal(shown.nav.hidden, false);
  shown.options(shown.nav)[1].click();
  await settle();
  assert.equal(shown.calls.reloads, 1);
});

test("a change of the card redraws the switch, and a choice in the switch tells the card", async () => {
  const shown = page({ holen: [GERMAN], senden: [ENGLISH] });
  const told = [];
  shown.doc.addEventListener("sprache-gespeichert", event => told.push(event.detail.app));
  await settle();
  shown.doc.dispatchEvent({ type: "sprache-gespeichert", detail: FRENCH });
  assert.deepEqual(pressed(shown.options(shown.nav)), ["false", "true", "false"]);
  shown.options(shown.nav)[2].click();
  await settle();
  assert.deepEqual(told, ["fr", "en"]);
});

test("Einrichtung asks the switch to read the folder's language again and shows the note", async () => {
  const shown = page({ holen: [FRENCH, GERMAN], senden: [] }, { setup: true, pathname: "/einrichtung" });
  await settle();
  await shown.window.Sprachwahl.refresh({ ergebnis: "eigene", app: "de" });
  assert.deepEqual(pressed(shown.options(shown.header)), ["true", "false", "false"]);
  assert.deepEqual(shown.calls.shown, [["In diesem Ordner war schon eine Sprache der App gespeichert: Deutsch. Sie gilt jetzt.", "hinweis"]]);
});
