// The cost of „Suchbegriffe prüfen lassen“ on Suche einstellen (#329), with a small stand-in DOM: the line beside the
// link is worded like „Alle prüfen“, the exclusions box and the CV suggestions, in every state of the estimate.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Texte = require("../seiten/texte.js");
const DotLine = require("../seiten/dot-line.js");

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
    "/api/suchbegriffe/hinweis": { verfuegbar: true, hinweis: null },
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
    SucheAnzeige: { regionText: () => "", zusammenfassung: () => [] },
    DotLine,
    SucheRahmen: { zeige: () => {} },
    TitelfilterBeispiele: { begriffe: () => {}, beispiele: () => {} },
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
  assert.equal(line.textContent, "Etwa USD\u00a00.03 und 1\u00a0Minute.");
  assert.equal(link.getAttribute("href"), "/suchbegriffe");
  assert.equal(link.getAttribute("aria-disabled"), null);
});

test("with the mediation the line is in CHF and names what stays in the credit", async () => {
  const { line } = await opened(CODE);
  assert.equal(line.textContent, "Etwa CHF\u00a00.04 und 1\u00a0Minute. Danach bleiben CHF\u00a04.21 im Guthaben.");
});

test("over the credit the line says it may not be enough, and the link stays", async () => {
  const { line, link } = await opened({ ...CODE, guthaben: 0.02, danach: 0 });
  assert.equal(line.textContent, "Etwa CHF\u00a00.04 und 1\u00a0Minute. Im Guthaben sind noch CHF\u00a00.02, das reicht vielleicht nicht.");
  assert.equal(link.getAttribute("href"), "/suchbegriffe");
});

test("with the credit used up the line links where to ask for a new code, and the link is locked", async () => {
  const { line, link } = await opened({ ...CODE, guthaben: 0, danach: 0 });
  // The link carries a hidden „, öffnet neuen Tab“ for screen readers.
  assert.equal(line.textContent, "Etwa CHF\u00a00.04 und 1\u00a0Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern, öffnet neuen Tab.");
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

// #334: the hint above the hit list and „Neu vorschlagen“ on /suchbegriffe priced the same way, from the estimate in
// the currency of the way; the hint used to put a dollar amount beside CHF.
const HINT = { verfuegbar: true, hinweis: { begriff: "Engineer", anzahl: 15, unter: 12, gesamt: 40, beispiele: [] },
  treffer: 40, seit: "2026-11-01" };
const MEDIATION = { ...OWN_KEY, waehrung: "CHF", guthaben: 4.25, danach: 4.22 };
const NACHSATZ = "Die KI kann bessere Begriffe vorschlagen. Geändert wird nur, was Sie übernehmen.";

/** Runs `scripts` with the routes `answers` (an Error: the route refused) and a stand-in DOM; gives the elements. */
async function ran(scripts, answers) {
  const elements = new Map();
  const doc = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, el("div"));
      return elements.get(id);
    },
    addEventListener() {},
    dispatchEvent() {},
  };
  const holen = async route => {
    if (!(route in answers)) throw new Error(`unexpected route ${route}`);
    if (answers[route] instanceof Error) throw answers[route];
    return answers[route];
  };
  const window = {
    App: { el, holen, senden: holen, status: () => {}, textsatz: async () => "stelle-sie" },
    Texte,
    DotLine,
    Meldungen: require("../seiten/meldungen.js"),
    VerworfenWoerterLogik: { ausAdresse: () => null },
    addEventListener() {},
  };
  const location = { hash: "", pathname: "/treffer", search: "" };
  const context = { window, document: doc, console, setTimeout, location, history: { replaceState() {} },
    CustomEvent: class {} };
  vm.createContext(context);
  for (const name of scripts) vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  await settled();
  return { $: id => doc.getElementById(id), window };
}

const settled = async () => {
  for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve));
};

/** The hint page after one load of the list; `answers` stays live, so a later `zeige` sees a changed estimate. */
async function hintPage(answers) {
  const page = await ran(["treffer-logik.js", "suchbegriffe-logik.js", "suchbegriffe-start.js"], answers);
  const zeige = async () => {
    await page.window.SuchbegriffeStart.zeige("stelle");
    await settled();
  };
  await zeige();
  return { ...page, zeige };
}

const hintWith = async estimate =>
  (await hintPage({ "/api/suchbegriffe/hinweis": HINT, [ESTIMATE]: estimate })).$("begriff-hinweis-nachsatz");

