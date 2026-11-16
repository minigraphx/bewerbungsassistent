// The box „Vorschläge der KI“ in „Lebenslauf erstellen“ (#293, G75, G95) with a small stand-in DOM: opening sends
// nothing and shows text and cost first; what the box says in each state, where the focus goes around a request and
// what the live region hears. Invented data, the AI is faked.
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
const ESTIMATE = { anzahl: 1, kosten: 0.03, waehrung: "USD", guthaben: null, danach: null, dauer_minuten: 1, reicht_fuer: null };
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
          el("button", { id: "cv-erstellen-ki-knopf", type: "button", class: "btn", "aria-describedby": "cv-erstellen-ki-kosten" }),
          el("span", { id: "cv-erstellen-ki-kosten", class: "caption" }),
          el("button", { id: "cv-erstellen-ki-neu-schaetzen", type: "button", class: "btn btn--quiet", hidden: true }, "Neu schätzen"),
          el("button", { id: "cv-erstellen-ki-stellentext", type: "button", class: "btn btn--quiet", hidden: true })),
        el("details", { id: "cv-erstellen-ki-text" }, el("pre", { id: "cv-erstellen-ki-text-inhalt" })),
        el("p", { id: "cv-erstellen-ki-status", tabindex: "-1" })),
      el("div", { id: "cv-erstellen-stationen" }),
      el("input", { id: "cv-erstellen-beruf" }), el("textarea", { id: "cv-erstellen-profil" }),
      el("div", { id: "cv-erstellen-designs" }),
      el("div", { id: "cv-erstellen-look" }, el("input", { id: "cv-erstellen-foto", type: "checkbox" }),
        el("button", { id: "cv-erstellen-farbe-oeffnen", type: "button", "aria-expanded": "false" })),
      el("p", { id: "cv-erstellen-foto-grund", hidden: true }), el("p", { id: "cv-erstellen-farbe-stand" }),
      el("div", { id: "cv-erstellen-farbe", hidden: true },
        el("div", { id: "cv-erstellen-zeichen" }), el("div", { id: "cv-erstellen-akzent" })),
      el("input", { id: "cv-erstellen-name" }),
      el("p", { id: "cv-erstellen-status" }), el("button", { id: "cv-erstellen-speichern" }),
      el("button", { id: "cv-erstellen-abbrechen" }), el("a", { id: "cv-erstellen-pdf" })),
    el("details", { id: "s-stelle" }, el("textarea", { id: "stellentext" })));
}

/** A queued answer is a value, an Error to throw, or a function whose promise the route waits for. */
async function answer(queue, fallback) {
  const next = queue.shift();
  const value = typeof next === "function" ? await next() : next === undefined ? fallback : next;
  if (value instanceof Error) throw value;
  return value;
}

function setup({ form = FORM, satz = "stelle-sie" } = {}) {
  const doc = { activeElement: null, listeners: {}, createElement: tag => new FakeElement(doc, tag),
                createElementNS: (_, tag) => new FakeElement(doc, tag),
                addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
                dispatchEvent(event) { calls.events.push(event); } };
  const calls = { holen: [], senden: [], status: [], einrichten: 0, events: [] };
  const answers = { senden: [], form: [], estimate: [] };
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
        calls.holen.push(route);
        if (route === ROUTE) return answer(answers.form, form);
        if (route === `${ROUTE}/schaetzung`) return answer(answers.estimate, ESTIMATE);
        return { text: "" };
      },
      senden: async (route, body) => {
        calls.senden.push([route, JSON.parse(JSON.stringify(body))]);
        return answer(answers.senden, SUGGESTION);
      },
      status: (element, text, type = "") => { calls.status.push([element.id, text, type]); },
      kiEinrichten: async () => { calls.einrichten += 1; },
    },
    Texte,
  };
  const context = { window, document: doc, location: { search: "?id=b1" }, URLSearchParams, console,
                    CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } } };
  vm.createContext(context);
  for (const name of ["treffer-logik.js", "zeichen-logik.js", "lebenslauf-erstellen-logik.js", "lebenslauf-erstellen.js"]) {
    vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  }
  const $ = id => doc.getElementById(id);
  return { doc, calls, answers, $ };
}

