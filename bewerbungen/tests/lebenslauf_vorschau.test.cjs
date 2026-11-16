// The live preview in „Lebenslauf erstellen“ (G76, #294): the logic without DOM, and the script with a small
// stand-in DOM and a fake clock: it waits for a pause in the changes, a newer request wins, a failed build replaces
// the preview with a message, the focus never moves, and the live region speaks only when something changes that
// the person cannot see where they are. Invented data, the server is faked.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Logic = require("../seiten/lebenslauf-vorschau-logik.js");
const Texte = require("../seiten/texte.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const ROUTE = "/api/lebenslauf/erstellen/vorschau";
const BODY = { id: "b1", stand: "abc", stationen: { work: [0] }, design: "zweispaltig", berufsbezeichnung: "Entwicklerin",
               kurzprofil: "Baut Webseiten.", bezeichnung: "Web" };
const FAILED = "Die Vorschau lässt sich gerade nicht erstellen. basics.x-image: unbekannte Felder";

test("the title names the pages, without a preview just the word", () => {
  assert.equal(Logic.title(2), "Vorschau · 2 Seiten");
  assert.equal(Logic.title(1), "Vorschau · 1 Seite");
  assert.equal(Logic.title(null), "Vorschau");
});

test("a reason from the page is worded like one from the server", () => {
  assert.equal(Logic.failedText("Bitte mindestens eine Station wählen."),
               "Die Vorschau lässt sich gerade nicht erstellen. Bitte mindestens eine Station wählen.");
  assert.equal(Logic.failedText(FAILED), FAILED);
});

test("the live region speaks only when the pages change, a build fails or works again", () => {
  assert.equal(Logic.announcement(null, { pages: 2 }), "", "the first preview is there to be read, not announced");
  assert.equal(Logic.announcement({ pages: 2 }, { pages: 2 }), "", "the same count says nothing");
  assert.equal(Logic.announcement({ pages: 2 }, { pages: 3 }), "Die Vorschau hat jetzt 3 Seiten.");
  assert.equal(Logic.announcement({ pages: 2 }, { pages: 1 }), "Die Vorschau hat jetzt 1 Seite.");
  assert.equal(Logic.announcement({ pages: 2 }, { failed: FAILED }), FAILED);
  assert.equal(Logic.announcement({ failed: FAILED }, { failed: FAILED }), "", "the same failure once");
  assert.equal(Logic.announcement({ failed: FAILED }, { pages: 2 }), "Die Vorschau ist wieder da, 2 Seiten.");
  assert.equal(Logic.announcement(null, { failed: FAILED }), FAILED);
});

test("each page image says which page it is", () => {
  assert.equal(Logic.pageAlt(1, 2), "Lebenslauf, Seite 1 von 2");
});

test("the text under the preview speaks Sie or du", () => {
  assert.match(Texte.text("lebenslauf.vorschau-hinweis", "stelle-sie"), /Ihrer Wahl/);
  assert.match(Texte.text("lebenslauf.vorschau-hinweis", "stelle-du"), /deiner Wahl/);
});

// --- the script ---

class FakeNode {}
class FakeText extends FakeNode {
  constructor(text) { super(); this.data = String(text); this.parent = null; }
  get textContent() { return this.data; }
}

class FakeElement extends FakeNode {
  constructor(doc, tag) {
    super();
    Object.assign(this, { doc, tagName: tag.toUpperCase(), attrs: new Map(), children: [], parent: null, listeners: {},
      className: "", open: false });
  }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  removeAttribute(name) { this.attrs.delete(name); }
  get id() { return this.getAttribute("id") || ""; }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  get src() { return this.getAttribute("src") || ""; }
  set src(value) { this.setAttribute("src", value); }
  get alt() { return this.getAttribute("alt") || ""; }
  set alt(value) { this.setAttribute("alt", value); }
  get href() { return this.getAttribute("href") || ""; }
  set href(value) { this.setAttribute("href", value); }
  append(...nodes) {
    for (const given of nodes) {
      const node = given instanceof FakeNode ? given : new FakeText(given);
      node.parent = this;
      this.children.push(node);
    }
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  get textContent() { return this.children.map(child => child.textContent).join(""); }
  set textContent(text) { this.replaceChildren(...(String(text) ? [String(text)] : [])); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatch(type) { for (const handler of this.listeners[type] || []) handler({ type, target: this }); }
  click() { this.dispatch("click"); }
  focus() { this.doc.activeElement = this; }
  showModal() { this.open = true; }
  close() { this.open = false; this.dispatch("close"); }
  all() { return this.children.filter(c => c instanceof FakeElement).flatMap(c => [c, ...c.all()]); }
  querySelectorAll(selector) { return this.all().filter(node => node.tagName === selector.toUpperCase()); }
}

function setup() {
  const doc = { activeElement: null, listeners: {}, createElement: tag => new FakeElement(doc, tag),
                addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); } };
  const calls = { senden: [] };
  const answers = [];
  const clock = { now: 0, timers: [] };
  function el(tag, attributes = {}, ...children) {
    const element = doc.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (value === false || value === null || value === undefined) continue;
      if (name.startsWith("on")) element.addEventListener(name.slice(2), value);
      else if (name === "class") element.className = value;
      else element.setAttribute(name, value === true ? "" : value);
    }
    for (const child of children.flat()) if (child !== null && child !== undefined) element.append(child);
    return element;
  }
  const root = el("main", {},
    el("button", { id: "cv-erstellen-beruf" }),
    el("aside", { id: "cv-vorschau" },
      el("h3", { id: "cv-vorschau-titel" }, "Vorschau"),
      el("img", { id: "cv-vorschau-bild", hidden: true }),
      el("p", { id: "cv-vorschau-fehler", hidden: true }),
      el("div", { id: "cv-vorschau-links", hidden: true },
        el("button", { id: "cv-vorschau-gross", type: "button" }, "Gross ansehen"),
        el("a", { id: "cv-vorschau-pdf" }, "Als PDF öffnen")),
      el("p", { id: "cv-vorschau-dossier", hidden: true }),
      el("p", { id: "cv-vorschau-status", role: "status" })),
    el("dialog", { id: "cv-vorschau-dialog" },
      el("h2", { id: "cv-vorschau-dialog-titel" }),
      el("div", { id: "cv-vorschau-seiten" }),
      el("a", { id: "cv-vorschau-dialog-pdf" }),
      el("button", { id: "cv-vorschau-schliessen", type: "button" }, "Schliessen")));
  doc.getElementById = id => root.all().find(node => node.id === id) || null;
  const window = {
    App: {
      el,
      url: (route, parameters = {}) => `${route}?${new URLSearchParams(parameters)}`,
      senden: async (route, body) => {
        calls.senden.push([route, body]);
        const next = answers.shift();
        const value = typeof next === "function" ? await next() : next;
        if (value instanceof Error) throw value;
        return value;
      },
    },
    LebenslaufVorschauLogik: Logic,
  };
  const context = {
    window, document: doc, location: { search: "?id=b1" }, URLSearchParams, console,
    setTimeout: (run, delay) => { clock.timers.push({ at: clock.now + delay, run }); return clock.timers.length; },
    clearTimeout: handle => { if (clock.timers[handle - 1]) clock.timers[handle - 1].run = null; },
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(SEITEN, "lebenslauf-vorschau.js"), "utf8"), context);
  const $ = id => doc.getElementById(id);
  const draft = detail => { for (const handler of doc.listeners["lebenslauf-entwurf"] || []) handler({ detail }); };
  const loaded = entry => { for (const handler of doc.listeners["bewerbung-geladen"] || []) handler({ detail: { bewerbung: entry } }); };
  const advance = async ms => {
    clock.now += ms;
    for (const timer of clock.timers) if (timer.run && timer.at <= clock.now) { const run = timer.run; timer.run = null; run(); }
    await settle();
  };
  return { doc, calls, answers, $, draft, loaded, advance };
}

