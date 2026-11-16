// The box „Vorschläge der KI“ in „Lebenslauf erstellen“ (#293, G75) with a small stand-in DOM: what it says in each
// state, where the focus goes around a request and what the live region hears. Invented data, the AI is faked.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Texte = require("../seiten/texte.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROUTE = "/api/lebenslauf/erstellen";
const COST = "Berechnet: 0.01 CHF.";
const FORM = {
  stand: "abc", ki: "bereit", eigene_variante: null,
  abschnitte: [
    { abschnitt: "work", titel: "Berufserfahrung", stationen: [
      { index: 0, titel: "Entwicklerin", zusatz: "Beispiel AG", zeit: "2019 – heute", gewaehlt: true },
      { index: 1, titel: "Junior", zusatz: "Muster GmbH", zeit: "2015 – 2019", gewaehlt: true },
    ] },
  ],
  berufsbezeichnung: "Entwicklerin", kurzprofil: "Erster Satz. Zweiter Satz.", design: "zweispaltig", bezeichnung: "Daten",
};
const SUGGESTION = { kosten_usd: 0.01, waehrung: "CHF", wiederholt: false, kosten_text: COST, empfehlungen: [
  { nummer: 0, was: "«Junior, Muster GmbH» weglassen", grund: "Keine Webstelle.",
    weglassen: [{ abschnitt: "work", index: 1 }], voran: [], kurzprofil: null },
  { nummer: 1, was: "Kurzprofil gekürzt", grund: "Kürzer liest sich besser.", weglassen: [], voran: [],
    kurzprofil: "Zweiter Satz." },
] };

class FakeNode {}

class FakeText extends FakeNode {
  constructor(text) { super(); this.data = String(text); this.parent = null; }
  get textContent() { return this.data; }
}

const kebab = name => name.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);

