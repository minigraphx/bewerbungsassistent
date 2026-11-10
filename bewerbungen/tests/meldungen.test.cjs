// Status messages behave the same on every page (#215): warnings and errors can be closed and stay until then,
// other messages fade after about eight seconds unless the pointer or the focus is on them.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const meldungen = require("../seiten/meldungen.js");

const SEITEN = path.join(__dirname, "..", "seiten");

// A small fake DOM: only what the helper may use.
class FakeText {
  constructor(text) { this.textContent = String(text); this.parentNode = null; }
}

class FakeElement {
  constructor(document, tag) {
    this.ownerDocument = document;
    this.tagName = tag.toUpperCase();
    this.childNodes = [];
    this.parentNode = null;
    this.dataset = {};
    this.attributes = {};
    this.listeners = {};
    this.classes = new Set();
    this.classList = {
      add: (...names) => names.forEach(n => this.classes.add(n)),
      remove: (...names) => names.forEach(n => this.classes.delete(n)),
      contains: name => this.classes.has(name),
      toggle: (name, on) => (on ? this.classes.add(name) : this.classes.delete(name)),
    };
  }
  get className() { return [...this.classes].join(" "); }
  set className(value) { this.classes = new Set(String(value).split(/\s+/).filter(Boolean)); }
  get textContent() { return this.childNodes.map(n => n.textContent).join(""); }
  set textContent(value) { this.replaceChildren(...(value === "" ? [] : [new FakeText(value)])); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return name in this.attributes ? this.attributes[name] : null; }
  removeAttribute(name) { delete this.attributes[name]; }
  append(...nodes) {
    for (const node of nodes) {
      const child = typeof node === "string" ? new FakeText(node) : node;
      child.parentNode = this;
      this.childNodes.push(child);
    }
  }
  replaceChildren(...nodes) { this.childNodes = []; this.append(...nodes); }
  contains(node) {
    for (let n = node; n; n = n.parentNode) if (n === this) return true;
    return false;
  }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  fire(type, init = {}) {
    for (let n = this; n; n = n.parentNode) for (const h of n.listeners?.[type] || []) h({ type, target: this, ...init });
  }
  find(tag) {
    for (const child of this.childNodes) {
      if (child.tagName === tag) return child;
      const inner = child.find?.(tag);
      if (inner) return inner;
    }
    return null;
  }
}

function fakeDocument() {
  const document = { activeElement: null };
  document.createElement = tag => new FakeElement(document, tag);
  document.createTextNode = text => new FakeText(text);
  return document;
}

const zeile = (klasse = "status-line") => {
  const element = fakeDocument().createElement("p");
  element.className = klasse;
  return element;
};
const knopf = element => element.find("BUTTON");
const SCHLIESSEN = "Meldung schliessen";

test.beforeEach(context => context.mock.timers.enable({ apis: ["setTimeout"] }));

test("an error shows a close button and stays until it is used", context => {
  const element = zeile();

  meldungen.zeige(element, "Speichern fehlgeschlagen", "fehler");
  context.mock.timers.tick(60_000);

  assert.equal(element.dataset.level, "danger");
  assert.match(element.textContent, /Speichern fehlgeschlagen/);
  const schliessen = knopf(element);
  assert.equal(schliessen.getAttribute("aria-label"), SCHLIESSEN);
  assert.equal(schliessen.getAttribute("type"), "button");
  assert.equal(schliessen.getAttribute("tabindex"), null);  // a button: reachable with the keyboard
  schliessen.fire("click");
  assert.equal(element.textContent, "");
  assert.equal(element.dataset.level, undefined);
});

test("a warning can be closed as well and keeps its level", context => {
  const element = zeile();

  meldungen.zeige(element, "Nicht gespeichert", "hinweis");
  context.mock.timers.tick(60_000);

  assert.equal(element.dataset.level, "warning");
  assert.equal(knopf(element).getAttribute("aria-label"), SCHLIESSEN);
});

for (const [stufe, level] of [["ok", "success"], ["success", "success"], ["", undefined]]) {
  test(`a ${stufe || "neutral"} message fades after about eight seconds and has nothing to close`, context => {
    const element = zeile();

    meldungen.zeige(element, "Gespeichert", stufe);
    assert.equal(knopf(element), null);
    assert.equal(element.dataset.level, level);
    context.mock.timers.tick(meldungen.AUSBLENDEN_MS - 100);
    assert.equal(element.textContent, "Gespeichert");
    context.mock.timers.tick(100);

    assert.equal(element.textContent, "");
  });
}

test("the pointer on a message keeps it until the pointer leaves", context => {
  const element = zeile();
  meldungen.zeige(element, "Gespeichert", "ok");

  element.fire("mouseenter");
  context.mock.timers.tick(meldungen.AUSBLENDEN_MS * 3);
  assert.equal(element.textContent, "Gespeichert");
  element.fire("mouseleave");

  assert.equal(element.textContent, "");
});

test("the focus inside a message keeps it until the focus leaves", context => {
  const element = zeile();
  meldungen.zeige(element, "Gespeichert", "ok");

  element.fire("focusin");
  context.mock.timers.tick(meldungen.AUSBLENDEN_MS * 3);
  assert.equal(element.textContent, "Gespeichert");
  element.fire("focusout", { relatedTarget: null });

  assert.equal(element.textContent, "");
});

