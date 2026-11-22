// Ordering the search terms on Suche einstellen (#285, G87): by dragging the handle, or with the move buttons from the
// keyboard. Each move is announced, focus stays on the moved term's control, and the whole order goes to the server.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const L = require("../seiten/suchliste-logik.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROUTE = "/api/beruf/reihenfolge";
const TERMS = ["Pflegefachmann", "Fachmann Gesundheit", "Betreuer", "Logistiker", "Koch"];
const ROW_HEIGHT = 48;

// The logic

test("a move takes the term out and puts it at its new place, without changing the list it got", () => {
  const before = [...TERMS];
  assert.deepEqual(L.verschoben(before, 0, 1), ["Fachmann Gesundheit", "Pflegefachmann", "Betreuer", "Logistiker", "Koch"]);
  assert.deepEqual(L.verschoben(before, 4, 0), ["Koch", "Pflegefachmann", "Fachmann Gesundheit", "Betreuer", "Logistiker"]);
  assert.deepEqual(L.verschoben(before, 2, 2), TERMS);
  assert.deepEqual(before, TERMS);
});

test("the place under the pointer counts the other rows whose middle lies above it", () => {
  const middles = [24, 72, 120, 168, 216];
  assert.equal(L.zielIndex(middles, 0, 10), 0);
  assert.equal(L.zielIndex(middles, 0, 80), 1);
  assert.equal(L.zielIndex(middles, 0, 500), 4);
  assert.equal(L.zielIndex(middles, 3, 0), 0);
  assert.equal(L.zielIndex(middles, 3, 130), 3, "below the middle of the row above it stays");
  assert.equal(L.zielIndex(middles, 3, 110), 2);
});

test("the announcement names the term and its place", () => {
  assert.equal(L.ansage("Pflegefachmann", 2, 5), "„Pflegefachmann“ steht jetzt an Stelle 2 von 5.");
  assert.deepEqual(L.knopfNamen("Koch"), { hoch: "Koch nach oben", runter: "Koch nach unten", entfernen: "Koch entfernen" });
});

// The page, with a small stand-in DOM

class FakeNode {}

class FakeText extends FakeNode {
  constructor(text) { super(); this.data = String(text); this.parent = null; }
  get textContent() { return this.data; }
}

class FakeElement extends FakeNode {
  constructor(doc, tag) {
    super();
    Object.assign(this, { doc, tagName: tag.toUpperCase(), attrs: new Map(), children: [], parent: null, listeners: {},
      disabled: false, className: "" });
  }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  removeAttribute(name) { this.attrs.delete(name); }
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
    if (this.contains(this.doc.activeElement)) this.doc.activeElement = null;
    this.children = [];
    this.append(...nodes);
  }
  get textContent() { return this.children.map(child => child.textContent).join(""); }
  set textContent(text) { this.replaceChildren(String(text)); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatch(type, extra = {}) {
    const event = { type, target: this, button: 0, pointerId: 1, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, ...extra };
    for (let node = this; node; node = node.parent) for (const handler of node.listeners[type] || []) handler(event);
    return event;
  }
  click() { if (!this.disabled) this.dispatch("click"); }
  focus() { this.doc.activeElement = this; }
  getBoundingClientRect() {
    const rows = this.parent ? this.parent.children : [this];
    const top = rows.indexOf(this) * ROW_HEIGHT;
    return { top, bottom: top + ROW_HEIGHT, height: ROW_HEIGHT };
  }
  all() { return this.children.filter(c => c instanceof FakeElement).flatMap(c => [c, ...c.all()]); }
  find(check) { return this.all().find(check) || null; }
  contains(node) { return node === this || this.all().includes(node); }
}