const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const visible = node => { for (let n = node; n; n = n.parent) if (n.hidden) return false; return true; };
const aiStatus = calls => calls.status.filter(([id]) => id === "cv-erstellen-ki-status");
const boxes = $ => $("cv-erstellen-ki-liste").querySelectorAll("input");
const text = (key, satz = "stelle-sie") => Texte.text(key, satz);
const estimates = calls => calls.holen.filter(route => route === `${ROUTE}/schaetzung`).length;
const SAVED = { ...FORM, eigene_variante: "b1-daten" };

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

test("the page markup: line, button with its cost line, the text for the AI, status, note", () => {
  const html = fs.readFileSync(path.join(SEITEN, "bewerbung.html"), "utf8");
  const box = html.slice(html.indexOf('id="cv-erstellen-ki"'), html.indexOf('id="cv-erstellen-stationen"'));
  const order = ['id="cv-erstellen-ki-zeile"', 'id="cv-erstellen-ki-knoepfe"', 'id="cv-erstellen-ki-kosten"',
                 'id="cv-erstellen-ki-text"', 'id="cv-erstellen-ki-status"', 'class="cv-create__ai-note"'];
  const places = order.map(part => box.indexOf(part));
  assert.ok(places.every(place => place > 0), places.join());
  assert.deepEqual([...places].sort((a, b) => a - b), places);
  assert.match(box, /<h5 [^>]*id="cv-erstellen-ki-titel" data-text="lebenslauf.ki-titel"/);
  assert.match(box, /<button type="button" class="btn" id="cv-erstellen-ki-knopf" aria-describedby="cv-erstellen-ki-kosten">/);
  assert.match(box, /<span class="caption" id="cv-erstellen-ki-kosten"><\/span>/);
  assert.match(box, /<button type="button" class="btn btn--quiet" id="cv-erstellen-ki-neu-schaetzen" data-text="lebenslauf.ki-neu-schaetzen" hidden>/);
  assert.match(box, /<button type="button" class="btn btn--quiet" id="cv-erstellen-ki-stellentext" data-text="lebenslauf.ki-zum-stellentext" hidden>/);
  assert.match(box, /<p [^>]*id="cv-erstellen-ki-status"[^>]*tabindex="-1"/);
  assert.match(html, /<script src="\/treffer-logik.js"><\/script>\s*<script src="\/lebenslauf-erstellen-logik.js">/);
});

test("opening sends nothing to the AI and shows the button, what it costs and the text for the AI", async () => {
  const { $, calls, doc } = await opened();

  assert.deepEqual(calls.senden, []);
  assert.equal($("cv-erstellen-ki-zeile").textContent, text("lebenslauf.ki-bereit"));
  assert.equal($("cv-erstellen-ki-knopf").textContent, "Vorschläge holen");
  assert.ok(visible($("cv-erstellen-ki-knopf")));
  assert.equal($("cv-erstellen-ki-knopf").getAttribute("aria-disabled"), null);
  assert.equal($("cv-erstellen-ki-kosten").textContent, "Etwa USD 0.03 und 1 Minute.");
  assert.ok(visible($("cv-erstellen-ki-text")));
  assert.equal(doc.activeElement, $("cv-erstellen-stationen").querySelector("input"));
  assert.deepEqual(aiStatus(calls).filter(([, said]) => said), []);
});

test("while the estimate runs the line says so and the button waits for it", async () => {
  const page = setup();
  const slow = pending(ESTIMATE);
  page.answers.estimate.push(slow.answer);
  page.$("cv-erstellen-oeffnen").click();
  await settle();
  const button = page.$("cv-erstellen-ki-knopf");

  assert.equal(page.$("cv-erstellen-ki-kosten").textContent, "Kosten und Dauer werden geschätzt …");
  assert.equal(button.getAttribute("aria-disabled"), "true");
  button.click();
  await settle();
  assert.deepEqual(page.calls.senden, []);

  slow.release();
  await settle();
  assert.equal(button.getAttribute("aria-disabled"), null);
  assert.equal(page.$("cv-erstellen-ki-kosten").textContent, "Etwa USD 0.03 und 1 Minute.");
});