class FakeElement extends FakeNode {
  constructor(doc, tag) {
    super();
    Object.assign(this, { doc, tagName: tag.toUpperCase(), attrs: new Map(), children: [], parent: null, listeners: {},
      value: "", disabled: false, checked: false, className: "", open: false, scrolled: 0 });
  }
  setAttribute(name, value) {
    this.attrs.set(name, String(value));
    if (name === "checked") this.checked = true;
    if (name === "disabled") this.disabled = true;
  }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  hasAttribute(name) { return this.attrs.has(name); }
  removeAttribute(name) { this.attrs.delete(name); }
  get dataset() {
    return new Proxy({}, {
      get: (_, key) => this.getAttribute(`data-${kebab(String(key))}`) ?? undefined,
      set: (_, key, value) => { this.setAttribute(`data-${kebab(String(key))}`, value); return true; },
    });
  }
  get id() { return this.getAttribute("id") || ""; }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  append(...nodes) {
    for (const given of nodes) {
      const node = given instanceof FakeNode ? given : new FakeText(given);
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
    const event = { type, target: this, currentTarget: this, preventDefault() {} };
    for (let node = this; node; node = node.parent) for (const handler of node.listeners[type] || []) handler(event);
  }
  click() { if (!this.disabled) this.dispatch("click"); }
  focus() { this.doc.activeElement = this; }
  scrollIntoView() { this.scrolled += 1; }
  all() { return this.children.filter(c => c instanceof FakeElement).flatMap(c => [c, ...c.all()]); }
  matches(selector) { return selector === "[data-key]" ? this.hasAttribute("data-key") : this.tagName === selector.toUpperCase(); }
  querySelector(selector) { return this.all().find(node => node.matches(selector)) || null; }
  querySelectorAll(selector) { return this.all().filter(node => node.matches(selector)); }
}

/** The part of bewerbung.html the script works on. */
function page(doc, el) {
  return el("main", {},
    el("button", { id: "cv-erstellen-oeffnen", type: "button" }, "Lebenslauf erstellen"),
    el("div", { id: "cv-erstellen", hidden: true },
      el("section", { id: "cv-erstellen-ki", hidden: true },
        el("h5", { id: "cv-erstellen-ki-titel" }),
        el("p", { id: "cv-erstellen-ki-zeile" }),
        el("ul", { id: "cv-erstellen-ki-liste", hidden: true }),
        el("div", { id: "cv-erstellen-ki-knoepfe", hidden: true },
          el("button", { id: "cv-erstellen-ki-knopf", type: "button", class: "btn" }),
          el("button", { id: "cv-erstellen-ki-stellentext", type: "button", class: "btn btn--quiet", hidden: true })),
        el("p", { id: "cv-erstellen-ki-status", tabindex: "-1" }),
        el("details", { id: "cv-erstellen-ki-text" }, el("pre", { id: "cv-erstellen-ki-text-inhalt" }))),
      el("div", { id: "cv-erstellen-stationen" }),
      el("input", { id: "cv-erstellen-beruf" }), el("textarea", { id: "cv-erstellen-profil" }),
      el("div", { id: "cv-erstellen-designs" }), el("input", { id: "cv-erstellen-name" }),
      el("p", { id: "cv-erstellen-status" }), el("button", { id: "cv-erstellen-speichern" }),
      el("button", { id: "cv-erstellen-abbrechen" }), el("a", { id: "cv-erstellen-pdf" })),
    el("details", { id: "s-stelle" }, el("textarea", { id: "stellentext" })));
}

function setup({ form = FORM, satz = "stelle-sie" } = {}) {
  const doc = { activeElement: null, listeners: {}, createElement: tag => new FakeElement(doc, tag),
                addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
                dispatchEvent() {} };
  const calls = { senden: [], status: [], einrichten: 0 };
  const answers = { senden: [], form: [form] };
  function el(tag, attributes = {}, ...children) {
    const element = doc.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (value === false || value === null || value === undefined) continue;
      if (name.startsWith("on")) element.addEventListener(name.slice(2), value);
      else if (name === "class") element.className = value;
      else element.setAttribute(name, value === true ? "" : value);
    }
    for (const child of children.flat()) if (child !== null && child !== undefined && child !== false) element.append(child);
    return element;
  }
  const root = page(doc, el);
  doc.getElementById = id => root.all().find(node => node.id === id) || null;
  const window = {
    App: {
      el,
      url: route => route,
      textsatz: async () => satz,
      holen: async route => {
        if (route !== ROUTE) return { text: "" };
        const next = answers.form.shift() || form;
        if (next instanceof Error) throw next;
        return next;
      },
      senden: async (route, body) => {
        calls.senden.push([route, JSON.parse(JSON.stringify(body))]);
        const next = answers.senden.shift();
        const value = typeof next === "function" ? await next() : next;
        if (value instanceof Error) throw value;
        return value || SUGGESTION;
      },
      status: (element, text, type = "") => { calls.status.push([element.id, text, type]); },
      kiEinrichten: async () => { calls.einrichten += 1; },
    },
    Texte,
  };
  const context = { window, document: doc, location: { search: "?id=b1" }, URLSearchParams, console,
                    CustomEvent: class { constructor(type) { this.type = type; } } };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "lebenslauf-erstellen-logik.js"), "utf8"), context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "lebenslauf-erstellen.js"), "utf8"), context);
  const $ = id => doc.getElementById(id);
  return { doc, calls, answers, $ };
}

const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const visible = node => { for (let n = node; n; n = n.parent) if (n.hidden) return false; return true; };
const aiStatus = calls => calls.status.filter(([id]) => id === "cv-erstellen-ki-status");
const boxes = $ => $("cv-erstellen-ki-liste").querySelectorAll("input");
const text = (key, satz = "stelle-sie") => Texte.text(key, satz);

/** A deferred answer: the request runs until `release` is called. */
function pending(value) {
  let release;
  const done = new Promise(resolve => { release = () => resolve(value); });
  return { answer: () => done, release: () => release() };
}

