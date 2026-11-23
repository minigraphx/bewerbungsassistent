// The notice of /suchbegriffe (#348): a failed proposal says «Kein Vorschlag» once, since the server text (FAILED in
// routes_terms.py) already starts with it; notices with a title of their own keep it. Small stand-in DOM.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Texte = require("../seiten/texte.js");
const DotLine = require("../seiten/dot-line.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const PROPOSAL = "/api/suchbegriffe/vorschlag";
const FAILED = "Kein Vorschlag. Die Antwort der KI liess sich nicht lesen. Berechnet: CHF 0.03. "
  + "Am Suchprofil hat sich nichts geändert.";
const HINT = { verfuegbar: true, treffer: 40, seit: "2026-11-01" };

class FakeNode {}

class FakeText extends FakeNode {
  constructor(text) { super(); this.data = String(text); }
  get textContent() { return this.data; }
}

class FakeElement extends FakeNode {
  constructor(tag) {
    super();
    Object.assign(this, { tagName: tag.toUpperCase(), attrs: new Map(), children: [], listeners: {}, className: "" });
  }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  removeAttribute(name) { this.attrs.delete(name); }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  append(...nodes) { for (const node of nodes) this.children.push(node instanceof FakeNode ? node : new FakeText(node)); }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  get textContent() { return this.children.map(child => child.textContent).join(""); }
  set textContent(text) { this.replaceChildren(String(text)); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  click() { for (const handler of this.listeners.click || []) handler(); }
  querySelectorAll() { return []; }
  /** Only a tag name as selector: the first such element below this one, depth first. */
  querySelector(tag) {
    for (const child of this.children.filter(node => node instanceof FakeElement)) {
      if (child.tagName === tag.toUpperCase()) return child;
      const below = child.querySelector(tag);
      if (below) return below;
    }
    return null;
  }
  focus() { focused = this; }
}

let focused = null;  // the stand-in for document.activeElement, reset with each page

function el(tag, attributes = {}, ...children) {
  const element = new FakeElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    if (name === "class") element.className = value;
    else if (typeof value === "function") element.addEventListener(name.replace(/^on/, ""), value);
    else element.setAttribute(name, value);
  }
  for (const child of children.flat()) if (child !== null && child !== undefined && child !== false) element.append(child);
  return element;
}

const settled = async () => {
  for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve));
};

/**
 * Runs suchbegriffe.js; `answers` maps a route to its answer, an Error (the route refused) or a function giving one
 * per call. Gives the elements and the bodies sent to the proposal route.
 */
async function opened(answers) {
  focused = null;
  const elements = new Map();
  const doc = {
    getElementById(id) {
      // #meldung starts as in suchbegriffe.html, so a neutral notice after a warning has to undo it
      if (!elements.has(id)) elements.set(id, el("div", id === "meldung" ? { class: "notice" } : {}));
      return elements.get(id);
    },
  };
  const sent = [];
  const answer = async (route, body) => {
    if (route === PROPOSAL) sent.push(body);
    if (!(route in answers)) throw new Error(`unexpected route ${route}`);
    const found = typeof answers[route] === "function" ? answers[route]() : answers[route];
    if (found instanceof Error) throw found;
    return found;
  };
  const window = {
    App: { el, holen: answer, senden: answer, status: () => {}, textsatz: async () => "stelle-sie" },
    Texte,
    DotLine,
    TrefferLogik: { costLine: () => ({ text: "", usedUp: false }), estimateFailedText: text => text },
    Meldungen: { clearInputError() {} },
    Einwilligung: { zeile() {} },
  };
  const context = { window, document: doc, console, setTimeout };
  vm.createContext(context);
  for (const name of ["suchbegriffe-logik.js", "suchbegriffe-schalter.js", "suchbegriffe-gezaehlt.js", "suchbegriffe.js"]) {
    vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  }
  await settled();
  return { $: id => doc.getElementById(id), sent, focused: () => focused };
}

/** What a sighted person reads in a part of the notice: hidden parts drop out. */
const shown = node => (node instanceof FakeElement ? (node.hidden ? "" : node.children.map(shown).join(" ")) : node.data);

const buttonsOf = page => page.$("meldung-knoepfe").children;

