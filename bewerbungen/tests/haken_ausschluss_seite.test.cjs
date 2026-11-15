// Taking a point of the rating over as an exclusion on Stellen (#224, G83), with a small stand-in DOM: the form
// opens inside the clicked point, errors stay in the form, and the confirmation with Rückgängig replaces it in place.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Texte = require("../seiten/texte.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROUTE = "/api/suche/haken-ausschluss";
const POINTS = ["Pikettdienst alle vier Wochen", "Englisch eine Stufe unter dem Verlangten"];
const HIT = { id: "jobs-ch-abc", stelle: "Systemtechniker mit Pikettdienst", bewertung: { note: 4, haken: POINTS } };

class FakeNode {}

class FakeText extends FakeNode {
  constructor(text) { super(); this.data = String(text); this.parent = null; }
  get textContent() { return this.data; }
}

class FakeElement extends FakeNode {
  constructor(doc, tag) {
    super();
    Object.assign(this, { doc, tagName: tag.toUpperCase(), attrs: new Map(), children: [], parent: null, listeners: {},
      value: "", disabled: false, checked: false, className: "", selection: null });
  }
  setAttribute(name, value) {
    this.attrs.set(name, String(value));
    if (name === "value") this.value = String(value);
    if (name === "checked") this.checked = true;
    if (name === "disabled") this.disabled = true;
  }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  hasAttribute(name) { return this.attrs.has(name); }
  removeAttribute(name) { this.attrs.delete(name); }
  get id() { return this.getAttribute("id") || ""; }
  set id(value) { this.setAttribute("id", value); }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  append(...nodes) {
    for (const given of nodes) {
      const node = given instanceof FakeNode ? given : new FakeText(given);
      if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1);
      node.parent = this;
      this.children.push(node);
    }
  }
  replaceChildren(...nodes) {
    for (const child of this.children) child.parent = null;
    this.children = [];
    this.append(...nodes);
  }
  replaceWith(node) {
    const parent = this.parent;
    const index = parent.children.indexOf(this);
    if (node.parent) node.parent.children.splice(node.parent.children.indexOf(node), 1);
    parent.children.splice(index, 1, node);
    node.parent = parent;
    this.parent = null;
  }
  get textContent() { return this.children.map(child => child.textContent).join(""); }
  set textContent(text) { this.replaceChildren(String(text)); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatch(type, extra = {}) {
    const event = { type, target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...extra };
    for (let node = this; node; node = node.parent) for (const handler of node.listeners[type] || []) handler(event);
    return event;
  }
  click() {
    if (this.disabled) return;
    if (this.getAttribute("type") === "radio") { this.checked = true; this.dispatch("change"); return; }
    this.dispatch("click");
    if (this.getAttribute("type") === "submit") {
      let form = this.parent;
      while (form && form.tagName !== "FORM") form = form.parent;
      if (form) form.dispatch("submit");
    }
  }
  focus() { this.doc.activeElement = this; }
  setSelectionRange(start, end) { this.selection = [start, end]; }
  all() { return this.children.filter(c => c instanceof FakeElement).flatMap(c => [c, ...c.all()]); }
  find(test) { return this.all().find(test) || null; }
  contains(node) { return node === this || this.all().includes(node); }
}

function setup({ satz = "stelle-sie", excluded = [false, false], anbieten = true } = {}) {
  const doc = { activeElement: null, createElement: tag => new FakeElement(doc, tag) };
  const calls = { holen: [], senden: [], meldungen: 0 };
  const answers = { senden: [] };
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
  const window = {
    App: {
      el,
      holen: async (route, parameter) => {
        calls.holen.push([route, parameter]);
        if (route === `${ROUTE}/punkte`) return { ausgeschlossen: excluded };
        return { id: HIT.id, punkt: parameter.punkt, text: POINTS[parameter.punkt], art: "titel_ausschluss",
          wert: "Pikettdienst", werte: { ausschluss: [], titel_ausschluss: [] } };
      },
      senden: async (route, body) => {
        calls.senden.push([route, JSON.parse(JSON.stringify(body))]);  // the page's objects come from another realm
        const next = answers.senden.shift();
        if (next instanceof Error) throw next;
        return next || { art: body.art, wert: body.wert };
      },
      status: () => { calls.meldungen += 1; },
    },
    Meldungen: { zeige: () => { calls.meldungen += 1; } },
    Texte,
  };
  const context = { window, document: doc, console };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "haken-ausschluss-logik.js"), "utf8"), context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "haken-ausschluss.js"), "utf8"), context);
  const column = window.HakenAusschluss.liste(HIT, "Was fehlt oder unsicher ist", { anbieten, satz });
  return { doc, calls, answers, column, window };
}