const LOCK = ["aria-disabled", "tabindex", "aria-describedby"];
const lockOf = link => Object.fromEntries(["href", ...LOCK].map(name => [name, link.getAttribute(name)]));

test("the hint above the hit list names the cost in dollars with an own key", async () => {
  assert.equal((await hintWith(OWN_KEY)).textContent, `${NACHSATZ} Etwa USD\u00a00.03 und 1\u00a0Minute.`);
});

test("the hint above the hit list names francs and the credit left with the mediation", async () => {
  assert.equal((await hintWith(MEDIATION)).textContent,
    `${NACHSATZ} Etwa CHF\u00a00.03 und 1\u00a0Minute. Danach bleiben CHF\u00a04.22 im Guthaben.`);
});

test("the hint over the credit says it may not be enough, a used-up credit links where to ask", async () => {
  assert.equal((await hintWith({ ...MEDIATION, guthaben: 0.01, danach: 0 })).textContent,
    `${NACHSATZ} Etwa CHF\u00a00.03 und 1\u00a0Minute. Im Guthaben sind noch CHF\u00a00.01, das reicht vielleicht nicht.`);
  const used = await hintWith({ ...MEDIATION, guthaben: 0, danach: 0 });
  assert.equal(used.textContent,
    `${NACHSATZ} Etwa CHF\u00a00.03 und 1\u00a0Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern, öffnet neuen Tab.`);
  assert.equal(used.children.find(child => child.tagName === "A").getAttribute("href"), Texte.CODE_REQUEST_URL);
});

test("a used-up credit locks the link of the hint, in the tab order and described by the line; credit opens it", async () => {
  const answers = { "/api/suchbegriffe/hinweis": HINT, [ESTIMATE]: { ...MEDIATION, guthaben: 0, danach: 0 } };
  const page = await hintPage(answers);
  const link = page.$("begriff-hinweis-pruefen");
  assert.deepEqual(lockOf(link), { href: null, "aria-disabled": "true", tabindex: "0",
    "aria-describedby": "begriff-hinweis-nachsatz" });
  answers[ESTIMATE] = MEDIATION;
  await page.zeige();
  assert.deepEqual(lockOf(link), { href: "/suchbegriffe", "aria-disabled": null, tabindex: null, "aria-describedby": null });
});

test("over the credit, with an own key and without an estimate the link of the hint stays open", async () => {
  for (const estimate of [{ ...MEDIATION, guthaben: 0.01, danach: 0 }, OWN_KEY, new Error("Die App antwortet nicht.")]) {
    const page = await hintPage({ "/api/suchbegriffe/hinweis": HINT, [ESTIMATE]: estimate });
    assert.equal(page.$("begriff-hinweis-pruefen").getAttribute("href"), "/suchbegriffe");
    assert.equal(page.$("begriff-hinweis-pruefen").getAttribute("aria-disabled"), null);
  }
});

test("the link of the hint has the id the page locks it by", () => {
  const html = fs.readFileSync(path.join(SEITEN, "treffer.html"), "utf8");
  assert.match(html, /<a class="btn btn--sm" id="begriff-hinweis-pruefen" href="\/suchbegriffe">Suchbegriffe prüfen lassen<\/a>/);
});

test("the hint names why the estimate is missing", async () => {
  assert.equal((await hintWith(new Error("Der Lebenslauf lässt sich nicht lesen."))).textContent,
    `${NACHSATZ} Die Schätzung fehlt: Der Lebenslauf lässt sich nicht lesen.`);
});

async function reviseWith(estimate) {
  const page = await ran(PAGE_SCRIPTS, {
    "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
    "/api/suchbegriffe/vorschlag": { aenderungen: [], treffer: 40, seit: "2026-11-01", runde: 1 }, [ESTIMATE]: estimate,
  });
  return page;
}

test("beside „Neu vorschlagen“ the cost is in dollars with an own key", async () => {
  assert.equal((await reviseWith(OWN_KEY)).$("anders-kosten").textContent, "Etwa USD\u00a00.03 und 1\u00a0Minute.");
});