test("over the credit the line warns and the button stays usable", async () => {
  const page = setup();
  page.answers.estimate.push({ ...ESTIMATE, kosten: 0.04, waehrung: "CHF", guthaben: 0.02, danach: 0 });
  page.$("cv-erstellen-oeffnen").click();
  await settle();

  assert.equal(page.$("cv-erstellen-ki-kosten").textContent,
               "Etwa CHF 0.04 und 1 Minute. Im Guthaben sind noch CHF 0.02, das reicht vielleicht nicht.");
  assert.equal(page.$("cv-erstellen-ki-knopf").disabled, false);
  assert.equal(page.$("cv-erstellen-ki-knopf").getAttribute("aria-disabled"), null);
});

test("with the credit used up the button is locked and the line links where to ask for a new code", async () => {
  const page = setup();
  page.answers.estimate.push({ ...ESTIMATE, kosten: 0.04, waehrung: "CHF", guthaben: 0, danach: 0 });
  page.$("cv-erstellen-oeffnen").click();
  await settle();
  const line = page.$("cv-erstellen-ki-kosten");

  assert.equal(line.textContent,
               "Etwa CHF 0.04 und 1 Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern, öffnet neuen Tab.");
  const link = line.querySelector("a");
  assert.equal(link.getAttribute("href"), Texte.CODE_REQUEST_URL);
  assert.equal(page.$("cv-erstellen-ki-knopf").disabled, true);
  page.$("cv-erstellen-ki-knopf").click();
  await settle();
  assert.deepEqual(page.calls.senden, []);
});

test("a failed estimate says why, offers Neu schätzen and leaves Vorschläge holen usable", async () => {
  const page = setup();
  page.answers.estimate.push(new Error("Die App antwortet nicht."));
  page.$("cv-erstellen-oeffnen").click();
  await settle();
  const again = page.$("cv-erstellen-ki-neu-schaetzen");

  assert.equal(page.$("cv-erstellen-ki-kosten").textContent, "Die Schätzung fehlt: Die App antwortet nicht.");
  assert.ok(visible(again));
  assert.equal(page.$("cv-erstellen-ki-knopf").getAttribute("aria-disabled"), null);
  assert.equal(page.$("cv-erstellen-ki-knopf").disabled, false);

  again.click();
  await settle();
  assert.equal(estimates(page.calls), 2);
  assert.equal(page.$("cv-erstellen-ki-kosten").textContent, "Etwa USD 0.03 und 1 Minute.");
  assert.equal(again.hidden, true);
});

test("with a saved CV for this application the box says so and offers Neu vorschlagen lassen with its cost", async () => {
  const { $, calls } = await opened({ form: SAVED });

  assert.deepEqual(calls.senden, []);
  assert.equal($("cv-erstellen-ki-zeile").textContent, text("lebenslauf.ki-gespeichert"));
  assert.match($("cv-erstellen-ki-zeile").textContent, /Ihre Auswahl gespeichert/);
  assert.equal($("cv-erstellen-ki-knopf").textContent, "Neu vorschlagen lassen");
  assert.equal($("cv-erstellen-ki-kosten").textContent, "Etwa USD 0.03 und 1 Minute.");
  assert.ok(visible($("cv-erstellen-ki-text")));
});

test("after the click the button stays, marked busy, the status says the AI suggests, and a second press asks nothing", async () => {
  const page = await opened();
  const { $, calls, answers, doc } = page;
  const slow = pending(SUGGESTION);
  answers.senden.push(slow.answer);

  const button = await pressed(page);
  assert.ok(visible(button), "hiding the row would drop the focus");
  assert.equal(doc.activeElement, button);
  assert.equal(button.getAttribute("aria-disabled"), "true");
  assert.equal(button.disabled, false, "a disabled button loses the focus");
  assert.equal($("cv-erstellen-ki-zeile").hidden, true);
  assert.deepEqual(aiStatus(calls).at(-1), ["cv-erstellen-ki-status", "Die KI schlägt vor …", ""]);
  button.click();
  await settle();
  assert.equal(calls.senden.length, 1);

  slow.release();
  await settle();
  assert.equal($("cv-erstellen-ki-knoepfe").hidden, true);
  assert.equal(doc.activeElement, boxes($)[0]);
  assert.ok(boxes($).every(box => box.checked));
  assert.equal($("cv-erstellen-ki-zeile").hidden, false);
  assert.equal($("cv-erstellen-ki-zeile").textContent, text("lebenslauf.ki-angewendet"));
  assert.deepEqual(aiStatus(calls).at(-1),
                   ["cv-erstellen-ki-status", `Vorschlag der KI angewendet: 2 Empfehlungen. ${COST}`, "ok"]);
});