test("a failed proposal shows the server text once, without the separate title «Kein Vorschlag»", async () => {
  const page = await opened({ "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
    [PROPOSAL]: new Error(FAILED) });
  assert.equal(page.$("meldung").hidden, false);
  const notice = ["meldung-titel", "meldung-text", "meldung-knoepfe"].map(id => shown(page.$(id))).join(" ");
  assert.equal(notice.split("Kein Vorschlag").length - 1, 1, `«Kein Vorschlag» once in: ${notice}`);
  assert.equal(page.$("meldung-titel").hidden, true, "an empty title is hidden, so it takes no place");
  assert.equal(page.$("meldung-titel").textContent, "");
  assert.equal(page.$("meldung-text").textContent, FAILED);
  assert.deepEqual(buttonsOf(page).map(button => button.textContent), ["Nochmals versuchen"]);
});

test("«Nochmals versuchen» asks again with the same body, and a second failure is still one notice", async () => {
  const page = await opened({ "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
    [PROPOSAL]: new Error(FAILED) });
  buttonsOf(page)[0].click();
  await settled();
  assert.equal(JSON.stringify(page.sent), "[{},{}]");
  assert.equal(page.$("meldung-titel").hidden, true);
  assert.equal(page.$("meldung-text").textContent, FAILED);
  assert.deepEqual(buttonsOf(page).map(button => button.textContent), ["Nochmals versuchen"]);
  assert.equal(page.$("meldung").className, "notice notice--warning");
  assert.equal(page.focused(), buttonsOf(page)[0], "the focus is on the new «Nochmals versuchen»");
});

test("a failed proposal is a warning, and screen readers hear it from «Nochmals versuchen», which takes the focus",
  async () => {
    const page = await opened({ "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
      [PROPOSAL]: new Error(FAILED) });
    assert.equal(page.$("meldung").className, "notice notice--warning");
    assert.equal(page.$("meldung-titel").hidden, true);
    const retry = buttonsOf(page)[0];
    assert.equal(retry.textContent, "Nochmals versuchen");
    assert.equal(retry.getAttribute("aria-describedby"), "meldung-text", "the button is described by the server text");
    assert.equal(page.focused(), retry, "#meldung is no live region, so the focus brings the text to screen readers");
  });

test("a notice after the failed proposal, like «Vorschlag verworfen», is neutral again and shows its title", async () => {
  const page = await opened({ "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
    [PROPOSAL]: new Error(FAILED) });
  page.$("verwerfen").click();
  assert.equal(page.$("meldung").className, "notice");
  assert.equal(page.$("meldung-titel").hidden, false);
  // The title has its own key since the UI/UX ruling of #425, so it no longer shares «Verworfen» with the jobs page
  assert.equal(page.$("meldung-titel").textContent, "Vorschlag verworfen");
  assert.equal(page.$("meldung-text").textContent, "Am Suchprofil hat sich nichts geändert.");
  assert.equal(buttonsOf(page)[0].getAttribute("aria-describedby"), null, "only the retry is described by the text");
});

test("a notice with a real title shows it again after the failed proposal hid it", async () => {
  let calls = 0;
  const page = await opened({ "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
    [PROPOSAL]: () => {
      calls += 1;
      return calls === 1 ? new Error(FAILED) : new Promise(() => {});
    } });
  buttonsOf(page)[0].click();
  await settled();
  page.$("abbrechen").click();
  assert.equal(page.$("meldung").className, "notice", "a cancel is no warning");
  assert.equal(page.$("meldung-titel").hidden, false);
  assert.equal(page.$("meldung-titel").textContent, "Abgebrochen");
  assert.equal(page.$("meldung-text").textContent, "Am Suchprofil hat sich nichts geändert.");
  assert.deepEqual(buttonsOf(page).map(button => button.textContent), ["Neu vorschlagen"]);
});

test("the notice for an apprenticeship search keeps its title", async () => {
  const page = await opened({ "/api/suchbegriffe/hinweis": { verfuegbar: false } });
  assert.equal(page.$("meldung-titel").hidden, false);
  assert.equal(page.$("meldung").className, "notice");
  assert.equal(page.$("meldung-titel").textContent, "Nur bei der Stellensuche");
  assert.equal(page.$("meldung-text").textContent, "Suchbegriffe prüfen gibt es vorerst nur bei der Stellensuche.");
});

test("the consent notice has no title, so none takes place", async () => {
  const page = await opened({ "/api/suchbegriffe/hinweis": HINT,
    "/api/ki/status": { einwilligung: { erteilt: false } } });
  assert.equal(page.$("meldung").hidden, false);
  assert.equal(page.$("meldung").className, "notice");
  assert.equal(page.$("meldung-titel").hidden, true);
  assert.notEqual(page.$("meldung-text").textContent, "");
});