test("beside „Neu vorschlagen“ the cost is in francs with the credit left, with the mediation", async () => {
  assert.equal((await reviseWith(MEDIATION)).$("anders-kosten").textContent, "Etwa CHF\u00a00.03 und 1\u00a0Minute. Danach bleiben CHF\u00a04.22 im Guthaben.");
  assert.equal((await reviseWith({ ...MEDIATION, guthaben: 0.01, danach: 0 })).$("anders-kosten").textContent,
    "Etwa CHF\u00a00.03 und 1\u00a0Minute. Im Guthaben sind noch CHF\u00a00.01, das reicht vielleicht nicht.");
});

test("beside „Neu vorschlagen“ a used-up credit links where to ask and the button stays as it was", async () => {
  const page = await reviseWith({ ...MEDIATION, guthaben: 0, danach: 0 });
  assert.equal(page.$("anders-kosten").textContent, "Etwa CHF\u00a00.03 und 1\u00a0Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern, öffnet neuen Tab.");
  const button = page.$("neu-vorschlagen");
  assert.equal(button.disabled, undefined);
  assert.equal(button.getAttribute("aria-disabled"), null);
});

// #337: the footer of the proposal card never starts a line with «·»; each «·» ends the part before it (#331 pattern)
const CHANGE = { nummer: 1, bereich: "keywords", bereich_name: "Suchbegriffe", zu_allgemein: false, satz: "«Trainer» aufnehmen",
  entfaellt: [], neu: ["Trainer"], grund: "Steht im Lebenslauf.", beleg: null };
const TERMS = { suchbegriffe: ["Python"], positiv: [], ausschluss: [] };
// #371: how many terms each area may hold, and how many are too many, as term_changes.limits gives them
const ROOM = { zu_viel: { suchbegriffe: 0, positiv: 0, ausschluss: 0 }, erlaubt: { suchbegriffe: 15, positiv: 30, ausschluss: 30 } };
const PROPOSAL = { vorschlag: "v1", aenderungen: [CHANGE], zusammenfassung: "Eine Änderung.", treffer: 40,
  seit: "2026-11-01", jetzt: TERMS, bisherige: TERMS, endstand: { ...TERMS, suchbegriffe: ["Python", "Trainer"] }, entfaellt: [],
  grenzen: { teile: ["Danach: 2 von 15 Suchbegriffen", "bis 4 Suchen pro Portal"], gesperrt: null, ...ROOM }, modell: "claude-sonnet-5-5", kosten_usd: 0.03, waehrung: "CHF",
  datum: "2026-11-16", runde: 1 };
const PAGE_SCRIPTS = ["treffer-logik.js", "suchbegriffe-logik.js", "suchbegriffe-schalter.js", "suchbegriffe.js"];

const proposalPage = async proposal => ran(PAGE_SCRIPTS, {
  "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
  "/api/suchbegriffe/vorschlag": proposal, [ESTIMATE]: MEDIATION,
});
const footerOf = async proposal => (await proposalPage(proposal)).$("fuss");

const isEl = n => n instanceof FakeElement;
const shownText = n => (isEl(n) ? (n.className === "visually-hidden" ? "" : n.children.map(shownText).join("")) : n.data);
const heardText = n => (isEl(n) ? (n.getAttribute("aria-hidden") === "true" ? "" : n.children.map(heardText).join("")) : n.data);

for (const [name, proposal, words] of [
  ["one proposal", PROPOSAL, ["Claude", "CHF\u00a00.03", "16.11.2026"]],
  ["a second proposal", { ...PROPOSAL, runde: 2, kosten_bisher: 0.06 }, ["Claude", "CHF\u00a00.03", "16.11.2026", "bisher CHF\u00a00.06"]],
]) {
  test(`after ${name} each «·» of the footer is glued to the part before it, a line breaks only after «· »`, async () => {
    const footer = await footerOf(proposal);
    const parts = footer.children.filter(isEl);
    assert.ok(parts.length === words.length && parts.every(n => n.className === "whole-part"), "the footer holds only whole parts");
    assert.deepEqual(footer.children.filter(n => !isEl(n)).map(n => n.data), words.slice(1).map(() => " "),
      "a plain space between two parts is the only place a line may break");
    assert.deepEqual(parts.map(shownText), words.map((word, i) => (i < words.length - 1 ? `${word}\u00a0·` : word)),
      "the «·» sits inside the part before it, after a no-break space");
    for (const part of parts.slice(0, -1)) {
      const [dot, comma] = part.children.slice(-2);
      assert.equal(dot.getAttribute("aria-hidden"), "true", "the «·» is hidden from screen readers");
      assert.equal(comma.className, "visually-hidden");
    }
    assert.equal(heardText(footer), words.join(", "), "screen readers hear the parts in order, with commas");
  });
}

