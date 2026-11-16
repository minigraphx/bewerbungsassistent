// The cost of „Suchbegriffe prüfen lassen“ on Suche einstellen (#329), with a small stand-in DOM: the line beside the
// link is worded like „Alle prüfen“, the exclusions box and the CV suggestions, in every state of the estimate.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Texte = require("../seiten/texte.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ESTIMATE = "/api/suchbegriffe/schaetzung";
const OWN_KEY = { verfuegbar: true, anzahl: 1, kosten: 0.03, waehrung: "USD", guthaben: null, danach: null,
  dauer_minuten: 1, reicht_fuer: null };
const CODE = { ...OWN_KEY, kosten: 0.04, waehrung: "CHF", guthaben: 4.25, danach: 4.21 };

class FakeNode {}

class FakeText extends FakeNode {
  constructor(text) { super(); this.data = String(text); }
  get textContent() { return this.data; }
}

class FakeElement extends FakeNode {
  constructor(tag) {
    super();
    Object.assign(this, { tagName: tag.toUpperCase(), attrs: new Map(), children: [], listeners: {}, value: "",
      checked: false, className: "" });
  }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  hasAttribute(name) { return this.attrs.has(name); }
  removeAttribute(name) { this.attrs.delete(name); }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  append(...nodes) { for (const node of nodes) this.children.push(node instanceof FakeNode ? node : new FakeText(node)); }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  get textContent() { return this.children.map(child => child.textContent).join(""); }
  set textContent(text) { this.replaceChildren(String(text)); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  querySelectorAll() { return []; }
  focus() {}
}

function el(tag, attributes = {}, ...children) {
  const element = new FakeElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === "class") element.className = value;
    else element.setAttribute(name, value);
  }
  for (const child of children.flat()) if (child !== null && child !== undefined && child !== false) element.append(child);
  return element;
}

/** Runs suche-einstellen.js with the estimate `answer` (an Error: the route refused) and the rest stubbed. */
async function opened(answer) {
  const elements = new Map();
  const doc = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, el(id === "pruefen-knopf" ? "a" : "div", id === "pruefen-knopf" ? { href: "/suchbegriffe" } : {}));
      return elements.get(id);
    },
    addEventListener() {},
  };
  const routes = {
    "/api/suche/liste": { art: "stelle", einstellungen: { auto_bewerten: false, zuschauen: false }, grenze: 50, portale: [] },
    "/api/suche/rahmen": { pensum: "", ausschluss: [], titel_ausschluss: [], titel_positiv: [] },
    "/api/firmen/ausgeschlossen": { firmen: [] },
    "/api/suchbegriffe/hinweis": { verfuegbar: true, hinweis: null, kosten_usd: 0.03, waehrung: "USD" },
  };
  const window = {
    App: {
      el,
      holen: async route => {
        if (route === ESTIMATE) {
          if (answer instanceof Error) throw answer;
          return answer;
        }
        if (!(route in routes)) throw new Error(`unexpected route ${route}`);
        return routes[route];
      },
      senden: async () => ({}),
      status: () => {},
      textsatz: async () => "stelle-sie",
    },
    Texte: { ...Texte, anwenden: () => {} },
    SucheAnzeige: { regionText: () => "", titelfilterText: () => "", zusammenfassung: () => "" },
    SucheRahmenLogik: { titelfilterLeer: "" },
    SucheRahmen: { zeige: () => {} },
    Suchbegriffe: { zeige: () => {} },
    PortalWahl: { zeige: () => {} },
  };
  const context = { window, document: doc, console, setTimeout, CustomEvent: class {} };
  vm.createContext(context);
  for (const name of ["treffer-logik.js", "suchbegriffe-logik.js", "suche-einstellen.js"]) {
    vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  }
  for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve));
  return { box: doc.getElementById("pruefen-block"), line: doc.getElementById("pruefen-kosten"),
    link: doc.getElementById("pruefen-knopf") };
}

test("with an own key the line is the estimate line of Alle prüfen, in USD", async () => {
  const { box, line, link } = await opened(OWN_KEY);
  assert.equal(box.hidden, false);
  assert.equal(line.textContent, "Etwa USD 0.03 und 1 Minute.");
  assert.equal(link.getAttribute("href"), "/suchbegriffe");
  assert.equal(link.getAttribute("aria-disabled"), null);
});

test("with the mediation the line is in CHF and names what stays in the credit", async () => {
  const { line } = await opened(CODE);
  assert.equal(line.textContent, "Etwa CHF 0.04 und 1 Minute. Danach bleiben CHF 4.21 im Guthaben.");
});

test("over the credit the line says it may not be enough, and the link stays", async () => {
  const { line, link } = await opened({ ...CODE, guthaben: 0.02, danach: 0 });
  assert.equal(line.textContent, "Etwa CHF 0.04 und 1 Minute. Im Guthaben sind noch CHF 0.02, das reicht vielleicht nicht.");
  assert.equal(link.getAttribute("href"), "/suchbegriffe");
});

test("with the credit used up the line links where to ask for a new code, and the link is locked", async () => {
  const { line, link } = await opened({ ...CODE, guthaben: 0, danach: 0 });
  // The link carries a hidden „, öffnet neuen Tab“ for screen readers.
  assert.equal(line.textContent, "Etwa CHF 0.04 und 1 Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern, öffnet neuen Tab.");
  const request = line.children.find(child => child.tagName === "A");
  assert.equal(request.getAttribute("href"), Texte.CODE_REQUEST_URL);
  assert.equal(link.getAttribute("href"), null);
  assert.equal(link.getAttribute("aria-disabled"), "true");
});

test("a locked link stays in the tab order, so its reason is heard; an open link needs no tabindex", async () => {
  const locked = (await opened({ ...CODE, guthaben: 0, danach: 0 })).link;
  assert.equal(locked.getAttribute("tabindex"), "0");
  assert.equal(locked.getAttribute("role"), "link");
  const open = (await opened(CODE)).link;
  assert.equal(open.getAttribute("tabindex"), null);
  assert.equal(open.getAttribute("role"), null);
});

test("a failed estimate names its reason and keeps the link", async () => {
  const { box, line, link } = await opened(new Error("Der Lebenslauf lässt sich nicht lesen."));
  assert.equal(box.hidden, false);
  assert.equal(line.textContent, "Die Schätzung fehlt: Der Lebenslauf lässt sich nicht lesen.");
  assert.equal(link.getAttribute("href"), "/suchbegriffe");
});

test("an apprenticeship search has no check of the terms", async () => {
  const { box } = await opened({ verfuegbar: false });
  assert.equal(box.hidden, true);
});

test("the link is described by the line", () => {
  const html = fs.readFileSync(path.join(SEITEN, "suche-einstellen.html"), "utf8");
  const link = html.match(/<a [^>]*id="pruefen-knopf"[^>]*>/)[0];
  assert.match(link, /aria-describedby="pruefen-kosten"/);
  assert.match(html, /<span class="caption" id="pruefen-kosten">/);
});