const settle = async () => { for (let i = 0; i < 5; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const points = column => column.all().filter(node => node.tagName === "LI");
const button = point => point.find(node => node.tagName === "BUTTON");
const box = point => point.find(node => (node.className || "").split(" ").includes("exclusion-adopt"));
const field = point => point.find(node => node.tagName === "INPUT" && node.getAttribute("type") === "text");
const byText = (point, text) => point.find(node => node.tagName === "BUTTON" && node.textContent === text);
const position = (point, node) => point.all().indexOf(node);

async function opened(options) {
  const page = setup(options);
  await settle();
  const first = points(page.column)[0];
  button(first).click();
  await settle();
  return { ...page, first };
}

test("each point has a quiet button on its own line that controls the box inside the point", async () => {
  const { column } = setup();
  await settle();
  for (const point of points(column)) {
    const knopf = button(point);
    assert.equal(knopf.textContent, "Künftig nicht zeigen");
    assert.equal(knopf.className, "btn btn--sm btn--quiet", "quiet, so the rating list keeps reading as content");
    assert.equal(knopf.getAttribute("aria-label"), `Künftig nicht zeigen: ${point.children[0].textContent}`);
    assert.equal(knopf.getAttribute("aria-expanded"), "false");
    assert.equal(knopf.getAttribute("aria-controls"), box(point).id);
    assert.ok(box(point).id && box(point).hidden);
    assert.equal(knopf.parent.tagName, "DIV", "the button sits on its own line, not inline with the text");
  }
});

test("a point that is excluded already says Ausgeschlossen instead of offering the button", async () => {
  const { column } = setup({ excluded: [true, false] });
  await settle();
  const [first, second] = points(column);

  assert.equal(button(first), null);
  assert.match(first.textContent, /Ausgeschlossen/);
  assert.ok(button(second));
});

test("an apprenticeship's list has no buttons and asks the app nothing", async () => {
  const { column, calls } = setup({ satz: "lehrstelle-du", anbieten: false });
  await settle();

  assert.equal(points(column).length, 2);
  assert.ok(points(column).every(point => button(point) === null));
  assert.deepEqual(calls.holen, []);
});

test("the form opens inside the clicked point, names the real card and puts the cursor at the end", async () => {
  const { first, doc } = await opened();
  const form = box(first);
  const input = field(first);

  assert.equal(form.hidden, false);
  assert.equal(button(first).getAttribute("aria-expanded"), "true");
  assert.match(form.textContent,
    /Die App trägt den Eintrag unten auf «Suche einstellen» unter «Was Sie nicht sehen wollen» ein\. Sie können ihn vorher ändern\./);
  assert.equal(first.find(node => node.tagName === "LEGEND").textContent, "Wo eintragen?");
  assert.equal(first.find(node => node.className === "field__label").textContent, "Was nicht vorkommen soll");
  assert.equal(byText(first, "Eintragen").className, "btn btn--sm btn--primary");
  assert.equal(byText(first, "Abbrechen").className, "btn btn--sm");
  assert.equal(doc.activeElement, input);
  assert.deepEqual(input.selection, ["Pikettdienst".length, "Pikettdienst".length]);
  const radios = first.all().filter(node => node.getAttribute("type") === "radio");
  const hint = first.find(node => node.className === "field__hint" && /nächsten Suche/.test(node.textContent));
  assert.ok(position(first, radios[1]) < position(first, hint) && position(first, hint) < position(first, input),
    "the hint sits under the radios");
  const described = input.getAttribute("aria-describedby").split(" ");
  const intro = first.find(node => /Was Sie nicht sehen wollen/.test(node.textContent) && node.tagName === "P");
  assert.ok(described.includes(intro.id) && described.includes(hint.id));
});

test("the du form names the card as the du set of texts does", async () => {
  const { first } = await opened({ satz: "stelle-du" });

  assert.match(box(first).textContent, /unter «Was du nicht sehen willst» ein\. Du kannst ihn vorher ändern\./);
});

test("the hint follows the chosen place", async () => {
  const { first } = await opened();
  const inserat = first.all().find(node => node.getAttribute("value") === "ausschluss");
  inserat.click();

  assert.match(box(first).textContent,
    /Solche Stellen kommen weiter in die Liste\. Die KI liest es bei jeder weiteren Einschätzung als Ausschluss mit\./);
});

test("Escape closes the form and returns the focus to the button", async () => {
  const { first, doc } = await opened();
  field(first).dispatch("keydown", { key: "Escape" });

  assert.equal(box(first).hidden, true);
  assert.equal(button(first).getAttribute("aria-expanded"), "false");
  assert.equal(doc.activeElement, button(first));
});

test("the button toggles: a second click closes the form instead of rebuilding it over the edits", async () => {
  const { first, doc, calls } = await opened();
  field(first).value = "Pikett";
  button(first).click();
  await settle();

  assert.equal(box(first).hidden, true);
  assert.equal(button(first).getAttribute("aria-expanded"), "false");
  assert.equal(doc.activeElement, button(first));
  assert.equal(calls.holen.filter(([route]) => route === ROUTE).length, 1, "no new proposal is fetched");
  button(first).click();
  await settle();
  assert.equal(box(first).hidden, false, "a third click opens it again");
});

test("an error shows above the buttons, keeps the form open and returns the focus to the field", async () => {
  const page = await opened();
  const { first, doc, calls, answers } = page;
  answers.senden.push(new Error("Bitte ohne Komma, ein Ausschluss pro Eintrag."));
  field(first).value = "Pikett, Nacht";
  byText(first, "Eintragen").click();
  await settle();

  const error = first.find(node => node.className === "field__error");
  assert.match(error.textContent, /Nicht gespeichert\. Bitte ohne Komma/);
  assert.ok(position(first, error) < position(first, byText(first, "Eintragen")), "above the buttons");
  assert.equal(doc.activeElement, field(first));
  assert.equal(field(first).getAttribute("aria-describedby"),
    `${error.id} ${box(first).id}-intro ${box(first).id}-hinweis`, "the error is read first");
  assert.equal(field(first).getAttribute("aria-invalid"), "true");
  assert.equal(box(first).hidden, false);
  assert.equal(calls.meldungen, 0, "nothing goes to the message at the top of the page");
});

test("success replaces the form with the confirmation and Rückgängig, as a status, with the focus there", async () => {
  const { first, doc, calls } = await opened();
  byText(first, "Eintragen").click();
  await settle();

  assert.deepEqual(calls.senden[0], [ROUTE, { id: HIT.id, punkt: 0, art: "titel_ausschluss", wert: "Pikettdienst" }]);
  const confirmation = box(first);
  assert.equal(confirmation.getAttribute("role"), "status");
  assert.equal(doc.activeElement, confirmation);
  assert.equal(confirmation.textContent,
    "«Pikettdienst» steht jetzt auf «Suche einstellen» unter «Im Titel». Gilt ab der nächsten Suche.Rückgängig");
  const message = confirmation.find(node => node.tagName === "P");
  assert.ok(message.id, "the confirmation paragraph has an id");
  assert.equal(confirmation.getAttribute("aria-labelledby"), message.id, "the box is named by its confirmation");
  assert.equal(byText(first, "Rückgängig").className, "btn btn--sm");
  assert.equal(field(first), null, "the form is gone");
  assert.match(first.textContent, /Ausgeschlossen/);
  assert.equal(byText(first, "Künftig nicht zeigen"), null);
  assert.equal(calls.meldungen, 0, "nothing goes to the message at the top of the page");
});

test("Rückgängig takes the entry back in the same box and offers the button again", async () => {
  const { first, doc, calls } = await opened();
  byText(first, "Eintragen").click();
  await settle();
  byText(first, "Rückgängig").click();
  await settle();

  assert.deepEqual(calls.senden[1], [`${ROUTE}/rueckgaengig`, { art: "titel_ausschluss", wert: "Pikettdienst" }]);
  assert.equal(box(first).textContent, "«Pikettdienst» steht nicht mehr auf «Suche einstellen» unter «Im Titel».");
  const message = box(first).find(node => node.tagName === "P");
  assert.equal(box(first).getAttribute("aria-labelledby"), message.id, "the box is named by the undo message");
  assert.equal(box(first).getAttribute("role"), "status");
  assert.equal(doc.activeElement, box(first));
  assert.ok(byText(first, "Künftig nicht zeigen"));
  assert.equal(calls.meldungen, 0);
});