test("a repeat from the cache says what it did and nothing about costs", async () => {
  const page = await opened();
  page.answers.senden.push({ ...SUGGESTION, kosten_usd: 0, wiederholt: true, kosten_text: "" });
  await pressed(page);
  assert.equal(aiStatus(page.calls).at(-1)[1], "Vorschlag der KI angewendet: 2 Empfehlungen.");
});

test("with nothing to recommend the focus goes to the status line that says so", async () => {
  const page = await opened({ form: SAVED });
  page.answers.senden.push({ ...SUGGESTION, empfehlungen: [] });

  await pressed(page);

  assert.equal(page.doc.activeElement, page.$("cv-erstellen-ki-status"));
  assert.match(aiStatus(page.calls).at(-1)[1], /^Die KI schlägt für diese Stelle nichts anderes vor\./);
});

test("on an error the focus stays on the button, now Nochmals vorschlagen, and the error goes to the status once", async () => {
  const page = await opened({ form: SAVED });
  const failure = "Kein Vorschlag der KI. Die KI antwortet gerade nicht. Nichts berechnet. Die Auswahl bleibt, wie sie ist.";
  page.answers.senden.push(new Error(failure));
  const before = aiStatus(page.calls).length;

  const button = await pressed(page);

  assert.equal(page.doc.activeElement, button);
  assert.ok(visible(button));
  assert.equal(button.textContent, "Nochmals vorschlagen");
  assert.equal(button.getAttribute("aria-disabled"), null);
  assert.deepEqual(aiStatus(page.calls).slice(before), [["cv-erstellen-ki-status", "Die KI schlägt vor …", ""],
                                                        ["cv-erstellen-ki-status", failure, "fehler"]]);
});

test("without the job ad the box says what is missing, leads to the Stellentext and estimates nothing", async () => {
  const { $, doc, calls } = await opened({ form: { ...FORM, ki: "ohne_inserat" } });

  assert.equal($("cv-erstellen-ki-zeile").textContent, "Für Vorschläge der KI fehlt noch der Stellentext.");
  assert.ok(visible($("cv-erstellen-ki-stellentext")));
  assert.equal(visible($("cv-erstellen-ki-knopf")), false);
  assert.equal($("cv-erstellen-ki-kosten").textContent, "");
  $("cv-erstellen-ki-stellentext").click();
  assert.equal($("s-stelle").open, true);
  assert.equal($("s-stelle").scrolled, 1);
  assert.equal(doc.activeElement, $("stellentext"));
  assert.equal(calls.senden.length, 0);
  assert.equal(estimates(calls), 0);
});

test("without AI the box offers to switch it on, worded for an apprenticeship", async () => {
  const { $, calls } = await opened({ form: { ...FORM, ki: "aus" }, satz: "lehrstelle-du" });

  assert.equal($("cv-erstellen-ki-zeile").textContent,
               "Mit KI schlägt die App für diese Lehrstelle Stationen, Reihenfolge und Kurzprofil vor.");
  assert.equal($("cv-erstellen-ki-knopf").textContent, "KI einschalten");
  assert.equal(visible($("cv-erstellen-ki-stellentext")), false);
  assert.equal(estimates(calls), 0);
});

test("once the AI is switched on, the box shows the button and its cost, sends nothing, and keeps the focus", async () => {
  const page = await opened({ form: { ...FORM, ki: "aus" } });
  page.answers.form.push(FORM);

  const button = await pressed(page);

  assert.equal(page.calls.einrichten, 1);
  assert.deepEqual(page.calls.senden, []);
  assert.equal(button.textContent, "Vorschläge holen");
  assert.equal(page.$("cv-erstellen-ki-kosten").textContent, "Etwa USD 0.03 und 1 Minute.");
  assert.equal(page.doc.activeElement, button);
});

test("when the app cannot tell whether the AI is on now, the box says why instead of staying silent", async () => {
  const page = await opened({ form: { ...FORM, ki: "aus" } });
  page.answers.form.push(new Error("Die App antwortet nicht."));

  const button = await pressed(page);

  assert.deepEqual(aiStatus(page.calls).at(-1), ["cv-erstellen-ki-status", "Die App antwortet nicht.", "fehler"]);
  assert.equal(page.doc.activeElement, button);
  assert.equal(page.calls.senden.length, 0);
});