function setup({ fail = false } = {}) {
  const docListeners = {};
  const doc = {
    activeElement: null,
    createElement: tag => new FakeElement(doc, tag),
    addEventListener(type, handler) { (docListeners[type] ||= []).push(handler); },
    removeEventListener(type, handler) { docListeners[type] = (docListeners[type] || []).filter(h => h !== handler); },
    fire(type, extra = {}) {
      const event = { type, pointerId: 1, preventDefault() {}, ...extra };
      for (const handler of [...(docListeners[type] || [])]) handler(event);
    },
    listening: type => (docListeners[type] || []).length,
  };
  const calls = { senden: [], meldungen: [], entfernt: [], geaendert: 0 };
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
  const window = {
    App: {
      el,
      senden: async (route, body) => {
        calls.senden.push([route, JSON.parse(JSON.stringify(body))]);
        if (fail) throw new Error("Die Liste hat sich inzwischen geändert.");
        return { berufe: body.berufe };
      },
      status: (target, text, art) => { calls.meldungen.push({ target, text, art }); },
    },
  };
  const timers = [];
  const context = { window, document: doc, console,
    setTimeout: (run, ms) => { timers.push({ run, ms }); return timers.length; }, clearTimeout: id => { timers[id - 1].run = () => {}; } };
  vm.createContext(context);
  for (const name of ["dot-line.js", "suche-ertrag-logik.js", "suchliste-logik.js", "suchliste.js"]) {
    vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  }
  const list = el("ol");
  const status = el("div");
  const options = { status, entfernen: (name, button) => calls.entfernt.push([name, button]), geaendert: () => { calls.geaendert += 1; } };
  window.Suchliste.zeige(list, TERMS, options);
  return { doc, list, status, calls, window, options, timers };
}