async function opened(options) {
  const page = setup(options);
  page.$("cv-erstellen-oeffnen").click();
  await settle();
  return page;
}

async function pressed(page) {
  const button = page.$("cv-erstellen-ki-knopf");
  button.focus();
  button.click();
  await settle();
  return button;
}

test("the page markup names the box by text set and lets the focus land on the status line", () => {
  const html = fs.readFileSync(path.join(SEITEN, "bewerbung.html"), "utf8");
  assert.match(html, /<h5 [^>]*id="cv-erstellen-ki-titel"[^>]*data-text="lebenslauf.ki-titel"|<h5 [^>]*data-text="lebenslauf.ki-titel"[^>]*id="cv-erstellen-ki-titel"/);
  assert.match(html, /<p [^>]*id="cv-erstellen-ki-status"[^>]*tabindex="-1"/);
  assert.match(html, /<button type="button" class="btn btn--quiet" id="cv-erstellen-ki-stellentext" data-text="lebenslauf.ki-zum-stellentext" hidden>/);
});

test("opening applies the suggestion, says once what it did and cost, and keeps the focus on the first station", async () => {
  const { $, calls, doc } = await opened();

  assert.equal($("cv-erstellen-ki-zeile").textContent, text("lebenslauf.ki-angewendet"));
  assert.equal(boxes($).length, 2);
  assert.ok(boxes($).every(box => box.checked));
  assert.deepEqual(aiStatus(calls).filter(([, said]) => said), [
    ["cv-erstellen-ki-status", `Vorschlag der KI angewendet: 2 Empfehlungen. ${COST}`, "ok"]]);
  assert.equal(doc.activeElement, $("cv-erstellen-stationen").querySelector("input"));
  assert.equal($("cv-erstellen-ki-knoepfe").hidden, true);
});

test("a repeat from the cache says what it did and nothing about costs", async () => {
  const { calls, answers, $ } = setup();
  answers.senden.push({ ...SUGGESTION, kosten_usd: 0, wiederholt: true, kosten_text: "" });
  $("cv-erstellen-oeffnen").click();
  await settle();
  assert.deepEqual(aiStatus(calls).filter(([, said]) => said).map(([, said]) => said),
                   ["Vorschlag der KI angewendet: 2 Empfehlungen."]);
});

test("with a saved CV for this application nothing is applied on opening; the AI can propose anew", async () => {
  const { $, calls } = await opened({ form: { ...FORM, eigene_variante: "b1-daten" } });

  assert.equal(calls.senden.length, 0);
  assert.equal($("cv-erstellen-ki-zeile").textContent, text("lebenslauf.ki-gespeichert"));
  assert.match($("cv-erstellen-ki-zeile").textContent, /Ihre Auswahl gespeichert/);
  assert.equal($("cv-erstellen-ki-knopf").textContent, "Neu vorschlagen lassen");
  assert.ok(visible($("cv-erstellen-ki-knopf")));
});

test("while the AI runs the button stays where it is, marked busy, and a second press asks nothing", async () => {
  const page = await opened({ form: { ...FORM, eigene_variante: "b1-daten" } });
  const { $, calls, answers, doc } = page;
  const slow = pending(SUGGESTION);
  answers.senden.push(slow.answer);

  const button = await pressed(page);
  assert.ok(visible(button), "hiding the row would drop the focus");
  assert.equal(doc.activeElement, button);
  assert.equal(button.getAttribute("aria-disabled"), "true");
  assert.equal(button.disabled, false, "a disabled button loses the focus");
  assert.notEqual($("cv-erstellen-ki-zeile").textContent, text("lebenslauf.ki-gespeichert"));
  assert.doesNotMatch($("cv-erstellen-ki-zeile").textContent, /kann/);
  button.click();
  await settle();
  assert.equal(calls.senden.length, 1);

  slow.release();
  await settle();
  assert.equal($("cv-erstellen-ki-knoepfe").hidden, true);
  assert.equal(doc.activeElement, boxes($)[0]);
  assert.equal($("cv-erstellen-ki-zeile").textContent, text("lebenslauf.ki-angewendet"));
});