// G76 (#294): every change of content and looks goes to the preview (lebenslauf-vorschau.js) as a draft.
const drafts = calls => calls.events.filter(event => event.type === "lebenslauf-entwurf")
  .map(event => JSON.parse(JSON.stringify(event.detail)));

test("opening hands the choice to the preview at once", async () => {
  const { calls } = await opened();

  const last = drafts(calls).at(-1);
  assert.equal(last.now, true);
  assert.deepEqual(last.body, { id: "b1", stand: "abc", stationen: { work: [0, 1] }, design: "zweispaltig",
                                berufsbezeichnung: "Entwicklerin", kurzprofil: "Erster Satz. Zweiter Satz.", bezeichnung: "Daten" });
});

test("each change of stations, order, texts and looks hands a new draft to the preview", async () => {
  const { $, calls } = await opened();
  const before = drafts(calls).length;

  $("cv-erstellen-stationen").querySelectorAll("input")[1].dispatch("change");
  assert.deepEqual(drafts(calls).at(-1).body.stationen, { work: [0] });
  [...$("cv-erstellen-stationen").querySelectorAll("button")].find(b => b.getAttribute("data-key") === "work-0-1").click();
  $("cv-erstellen-beruf").value = "Leiterin";
  $("cv-erstellen-beruf").dispatch("input");
  assert.equal(drafts(calls).at(-1).body.berufsbezeichnung, "Leiterin");
  $("cv-erstellen-profil").value = "Neu.";
  $("cv-erstellen-profil").dispatch("input");
  assert.equal(drafts(calls).at(-1).body.kurzprofil, "Neu.");
  [...$("cv-erstellen-designs").querySelectorAll("input")].find(i => i.getAttribute("value") === "einspaltig").dispatch("change");

  const sent = drafts(calls).slice(before);
  assert.equal(sent.length, 5);
  assert.ok(sent.every(draft => !draft.now), "changes wait for a pause");
  assert.equal(sent.at(-1).body.design, "einspaltig");
});

test("without any station the preview gets an empty state, not a failure", async () => {
  const { $, calls } = await opened();

  for (const box of $("cv-erstellen-stationen").querySelectorAll("input")) box.dispatch("change");

  assert.deepEqual(drafts(calls).at(-1), { body: null, empty: true });
});

test("closing the panel tells the preview to stop", async () => {
  const { $, calls } = await opened();

  $("cv-erstellen-abbrechen").click();

  assert.deepEqual(drafts(calls).at(-1), { closed: true });
});

test("«Neu laden» in the preview closes the panel and opens it again with Meine Angaben as they are now", async () => {
  const page = await opened();
  const { $, calls, doc } = page;
  const before = calls.holen.filter(route => route === ROUTE).length;

  for (const handler of doc.listeners["lebenslauf-neu-oeffnen"] || []) handler({});
  await settle();

  assert.equal(calls.holen.filter(route => route === ROUTE).length, before + 1, "the form is fetched anew");
  assert.equal($("cv-erstellen").hidden, false, "the panel is open again");
  assert.ok(drafts(calls).some(draft => draft.closed), "the old preview stopped");
  assert.equal(drafts(calls).at(-1).now, true, "the new choice is built at once");
});

// G77 (#295): photo, colour and mark of this CV under «Aussehen», each change a new draft for the preview.
const LOOKED = { ...FORM, aussehen: { foto: true, zeichen: "passend", akzent: "passend" },
                 aussehen_angebot: { foto_vorhanden: true, initialen: "EB", logo: false } };

test("the panel shows «Mit Foto» as given and names mark and colour beside the button", async () => {
  const { $ } = await opened({ form: LOOKED });

  assert.equal($("cv-erstellen-look").hidden, false);
  assert.equal($("cv-erstellen-foto").checked, true);
  assert.equal($("cv-erstellen-foto").disabled, false);
  assert.equal(spoken($("cv-erstellen-farbe-stand")), "Ohne Zeichen, Farbe: passend zum Design");
  assert.equal(seen($("cv-erstellen-farbe-stand")), "Ohne Zeichen · Farbe: passend zum Design");
  assert.equal($("cv-erstellen-farbe").hidden, true);
});

/** What the eye sees: without visually hidden text. What a screen reader hears: without aria-hidden text. */
const seen = node => (node.className === "visually-hidden" ? "" : node.children
  ? node.children.map(seen).join("") : node.textContent);