const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };

function pending(value) {
  let release;
  const done = new Promise(resolve => { release = () => resolve(value); });
  return { answer: () => done, release: () => release() };
}

test("opening builds at once and shows page 1, the page count and both ways to look closer", async () => {
  const page = setup();
  page.answers.push({ schluessel: "k1", seiten: 2 });

  page.draft({ body: BODY, now: true });
  await settle();

  assert.deepEqual(page.calls.senden, [[ROUTE, BODY]]);
  assert.equal(page.$("cv-vorschau-titel").textContent, "Vorschau · 2 Seiten");
  assert.equal(page.$("cv-vorschau-bild").hidden, false);
  assert.equal(page.$("cv-vorschau-bild").src, `${ROUTE}/seite?id=b1&schluessel=k1&seite=1`);
  assert.equal(page.$("cv-vorschau-bild").alt, "Lebenslauf, Seite 1 von 2");
  assert.equal(page.$("cv-vorschau-links").hidden, false);
  assert.equal(page.$("cv-vorschau-pdf").href, `${ROUTE}/pdf?id=b1&schluessel=k1`);
  assert.equal(page.$("cv-vorschau").getAttribute("aria-busy"), "false");
  assert.equal(page.$("cv-vorschau-status").textContent, "");
});

test("changes wait for a pause; only the last one is built", async () => {
  const page = setup();
  page.answers.push({ schluessel: "k1", seiten: 2 }, { schluessel: "k2", seiten: 2 });
  page.draft({ body: BODY, now: true });
  await settle();

  page.draft({ body: { ...BODY, kurzprofil: "B" } });
  await page.advance(Logic.DELAY_MS - 100);
  page.draft({ body: { ...BODY, kurzprofil: "Ba" } });
  await page.advance(Logic.DELAY_MS - 100);
  assert.equal(page.calls.senden.length, 1, "nothing while the person keeps typing");
  assert.equal(page.$("cv-vorschau").getAttribute("aria-busy"), "true", "the old preview is marked as about to change");
  await page.advance(100);

  assert.deepEqual(page.calls.senden.map(([, body]) => body.kurzprofil), ["Baut Webseiten.", "Ba"]);
  assert.match(page.$("cv-vorschau-bild").src, /schluessel=k2/);
});