test("a focused button that is removed takes the focus with it, so the next message fades", context => {
  const element = zeile();
  meldungen.zeige(element, "Fehler", "fehler");
  const schliessen = knopf(element);

  schliessen.fire("focusin");
  schliessen.fire("click");  // the button is gone; browsers send no focusout the line can rely on
  meldungen.zeige(element, "Gespeichert", "ok");
  context.mock.timers.tick(meldungen.AUSBLENDEN_MS);

  assert.equal(element.textContent, "");
});

test("an action used with the keyboard lets its own success fade", context => {
  const element = zeile();
  meldungen.zeige(element, "Der Browser lädt die Sicherung herunter.", "", {
    aktion: { text: "Datei ist gespeichert", ausfuehren: () => meldungen.zeige(element, "Danke, vermerkt.", "ok") },
  });
  const aktion = element.childNodes.find(n => n.textContent === "Datei ist gespeichert");

  aktion.fire("focusin");
  aktion.fire("click");
  assert.equal(element.textContent, "Danke, vermerkt.");
  context.mock.timers.tick(meldungen.AUSBLENDEN_MS);

  assert.equal(element.textContent, "");
});

test("the pointer that leaves before the time is up leaves the message its time", context => {
  const element = zeile();
  meldungen.zeige(element, "Gespeichert", "ok");

  element.fire("mouseenter");
  element.fire("mouseleave");
  context.mock.timers.tick(meldungen.AUSBLENDEN_MS - 100);

  assert.equal(element.textContent, "Gespeichert");
});

test("a newer message replaces the older one and gets its own time", context => {
  const element = zeile();
  meldungen.zeige(element, "Erste", "ok");
  context.mock.timers.tick(meldungen.AUSBLENDEN_MS - 1000);

  meldungen.zeige(element, "Zweite", "ok");
  context.mock.timers.tick(2000);
  assert.equal(element.textContent, "Zweite");

  meldungen.zeige(element, "Fehler danach", "fehler");
  context.mock.timers.tick(meldungen.AUSBLENDEN_MS * 2);
  assert.match(element.textContent, /Fehler danach/);
});

test("a success after an error takes the close button away", () => {
  const element = zeile();
  meldungen.zeige(element, "Fehler", "fehler");

  meldungen.zeige(element, "Gespeichert", "ok");

  assert.equal(knopf(element), null);
  assert.equal(element.dataset.level, "success");
});

test("a message with an action stays until the action is used", context => {
  const element = zeile();
  let used = 0;

  meldungen.zeige(element, "Der Browser lädt die Sicherung herunter.", "", { aktion: { text: "Datei ist gespeichert", ausfuehren: () => { used += 1; } } });
  context.mock.timers.tick(60_000);
  assert.match(element.textContent, /Datei ist gespeichert/);
  const buttons = element.childNodes.filter(n => n.tagName === "BUTTON");
  assert.equal(buttons.length, 2);  // the action and the close button
  buttons.find(b => b.textContent === "Datei ist gespeichert").fire("click");

  assert.equal(used, 1);
  assert.equal(element.textContent, "");
});

test("a message with an action can be closed without using it", () => {
  const element = zeile();
  let used = 0;
  meldungen.zeige(element, "Bitte bestätigen", "", { aktion: { text: "Ja", ausfuehren: () => { used += 1; } } });

  element.childNodes.find(n => n.getAttribute?.("aria-label") === SCHLIESSEN).fire("click");

  assert.equal(used, 0);
  assert.equal(element.textContent, "");
});

test("an empty text clears the message", () => {
  const element = zeile();
  meldungen.zeige(element, "Fehler", "fehler");

  meldungen.zeige(element, "");

  assert.equal(element.textContent, "");
  assert.equal(element.dataset.level, undefined);
});

test("a message can be a node as well as a text", () => {
  const element = zeile();
  const link = element.ownerDocument.createElement("a");
  link.append("Anleitung");

  meldungen.zeige(element, ["Siehe ", link], "hinweis");

  assert.match(element.textContent, /^Siehe Anleitung/);
});

test("lines of the older kind keep their class for the look", () => {
  const element = zeile("status");

  meldungen.zeige(element, "Fehler", "fehler");
  assert.ok(element.classList.contains("fehler") && element.classList.contains("status"));
  meldungen.zeige(element, "Gut", "ok");
  assert.ok(element.classList.contains("ok") && !element.classList.contains("fehler"));
});

// Every page uses the one helper

const scripts = fs.readdirSync(SEITEN).filter(name => name.endsWith(".js") && name !== "meldungen.js");
const pages = fs.readdirSync(SEITEN).filter(name => name.endsWith(".html"));

test("no page sets the level or the class of a message itself", () => {
  for (const name of scripts) {
    const code = fs.readFileSync(path.join(SEITEN, name), "utf8");
    assert.doesNotMatch(code, /\.dataset\.level\s*=(?!=)|delete [^;]*\.dataset\.level|className\s*=\s*["'`]status/, name);
  }
});

test("every page loads the helper before app.js", () => {
  for (const name of pages) {
    const html = fs.readFileSync(path.join(SEITEN, name), "utf8");
    const helper = html.indexOf('<script src="/meldungen.js"></script>');
    assert.ok(helper >= 0 && helper < html.indexOf('<script src="/app.js"></script>'), name);
  }
});