const spoken = node => (node.getAttribute?.("aria-hidden") === "true" ? "" : node.children
  ? node.children.map(spoken).join("") : node.textContent);
const option = (box, value) => box.querySelectorAll("input").find(input => input.getAttribute("value") === value);
const label = input => input.parent;

test("each mark of initials has its sentence below, linked to its radio; a locked one has its reason below that", async () => {
  const { $ } = await opened({ form: LOOKED });
  $("cv-erstellen-farbe-oeffnen").click();
  const byId = $;

  const ring = option($("cv-erstellen-zeichen"), "ring");
  assert.equal(ring.getAttribute("aria-describedby"), "cv-erstellen-zeichen-ring-satz");
  assert.equal(byId("cv-erstellen-zeichen-ring-satz").textContent, "Initialen im Ring");
  assert.equal(byId("cv-erstellen-zeichen-ring-satz").className, "cv-create__mark-note");
  assert.equal(option($("cv-erstellen-zeichen"), "passend").getAttribute("aria-describedby"), null);
  const logo = option($("cv-erstellen-zeichen"), "logo");
  assert.equal(logo.getAttribute("aria-describedby"), "cv-erstellen-zeichen-logo-grund");
  assert.equal(label(logo).querySelectorAll("span").some(span => span.className === "cv-create__mark-note"), false);
});

test("«Passend zum Design» spans the row, names the swatch it is, and that swatch is not offered twice", async () => {
  const { $ } = await opened({ form: LOOKED });
  $("cv-erstellen-farbe-oeffnen").click();

  const inputs = $("cv-erstellen-akzent").querySelectorAll("input");
  assert.equal(inputs.length, 7);
  assert.equal(option($("cv-erstellen-akzent"), "#38495d"), undefined, "Schieferblau is the design's own");
  const fitting = option($("cv-erstellen-akzent"), "passend");
  assert.match(label(fitting).className, /mark-swatch--wide/);
  assert.equal(fitting.getAttribute("aria-describedby"), "cv-erstellen-akzent-passend-farbe");
  assert.equal($("cv-erstellen-akzent-passend-farbe").textContent, "Schieferblau");
  const css = fs.readFileSync(path.join(SEITEN, "stil.css"), "utf8");
  assert.match(css, /\.mark-swatch--wide \{[^}]*grid-column: 1 \/ -1/);
  assert.match(css, /\.cv-create__mark \.mark-swatch__chip rect \{[^}]*stroke: var\(--line-strong\)/);
});

test("a blocked «Mit Foto» shows no tick, and back with Zweispaltig the tick returns", async () => {
  const { $ } = await opened({ form: LOOKED });
  const design = value => $("cv-erstellen-designs").querySelectorAll("input").find(i => i.getAttribute("value") === value);

  design("einspaltig").dispatch("change");
  assert.equal($("cv-erstellen-foto").checked, false);
  design("zweispaltig").dispatch("change");
  assert.equal($("cv-erstellen-foto").checked, true);
});

test("the panel says the dossier rule once, in the hint below Aussehen", () => {
  const html = fs.readFileSync(path.join(SEITEN, "bewerbung.html"), "utf8");
  assert.doesNotMatch(html, /lebenslauf\.dossier-farbe/);
  assert.throws(() => text("lebenslauf.dossier-farbe"), /Unbekannter Text/);
  const hint = "Gilt nur für diese Bewerbung. Ein Dossier hat Design, Farbe und Zeichen aus «Dossier gestalten»; das Foto nimmt es von hier.";
  assert.equal(text("lebenslauf.aussehen-hinweis"), hint);
  assert.equal(text("lebenslauf.aussehen-hinweis", "stelle-du"), hint);
  assert.match(html, /<p class="field__hint" data-text="lebenslauf.aussehen-hinweis">Gilt nur für diese Bewerbung\. Ein Dossier hat Design, Farbe und Zeichen aus «Dossier gestalten»; das Foto nimmt es von hier\.<\/p>/);
});

test("without a look in the answer the controls stay away and the request is as before", async () => {
  const { $ } = await opened();

  assert.equal($("cv-erstellen-look").hidden, true);
  assert.equal($("cv-erstellen-farbe-stand").hidden, true);
});