const settle = async () => { for (let i = 0; i < 5; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const rows = list => list.children;
const shown = list => rows(list).map(row => row.getAttribute("data-begriff"));
const control = (list, name, role) => list.find(node => node.tagName === "BUTTON" && node.getAttribute("aria-label") === L.knopfNamen(name)[role]);
const handle = (list, name) => rows(list)[shown(list).indexOf(name)].find(node => (node.className || "").includes("suchliste__griff"));

test("each row has a handle and the move buttons, named after the term", () => {
  const { list } = setup();
  assert.deepEqual(shown(list), TERMS);
  for (const name of TERMS) {
    assert.ok(control(list, name, "hoch"), `${name} nach oben`);
    assert.ok(control(list, name, "runter"), `${name} nach unten`);
    assert.ok(control(list, name, "entfernen"), `${name} entfernen`);
    assert.equal(handle(list, name).getAttribute("aria-hidden"), "true");
  }
  assert.equal(control(list, TERMS[0], "hoch").getAttribute("aria-disabled"), "true");
  assert.equal(control(list, TERMS[4], "runter").getAttribute("aria-disabled"), "true");
  assert.equal(control(list, TERMS[1], "hoch").getAttribute("aria-disabled"), null);
});

test("Nach unten moves the term, announces its place, keeps focus on its button and saves the order", async () => {
  const { list, status, calls, doc } = setup();
  control(list, "Pflegefachmann", "runter").focus();

  control(list, "Pflegefachmann", "runter").click();
  await settle();

  assert.deepEqual(shown(list), ["Fachmann Gesundheit", "Pflegefachmann", "Betreuer", "Logistiker", "Koch"]);
  assert.deepEqual(calls.meldungen.at(-1), { target: status, text: "„Pflegefachmann“ steht jetzt an Stelle 2 von 5.", art: "ok" });
  assert.equal(doc.activeElement, control(list, "Pflegefachmann", "runter"));
  assert.deepEqual(calls.senden, [[ROUTE, { berufe: shown(list) }]]);
  assert.equal(calls.geaendert, 1);
});

test("Nach oben at the top moves nothing and keeps focus where it is", async () => {
  const { list, calls, doc } = setup();
  control(list, "Pflegefachmann", "hoch").focus();

  control(list, "Pflegefachmann", "hoch").click();
  await settle();

  assert.deepEqual(shown(list), TERMS);
  assert.deepEqual(calls.senden, []);
  assert.equal(doc.activeElement, control(list, "Pflegefachmann", "hoch"));
});

test("quick moves save each order in turn, and a reload from the page waits until the last is saved", async () => {
  const { list, calls, window, options } = setup();
  control(list, "Koch", "hoch").click();
  control(list, "Koch", "hoch").click();
  window.Suchliste.zeige(list, TERMS, options);  // the page reloads with what the server had before

  assert.deepEqual(shown(list), ["Pflegefachmann", "Fachmann Gesundheit", "Koch", "Betreuer", "Logistiker"]);
  await settle();
  assert.deepEqual(calls.senden.map(([, body]) => body.berufe.indexOf("Koch")), [3, 2]);
  assert.equal(calls.geaendert, 1);
});

test("dragging the handle moves the term under the pointer and saves once it is dropped", async () => {
  const { list, calls, doc } = setup();
  const grip = handle(list, "Logistiker");

  const down = grip.dispatch("pointerdown", { clientY: 3 * ROW_HEIGHT + 10 });
  doc.fire("pointermove", { clientY: 2 * ROW_HEIGHT + 5 });
  doc.fire("pointermove", { clientY: 10 });
  assert.equal(down.defaultPrevented, true);
  assert.deepEqual(shown(list), ["Logistiker", "Pflegefachmann", "Fachmann Gesundheit", "Betreuer", "Koch"]);
  assert.ok(rows(list)[0].className.includes("suchliste__eintrag--zieht"));
  assert.deepEqual(calls.senden, [], "nothing is saved while dragging");

  doc.fire("pointerup", { clientY: 10 });
  await settle();

  assert.deepEqual(calls.senden, [[ROUTE, { berufe: ["Logistiker", "Pflegefachmann", "Fachmann Gesundheit", "Betreuer", "Koch"] }]]);
  assert.equal(calls.meldungen.at(-1).text, "„Logistiker“ steht jetzt an Stelle 1 von 5.");
  assert.ok(!rows(list)[0].className.includes("suchliste__eintrag--zieht"));
  assert.equal(doc.listening("pointermove"), 0);
});

const MOVED = "suchliste__eintrag--verschoben";
const marked = list => rows(list).filter(row => row.className.includes(MOVED)).map(row => row.getAttribute("data-begriff"));

test("the moved row stands out for about a second, also when the page draws the list anew", async () => {
  const { list, timers, window, options } = setup();

  control(list, "Betreuer", "hoch").click();
  await settle();
  assert.deepEqual(marked(list), ["Betreuer"]);
  window.Suchliste.zeige(list, ["Pflegefachmann", "Betreuer", "Fachmann Gesundheit", "Logistiker", "Koch"], options);
  assert.deepEqual(marked(list), ["Betreuer"]);

  const last = timers.at(-1);
  assert.ok(last.ms >= 800 && last.ms <= 1500, `${last.ms} ms`);
  last.run();
  assert.deepEqual(marked(list), []);
});

test("a second move hands the highlight to the newly moved term", async () => {
  const { list, timers } = setup();
  control(list, "Betreuer", "hoch").click();
  control(list, "Koch", "hoch").click();
  await settle();

  assert.deepEqual(marked(list), ["Koch"]);
  timers[0].run();
  assert.deepEqual(marked(list), ["Koch"], "the first timer does not end the second highlight");
});

test("a dropped row stands out too", async () => {
  const { list, doc } = setup();
  handle(list, "Koch").dispatch("pointerdown", { clientY: 4 * ROW_HEIGHT + 10 });
  doc.fire("pointermove", { clientY: 5 });
  doc.fire("pointerup", { clientY: 5 });
  await settle();

  assert.deepEqual(marked(list), ["Koch"]);
});

test("Escape while dragging puts the term back and saves nothing", async () => {
  const { list, calls, doc } = setup();
  handle(list, "Koch").dispatch("pointerdown", { clientY: 4 * ROW_HEIGHT + 10 });
  doc.fire("pointermove", { clientY: 5 });

  doc.fire("keydown", { key: "Escape" });
  doc.fire("pointerup", { clientY: 5 });
  await settle();

  assert.deepEqual(shown(list), TERMS);
  assert.deepEqual(calls.senden, []);
});

test("a drop at the same place saves nothing", async () => {
  const { list, calls, doc } = setup();
  handle(list, "Betreuer").dispatch("pointerdown", { clientY: 2 * ROW_HEIGHT + 10 });
  doc.fire("pointerup", { clientY: 2 * ROW_HEIGHT + 12 });
  await settle();

  assert.deepEqual(calls.senden, []);
});

test("a refused order says why and lets the page load the saved one", async () => {
  const { list, status, calls } = setup({ fail: true });
  control(list, "Betreuer", "hoch").click();
  await settle();

  assert.deepEqual(calls.meldungen.at(-1),
    { target: status, text: "Reihenfolge nicht gespeichert: Die Liste hat sich inzwischen geändert.", art: "fehler" });
  assert.equal(calls.geaendert, 1);
});

test("Entfernen goes to the page's own handler with its button", () => {
  const { list, calls } = setup();
  const button = control(list, "Betreuer", "entfernen");

  button.click();

  assert.deepEqual(calls.entfernt, [["Betreuer", button]]);
  assert.equal(button.textContent, "Entfernen");
});

test("a single term has nothing to order", () => {
  const { list, window, options } = setup();
  window.Suchliste.zeige(list, ["Koch"], options);

  assert.equal(rows(list).length, 1);
  assert.equal(control(list, "Koch", "hoch"), null);
  assert.equal(handle(list, "Koch"), null);
  assert.ok(control(list, "Koch", "entfernen"));
});

// The yield of each term (G103, #375)

const YIELD = new Map([
  ["Betreuer", { begriff: "Betreuer", suchen: 3, treffer: 4, neu: 1, ab_note_4: 1, aussortiert: 2, ohne_ertrag: false }],
  ["Koch", { begriff: "Koch", suchen: 9, treffer: 0, neu: 0, ab_note_4: 0, aussortiert: 0, ohne_ertrag: true }],
]);
const row = (list, name) => rows(list)[shown(list).indexOf(name)];
const part = (node, name) => node.find(child => (child.className || "").split(" ").includes(name));

test("each row carries its yield as plain text, and the mark when a term brought nothing", () => {
  const { list, window } = setup();
  window.Suchliste.ertrag(YIELD);

  assert.equal(part(row(list, "Betreuer"), "suchliste__ertrag").textContent.replace(/\s·,/g, " ·"), "3 Suchen · 4 Treffer · 1 neu · 1 ab Note 4 · 2 aussortiert");
  assert.equal(part(row(list, "Koch"), "term--flag").textContent, "ohne Ertrag");
  assert.equal(part(row(list, "Betreuer"), "term--flag"), null);
  assert.equal(part(row(list, "Pflegefachmann"), "suchliste__ertrag"), null, "a term no run has searched yet has no line");
});

test("the yield neither moves the handle nor renames the buttons", () => {
  const { list, window } = setup();
  window.Suchliste.ertrag(YIELD);

  const children = row(list, "Betreuer").children;
  assert.ok(children[0].className.includes("suchliste__griff"), "the handle stays first");
  assert.ok(children.at(-1).className.includes("suchliste__ertrag"), "the yield comes last, on its own line");
  assert.ok(children.at(-2).className.includes("suchliste__knoepfe"));
  for (const name of TERMS) for (const role of ["hoch", "runter", "entfernen"]) assert.ok(control(list, name, role), `${name} ${role}`);
});

test("a yield that arrives while a term is dragged waits for the drop", () => {
  const { list, window, doc } = setup();
  handle(list, "Koch").dispatch("pointerdown", { pointerType: "mouse" });
  window.Suchliste.ertrag(YIELD);
  assert.equal(part(row(list, "Koch"), "term--flag"), null);
  doc.fire("pointerup");
  assert.equal(part(row(list, "Koch"), "term--flag").textContent, "ohne Ertrag");
});

// The page around it

test("Suche einstellen shows the terms as an ordered list with a hint and loads the scripts before the list's", () => {
  const html = fs.readFileSync(path.join(SEITEN, "suche-einstellen.html"), "utf8");
  assert.match(html, /<ol id="suchliste-liste" class="suchliste"/);
  assert.match(html, /<p id="suchliste-hinweis" class="field__hint" hidden><\/p>/);
  const order = ["/suchliste-logik.js", "/suchliste.js", "/beruf-vorschlag.js"].map(src => html.indexOf(`<script src="${src}">`));
  assert.ok(order.every(index => index > 0) && order[0] < order[1] && order[1] < order[2], order.join(", "));
});

test("the targets of a row are at least 44 by 44 pixels and the handle does not scroll the page on touch", () => {
  const css = fs.readFileSync(path.join(SEITEN, "stil.css"), "utf8");
  const rule = selector => (css.match(new RegExp(`${selector.replace(/[.]/g, "\\.")} \\{([^}]*)\\}`)) || [])[1] || "";
  assert.match(rule(".suchliste__griff"), /min-width: 44px/);
  assert.match(rule(".suchliste__griff"), /min-height: 44px/);
  assert.match(rule(".suchliste__griff"), /touch-action: none/);
  assert.match(rule(".suchliste button"), /min-height: 44px/);
  assert.match(rule(".suchliste__pfeil"), /min-width: 44px/);
});
