// The shared frame of every page in French and English (#416, G10, docs/design/sprachen.md): the sidebar, the
// messages, the card „Über die App“ and the choice of the way to the AI say their texts through Texte.t, with the
// catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages. German stays as it was.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const sidebar = require("../seiten/sidebar-logic.js");
const meldungen = require("../seiten/meldungen.js");
const kiZugang = require("../seiten/ki-zugang.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const CATALOG = path.join(__dirname, "..", "sprachen");
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);

/** What translation_catalog.for_page hands a page of one language: plain texts and text sets. */
function catalogFor(language) {
  const files = fs.existsSync(CATALOG) ? fs.readdirSync(CATALOG) : [];
  const entries = Object.assign({}, ...files.filter(name => name.endsWith(".json"))
    .map(name => JSON.parse(fs.readFileSync(path.join(CATALOG, name), "utf8"))));
  const texts = {};
  const sets = {};
  for (const [key, entry] of Object.entries(entries)) {
    if (key.startsWith(SET_PREFIX)) sets[key.slice(SET_PREFIX.length)] = entry[language];
    else texts[key] = entry[language];
  }
  return { sprache: language, texte: texts, saetze: sets };
}

/** Runs `check` with the app in `language`, then gives the page back its own language. */
function inLanguage(language, check) {
  texte.setzeSprache(language, catalogFor(language));
  try {
    return check();
  } finally {
    texte.setzeSprache();
  }
}

const textOf = node => (node && typeof node === "object" ? node.children.map(textOf).join("") : String(node ?? ""));
const paragraphs = node => (node && typeof node === "object"
  ? [...(node.tag === "p" ? [node] : []), ...node.children.flatMap(paragraphs)] : []);
const settle = async () => { for (let i = 0; i < 8; i += 1) await new Promise(resolve => setImmediate(resolve)); };

function element(tag) {
  const node = {
    tag, attrs: {}, children: [], hidden: false, className: "",
    get textContent() { return textOf(node); },
    set textContent(value) { node.children = [String(value)]; },
    setAttribute(name, value) { node.attrs[name] = value; },
    removeAttribute(name) { delete node.attrs[name]; },
    addEventListener() {},
    append(...items) { node.children.push(...items); },
    replaceChildren(...items) { node.children = items; },
    prepend(...items) { node.children.unshift(...items); },
  };
  return node;
}

/** The card „Über die App“ that app.js draws on the settings page of the packaged app. */
async function aboutCard(version) {
  const card = element("section");
  const answers = { "/api/app/version": version, "/api/app/einrichtung": { eingerichtet: true } };
  const fetch = async url => {
    const found = answers[String(url).split("?")[0]];
    return { ok: Boolean(found), status: found ? 200 : 404, statusText: "", headers: { get: () => "application/json" },
             json: async () => found || { fehler: "Nicht gefunden" } };
  };
  const document = {
    querySelector: selector => (selector.startsWith("meta") ? { content: "token" } : null), querySelectorAll: () => [],
    getElementById: id => (id === "ueber-die-app" ? card : null),
    addEventListener() {}, hidden: false, documentElement: { dataset: {} },
    head: element("head"), body: element("body"), createElement: tag => element(tag), createTextNode: text => text,
  };
  const Node = { [Symbol.hasInstance]: value => typeof value === "object" && value !== null };
  const location = { pathname: "/einstellungen", search: "", hash: "", origin: "http://127.0.0.1:1", replace() {}, reload() {} };
  vm.runInNewContext(fs.readFileSync(path.join(SEITEN, "app.js"), "utf8"), {
    window: { addEventListener() {}, Texte: texte }, document, location, history: { state: null, length: 1, replaceState() {} },
    fetch, URLSearchParams, Node, setInterval() {}, setTimeout, Promise, crypto: { randomUUID: () => "x" },
  });
  await settle();
  return card;
}