test("a whole part breaks to the next line only as a whole, in the shared style of every page", () => {
  const css = fs.readFileSync(path.join(SEITEN, "stil.css"), "utf8");
  const rule = css.split("\n").find(line => line.startsWith(".whole-part {"));
  assert.ok(rule, ".whole-part has its rule in stil.css");
  assert.match(rule, /display: inline-block; max-width: 100%;/);
  assert.match(fs.readFileSync(path.join(SEITEN, "suchbegriffe.html"), "utf8"), /<link rel="stylesheet" href="\/stil\.css">/);
});

test("the meta of the footer stands on a line of its own, after the sentence and a space for screen readers", () => {
  const html = fs.readFileSync(path.join(SEITEN, "suchbegriffe.html"), "utf8");
  assert.match(html, /<span id="fuss-satz"><\/span> <span id="fuss" class="ai-result__meta"><\/span>/);
  const css = fs.readFileSync(path.join(SEITEN, "stil.css"), "utf8");
  const rule = css.split("\n").find(line => line.startsWith(".ai-result__meta {"));
  assert.ok(rule, ".ai-result__meta has its rule in stil.css");
  assert.match(rule, /display: block;/);
});

// #340: every «·» line of the card is drawn by the shared helper, so none starts a line with «·»
function assertDotLine(line, words) {
  const parts = line.children.filter(isEl);
  assert.ok(parts.length === words.length && parts.every(n => n.className === "whole-part"), "the line holds only whole parts");
  assert.deepEqual(line.children.filter(n => !isEl(n)).map(n => n.data), words.slice(1).map(() => " "),
    "a plain space between two parts is the only place a line may break");
  assert.deepEqual(parts.map(shownText), words.map((word, i) => (i < words.length - 1 ? `${word}\u00a0·` : word)),
    "the «·» sits inside the part before it, after a no-break space");
  assert.equal(heardText(line), words.join(", "), "screen readers hear the parts in order, with commas");
}

test("the heading is a «·» line of whole parts, and its accessible name has a comma instead of «·»", async () => {
  const page = await proposalPage(PROPOSAL);
  assertDotLine(page.$("vorschlag-kopf"), ["Vorschlag der KI", "1 Änderung"]);
  assert.equal(heardText(page.$("vorschlag-kopf")), "Vorschlag der KI, 1 Änderung");
  const two = await proposalPage({ ...PROPOSAL, aenderungen: [CHANGE, { ...CHANGE, nummer: 2 }] });
  assertDotLine(two.$("vorschlag-kopf"), ["Vorschlag der KI", "2 Änderungen"]);
});

test("the round line of a second proposal is a «·» line of whole parts; the first has none", async () => {
  const second = await proposalPage({ ...PROPOSAL, runde: 2, kosten_bisher: 0.06 });
  assert.equal(second.$("runde").hidden, false);
  assertDotLine(second.$("runde"), ["Vorschlag 2", "nach Ihrem Hinweis"]);
  const first = await proposalPage(PROPOSAL);
  assert.equal(first.$("runde").hidden, true);
  assert.deepEqual(first.$("runde").children, []);
});

test("the limits line is a «·» line of whole parts, also after a change is unticked", async () => {
  const page = await ran(PAGE_SCRIPTS, {
    "/api/suchbegriffe/hinweis": HINT, "/api/ki/status": { einwilligung: null },
    "/api/suchbegriffe/vorschlag": PROPOSAL, [ESTIMATE]: MEDIATION,
    "/api/suchbegriffe/endstand": { endstand: TERMS, entfaellt: [],
      grenzen: { teile: ["Danach: 1 von 15 Suchbegriffen", "bis 2 Suchen pro Portal"],
        gesperrt: "Mit dieser Auswahl bleibt alles wie bisher.", ...ROOM } },
  });
  assertDotLine(page.$("grenzen"), ["Danach: 2 von 15 Suchbegriffen", "bis 4 Suchen pro Portal"]);
  const box = page.$("aenderungen").children[0].children.find(n => isEl(n) && n.tagName === "LABEL").children[0];
  box.checked = false;
  for (const handler of box.listeners.change) handler();
  await settled();
  assertDotLine(page.$("grenzen"), ["Danach: 1 von 15 Suchbegriffen", "bis 2 Suchen pro Portal"]);
});