test("with nothing to recommend the focus goes to the status line that says so", async () => {
  const page = await opened({ form: { ...FORM, eigene_variante: "b1-daten" } });
  page.answers.senden.push({ ...SUGGESTION, empfehlungen: [] });

  await pressed(page);

  assert.equal(page.doc.activeElement, page.$("cv-erstellen-ki-status"));
  assert.match(aiStatus(page.calls).at(-1)[1], /^Die KI schlägt für diese Stelle nichts anderes vor\./);
});

test("on an error the focus stays on the button, now Nochmals vorschlagen, and the live region hears it once", async () => {
  const page = await opened({ form: { ...FORM, eigene_variante: "b1-daten" } });
  const failure = "Kein Vorschlag der KI. Die KI antwortet gerade nicht. Nichts berechnet. Die Auswahl bleibt, wie sie ist.";
  page.answers.senden.push(new Error(failure));
  const before = aiStatus(page.calls).length;

  const button = await pressed(page);

  assert.equal(page.doc.activeElement, button);
  assert.ok(visible(button));
  assert.equal(button.textContent, "Nochmals vorschlagen");
  assert.equal(button.getAttribute("aria-disabled"), null);
  assert.deepEqual(aiStatus(page.calls).slice(before), [["cv-erstellen-ki-status", failure, "fehler"]]);
});

test("without the job ad the box says what is missing and leads to the Stellentext", async () => {
  const { $, doc, calls } = await opened({ form: { ...FORM, ki: "ohne_inserat" } });

  assert.equal($("cv-erstellen-ki-zeile").textContent, "Für Vorschläge der KI fehlt noch der Stellentext.");
  assert.ok(visible($("cv-erstellen-ki-stellentext")));
  assert.equal(visible($("cv-erstellen-ki-knopf")), false);
  $("cv-erstellen-ki-stellentext").click();
  assert.equal($("s-stelle").open, true);
  assert.equal($("s-stelle").scrolled, 1);
  assert.equal(doc.activeElement, $("stellentext"));
  assert.equal(calls.senden.length, 0);
});

test("without AI the box offers to switch it on, worded for an apprenticeship", async () => {
  const { $ } = await opened({ form: { ...FORM, ki: "aus" }, satz: "lehrstelle-du" });

  assert.equal($("cv-erstellen-ki-zeile").textContent,
               "Mit KI schlägt die App für diese Lehrstelle Stationen, Reihenfolge und Kurzprofil vor.");
  assert.equal($("cv-erstellen-ki-knopf").textContent, "KI einschalten");
  assert.equal(visible($("cv-erstellen-ki-stellentext")), false);
});

test("once the AI is switched on, it suggests and the focus goes to the first recommendation", async () => {
  const page = await opened({ form: { ...FORM, ki: "aus" } });
  page.answers.form.push(FORM);

  await pressed(page);

  assert.equal(page.calls.einrichten, 1);
  assert.equal(page.calls.senden.length, 1);
  assert.equal(page.doc.activeElement, boxes(page.$)[0]);
});

test("when the app cannot tell whether the AI is on now, the box says why instead of staying silent", async () => {
  const page = await opened({ form: { ...FORM, ki: "aus" } });
  page.answers.form.push(new Error("Die App antwortet nicht."));

  const button = await pressed(page);

  assert.deepEqual(aiStatus(page.calls).at(-1), ["cv-erstellen-ki-status", "Die App antwortet nicht.", "fehler"]);
  assert.equal(page.doc.activeElement, button);
  assert.equal(page.calls.senden.length, 0);
});