test("a newer request wins: the answer of an older one is dropped", async () => {
  const page = setup();
  const slow = pending({ schluessel: "alt", seiten: 3 });
  page.answers.push(slow.answer, { schluessel: "neu", seiten: 2 });

  page.draft({ body: BODY, now: true });
  await settle();
  page.draft({ body: { ...BODY, design: "einspaltig" }, now: true });
  await settle();
  slow.release();
  await settle();

  assert.match(page.$("cv-vorschau-bild").src, /schluessel=neu/);
  assert.equal(page.$("cv-vorschau-titel").textContent, "Vorschau · 2 Seiten");
});

test("a failed build shows its message instead of the old preview and says it once", async () => {
  const page = setup();
  page.answers.push({ schluessel: "k1", seiten: 2 }, new Error(FAILED), new Error(FAILED));
  page.draft({ body: BODY, now: true });
  await settle();

  page.draft({ body: BODY, now: true });
  await settle();

  assert.equal(page.$("cv-vorschau-bild").hidden, true);
  assert.equal(page.$("cv-vorschau-bild").src, "", "the old page is gone, not only hidden");
  assert.equal(page.$("cv-vorschau-links").hidden, true);
  assert.equal(page.$("cv-vorschau-fehler").hidden, false);
  assert.equal(page.$("cv-vorschau-fehler").textContent, FAILED);
  assert.equal(page.$("cv-vorschau-titel").textContent, "Vorschau");
  assert.equal(page.$("cv-vorschau-status").textContent, FAILED);

  page.$("cv-vorschau-status").textContent = "";
  page.draft({ body: BODY, now: true });
  await settle();
  assert.equal(page.$("cv-vorschau-status").textContent, "", "the same failure again stays quiet");
});

test("a choice the page cannot send fails at once without a request", async () => {
  const page = setup();
  page.answers.push({ schluessel: "k1", seiten: 2 });
  page.draft({ body: BODY, now: true });
  await settle();

  page.draft({ body: null, reason: "Bitte mindestens eine Station wählen." });
  await page.advance(Logic.DELAY_MS);

  assert.equal(page.calls.senden.length, 1);
  assert.equal(page.$("cv-vorschau-fehler").textContent,
               "Die Vorschau lässt sich gerade nicht erstellen. Bitte mindestens eine Station wählen.");
  assert.equal(page.$("cv-vorschau-bild").hidden, true);
});

test("a page that does not load shows a message instead of a broken image", async () => {
  const page = setup();
  page.answers.push({ schluessel: "k1", seiten: 2 });
  page.draft({ body: BODY, now: true });
  await settle();

  page.$("cv-vorschau-bild").dispatch("error");

  assert.equal(page.$("cv-vorschau-bild").hidden, true);
  assert.equal(page.$("cv-vorschau-fehler").hidden, false);
  assert.match(page.$("cv-vorschau-fehler").textContent, /^Die Vorschau lässt sich gerade nicht/);
});