/** window.App of app.js on a page where every request answers `answer`. */
function appAnswering(answer) {
  const document = {
    querySelector: selector => (selector.startsWith("meta") ? { content: "token" } : null), querySelectorAll: () => [],
    getElementById: () => null, addEventListener() {},
    hidden: false, documentElement: { dataset: {} }, head: element("head"), body: element("body"),
    createElement: tag => element(tag), createTextNode: text => text,
  };
  const window = { addEventListener() {}, Texte: texte };
  const location = { pathname: "/inhalte", search: "", hash: "", origin: "http://127.0.0.1:1", replace() {}, reload() {} };
  vm.runInNewContext(fs.readFileSync(path.join(SEITEN, "app.js"), "utf8"), {
    window, document, location, history: { state: null, length: 1, replaceState() {} }, fetch: async () => answer,
    URLSearchParams, Node: { [Symbol.hasInstance]: () => false }, setInterval() {}, setTimeout, Promise,
    crypto: { randomUUID: () => "x" },
  });
  return window.App;
}

test("a preview that is no PDF is refused in the app language", async () => {
  const html = { ok: true, status: 200, headers: { get: () => "text/html" }, json: async () => ({}) };

  await assert.rejects(appAnswering(html).pdfAdresse("/api/inhalt/pdf"), { message: "Antwort ist kein PDF" });
  texte.setzeSprache("fr", catalogFor("fr"));
  try {
    await assert.rejects(appAnswering(html).pdfAdresse("/api/inhalt/pdf"), { message: "La réponse n'est pas un PDF" });
  } finally {
    texte.setzeSprache();
  }
});

test("the badges of the sidebar speak French and English", () => {
  assert.deepEqual(inLanguage("fr", () => sidebar.badges({ open: 4, newHits: 1 })), {
    heute: { long: "4 à faire", short: "4" }, stellen: { long: "1 à voir", short: "1 à voir" } });
  assert.deepEqual(inLanguage("en", () => sidebar.badges({ open: 4, newHits: 1 })), {
    heute: { long: "4 to do", short: "4" }, stellen: { long: "1 new", short: "1 new" } });
});

test("the AI budget at the bottom of the sidebar names month and renewal in French", () => {
  const status = { eingerichtet: true, vermittlung: true, guthaben_chf: 5, verbraucht_chf: 4.5, monat: "2026-11",
                   erneuert_am: "2026-12-01" };

  const view = inLanguage("fr", () => sidebar.budgetView(status));

  assert.equal(view.title, "Budget IA novembre");
  assert.equal(view.text, `CHF${NBSP}4.50 sur CHF${NBSP}5.00 utilisés`);
  assert.equal(view.warning, `Presque épuisé. Nouveau budget le 1er${NBSP}décembre.`);
  assert.equal(view.label, "90 pour cent du budget IA utilisés en novembre");
  assert.equal(inLanguage("fr", () => sidebar.budgetView({ ...status, erneuert_am: "2026-12-02" })).warning,
               `Presque épuisé. Nouveau budget le 2${NBSP}décembre.`);
});

test("the own key costs name the month in English", () => {
  const view = inLanguage("en", () => sidebar.budgetView({ monat: "2026-03", eingerichtet: true, vermittlung: false,
                                                            eigener_schluessel: true, kosten_usd: 1.5 }));

  assert.equal(view.title, "AI costs in March");
  assert.equal(view.detail, "No credit on the app's AI service");
});

/** App.el as the pages have it: tag, attributes and children. */
function el(tag, attrs = {}, ...children) {
  const node = element(tag);
  Object.assign(node.attrs, attrs);
  node.append(...children);
  return node;
}
const linkWord = parts => parts.find(part => typeof part === "object")?.children[0];