test("«Farbe und Zeichen ändern» opens marks and colours, says so, and puts the focus on the chosen mark", async () => {
  const { $, doc } = await opened({ form: LOOKED });

  $("cv-erstellen-farbe-oeffnen").click();

  assert.equal($("cv-erstellen-farbe").hidden, false);
  assert.equal($("cv-erstellen-farbe-oeffnen").getAttribute("aria-expanded"), "true");
  const marks = $("cv-erstellen-zeichen").querySelectorAll("input");
  assert.deepEqual(marks.map(input => input.getAttribute("value")),
                   ["passend", "ring", "block", "verschraenkt", "linie", "punkt", "logo"]);
  assert.equal(marks.find(input => input.getAttribute("value") === "logo").disabled, true);
  assert.equal($("cv-erstellen-akzent").querySelectorAll("input").length, 7);
  assert.equal(doc.activeElement, marks[0]);
  $("cv-erstellen-farbe-oeffnen").click();
  assert.equal($("cv-erstellen-farbe").hidden, true);
  assert.equal($("cv-erstellen-farbe-oeffnen").getAttribute("aria-expanded"), "false");
});

test("photo, mark and colour each hand a new draft to the preview and keep the focus", async () => {
  const { $, calls, doc } = await opened({ form: LOOKED });
  $("cv-erstellen-farbe-oeffnen").click();

  $("cv-erstellen-foto").checked = false;
  $("cv-erstellen-foto").dispatch("change");
  assert.deepEqual(drafts(calls).at(-1).body.aussehen, { foto: false, zeichen: "passend", akzent: "passend" });
  const ring = $("cv-erstellen-zeichen").querySelectorAll("input").find(input => input.getAttribute("value") === "ring");
  ring.focus();
  ring.dispatch("change");
  assert.equal(drafts(calls).at(-1).body.aussehen.zeichen, "ring");
  assert.equal(doc.activeElement.id, "cv-erstellen-zeichen-ring", "the focus stays on the mark just chosen");
  $("cv-erstellen-akzent").querySelectorAll("input").find(input => input.getAttribute("value") === "#7a2e3a").dispatch("change");
  assert.deepEqual(drafts(calls).at(-1).body.aussehen, { foto: false, zeichen: "ring", akzent: "#7a2e3a" });
  assert.equal(seen($("cv-erstellen-farbe-stand")), "Zeichen: Ring · Farbe: Weinrot");
});

test("with Einspaltig «Mit Foto» cannot be ticked and says why", async () => {
  const { $ } = await opened({ form: LOOKED });

  $("cv-erstellen-designs").querySelectorAll("input").find(i => i.getAttribute("value") === "einspaltig").dispatch("change");

  assert.equal($("cv-erstellen-foto").disabled, true);
  assert.equal($("cv-erstellen-foto-grund").hidden, false);
  assert.equal($("cv-erstellen-foto-grund").textContent, "Einspaltig zeigt kein Foto.");
});

test("the texts of the look speak Sie or du", () => {
  assert.match(text("lebenslauf.foto-fehlt"), /fügen Sie/);
  assert.match(text("lebenslauf.foto-fehlt", "stelle-du"), /fügst du/);
  assert.equal(text("lebenslauf.zeichen-logo"), "Ihr Logo");
  assert.equal(text("lebenslauf.zeichen-logo", "stelle-du"), "Dein Logo");
  assert.match(text("lebenslauf.zeichen-hinweis", "stelle-du"), /deinen Initialen/);
});

test("the title and the intro of the panel speak Sie or du and name an apprenticeship", () => {
  assert.equal(text("lebenslauf.erstellen-titel"), "Lebenslauf für diese Stelle");
  assert.equal(text("lebenslauf.erstellen-titel", "lehrstelle-du"), "Lebenslauf für diese Lehrstelle");
  assert.match(text("lebenslauf.erstellen-intro"), /aus Ihren Angaben.*wählen Sie getrennt/);
  assert.match(text("lebenslauf.erstellen-intro", "stelle-du"), /aus deinen Angaben.*wählst du getrennt/);
  const html = fs.readFileSync(path.join(SEITEN, "bewerbung.html"), "utf8");
  assert.match(html, /<h3 class="cv-create__title" data-text="lebenslauf.erstellen-titel">/);
  assert.match(html, /<p class="field__hint" data-text="lebenslauf.erstellen-intro">/);
});