test("updates never move the focus and announce only a new page count", async () => {
  const page = setup();
  page.answers.push({ schluessel: "k1", seiten: 2 }, { schluessel: "k2", seiten: 2 }, { schluessel: "k3", seiten: 3 });
  page.$("cv-erstellen-beruf").focus();

  page.draft({ body: BODY, now: true });
  await settle();
  page.draft({ body: BODY, now: true });
  await settle();
  assert.equal(page.$("cv-vorschau-status").textContent, "");
  page.draft({ body: BODY, now: true });
  await settle();

  assert.equal(page.$("cv-vorschau-status").textContent, "Die Vorschau hat jetzt 3 Seiten.");
  assert.equal(page.doc.activeElement, page.$("cv-erstellen-beruf"));
});

test("closing the panel drops a pending change and an answer still under way", async () => {
  const page = setup();
  const slow = pending({ schluessel: "spaet", seiten: 2 });
  page.answers.push(slow.answer);
  page.draft({ body: BODY, now: true });
  await settle();
  page.$("cv-vorschau-status").textContent = FAILED;
  page.draft({ closed: true });
  assert.equal(page.$("cv-vorschau-status").textContent, "", "nothing stale stays in the live region");
  page.draft({ body: BODY });
  page.draft({ closed: true });
  slow.release();
  await page.advance(Logic.DELAY_MS);

  assert.equal(page.calls.senden.length, 1);
  assert.equal(page.$("cv-vorschau-bild").src, "");
  assert.equal(page.$("cv-vorschau").getAttribute("aria-busy"), "false");
});

test("«Gross ansehen» shows every page large in a dialog and gives the focus back on closing", async () => {
  const page = setup();
  page.answers.push({ schluessel: "k1", seiten: 2 });
  page.draft({ body: BODY, now: true });
  await settle();
  const button = page.$("cv-vorschau-gross");
  button.focus();

  button.click();

  const dialog = page.$("cv-vorschau-dialog");
  assert.equal(dialog.open, true);
  const images = page.$("cv-vorschau-seiten").querySelectorAll("img");
  assert.deepEqual(images.map(image => image.src), [1, 2].map(n => `${ROUTE}/seite?id=b1&schluessel=k1&seite=${n}&groesse=gross`));
  assert.deepEqual(images.map(image => image.alt), ["Lebenslauf, Seite 1 von 2", "Lebenslauf, Seite 2 von 2"]);
  assert.equal(page.$("cv-vorschau-dialog-titel").textContent, "Vorschau · 2 Seiten");
  assert.equal(page.$("cv-vorschau-dialog-pdf").href, `${ROUTE}/pdf?id=b1&schluessel=k1`);
  assert.equal(page.doc.activeElement, page.$("cv-vorschau-schliessen"));

  page.$("cv-vorschau-schliessen").click();
  assert.equal(dialog.open, false);
  assert.equal(page.doc.activeElement, button);
});

test("with a dossier the preview says that the dossier has its own design", () => {
  const page = setup();
  page.loaded({ id: "b1", unterlagen: "dossier" });
  assert.equal(page.$("cv-vorschau-dossier").hidden, false);
  page.loaded({ id: "b1" });
  assert.equal(page.$("cv-vorschau-dossier").hidden, true);
});

test("the page markup: preview beside the choice, a live region, the dialog, scripts in order", () => {
  const html = fs.readFileSync(path.join(SEITEN, "bewerbung.html"), "utf8");
  const panel = html.slice(html.indexOf('id="cv-erstellen"'), html.indexOf('id="s-anschreiben"'));
  for (const id of ["cv-vorschau", "cv-vorschau-titel", "cv-vorschau-bild", "cv-vorschau-fehler", "cv-vorschau-links",
                    "cv-vorschau-gross", "cv-vorschau-pdf", "cv-vorschau-dossier", "cv-vorschau-status"]) {
    assert.ok(panel.includes(`id="${id}"`), id);
  }
  assert.match(panel, /<p [^>]*id="cv-vorschau-status"[^>]*role="status"/);
  assert.match(panel, /<aside [^>]*id="cv-vorschau"[^>]*aria-labelledby="cv-vorschau-titel"/);
  assert.ok(panel.indexOf('id="cv-vorschau"') < panel.indexOf('id="cv-erstellen-speichern"'),
            "on a narrow screen the preview comes before «Lebenslauf übernehmen»");
  assert.match(html, /<dialog [^>]*id="cv-vorschau-dialog"[^>]*aria-labelledby="cv-vorschau-dialog-titel"/);
  assert.ok(html.indexOf('id="cv-vorschau-schliessen"') < html.indexOf('id="cv-vorschau-seiten"'),
            "«Schliessen» above the pages: its focus shows the first page");
  assert.match(html, /<script src="\/lebenslauf-vorschau-logik.js"><\/script>\s*<script src="\/lebenslauf-vorschau.js">/);
});