test("the link to a new code sits on the request word of the app language", () => {
  const usedUp = { eingerichtet: true, vermittlung: true, guthaben_chf: 5, verbraucht_chf: 5 };
  const linked = () => {
    const warning = sidebar.budgetView(usedUp).warning;
    return { warning, word: linkWord(texte.withCodeRequestLink(warning, el)) };
  };

  assert.deepEqual(inLanguage("fr", linked), { warning: `Crédit épuisé${NBSP}: demander un nouveau code`, word: "demander" });
  assert.deepEqual(inLanguage("en", linked), { warning: "Credit used up: request a new code", word: "request" });
  assert.deepEqual(linked(), { warning: "Guthaben aufgebraucht: neuen Code anfordern", word: "anfordern" });
});

test("the budget in the window „KI einrichten“ goes through the catalog", () => {
  const status = { guthaben_chf: 5, verbraucht_chf: 1.2, monat: "2026-11", erneuert_am: "2026-12-01" };
  const usedUp = { ...status, verbraucht_chf: 5 };

  assert.equal(inLanguage("fr", () => texte.budgetPart(status)),
               ` Budget IA en novembre${NBSP}: CHF${NBSP}1.20 sur CHF${NBSP}5.00 utilisés.`);
  assert.equal(inLanguage("fr", () => texte.budgetPart(usedUp)),
               ` Budget IA en novembre${NBSP}: CHF${NBSP}5.00 sur CHF${NBSP}5.00 utilisés. Il est épuisé${NBSP}; `
               + `l'IA fonctionne à nouveau dès le 1er${NBSP}décembre.`);
  assert.equal(inLanguage("en", () => texte.budgetPart(usedUp)),
               ` AI budget in November: CHF${NBSP}5.00 of CHF${NBSP}5.00 used. It is used up; the AI works again from `
               + `1${NBSP}December.`);
  assert.equal(inLanguage("fr", () => texte.budgetPart({ guthaben_chf: 5, verbraucht_chf: 5 })),
               ` Crédit${NBSP}: CHF${NBSP}5.00 sur CHF${NBSP}5.00 utilisés. Le crédit est épuisé${NBSP}: demander un `
               + "nouveau code et l'utiliser sous Paramètres, IA, budget et langue.");
  assert.equal(texte.budgetPart(usedUp), ` KI-Budget im November: CHF${NBSP}5.00 von CHF${NBSP}5.00 verbraucht. `
               + `Es ist aufgebraucht; die KI geht wieder ab 1.${NBSP}Dezember.`);
});

test("the close button of a message is named in English", () => {
  assert.equal(inLanguage("en", () => meldungen.schliessenText()), "Close message");
  assert.equal(meldungen.schliessenText(), "Meldung schliessen");
});

test("the ways to the AI are worded in French", () => {
  const lines = inLanguage("fr", () => kiZugang.options({ abo: true }).map(option => kiZugang.line(option, "einladung")));

  assert.equal(lines[0], `Configuré. Gratuit pendant le pilote, avec un budget de CHF 5 par mois.`);
  assert.equal(lines[1], "Le travail se fait dans Claude, l'app fournit les outils.");
});

test("the card „Über die App“ speaks French", async () => {
  texte.setzeSprache("fr", catalogFor("fr"));
  try {
    const card = await aboutCard({ version: "9.2.0", update: null, store: true });

    assert.deepEqual(paragraphs(card).map(textOf), ["Bewerbungsbegleiter", "Version 9.2.0", "par Andreas Schmidt",
                                                     "Les mises à jour arrivent par le Microsoft Store."]);
  } finally {
    texte.setzeSprache();
  }
});

test("in German the card and the badges read as before", async () => {
  const card = await aboutCard({ version: "9.2.0", update: null, store: true });

  assert.deepEqual(paragraphs(card).map(textOf), ["Bewerbungsbegleiter", "Version 9.2.0", "von Andreas Schmidt",
                                                   "Updates kommen über den Microsoft Store."]);
  assert.deepEqual(sidebar.badges({ open: 4, newHits: 1 }), {
    heute: { long: "4 offen", short: "4" }, stellen: { long: "1 neu", short: "1 neu" } });
});
