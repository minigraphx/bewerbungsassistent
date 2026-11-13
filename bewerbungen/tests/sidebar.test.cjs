// Sidebar instead of the header with „Mehr“ (#259, G54): seven destinations, AI budget and extension at the bottom,
// badges only where something waits; below 900 px a header with the four main destinations and „Menü“.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const sidebar = require("../seiten/sidebar-logic.js");

const PAGES = path.join(__dirname, "..", "seiten");
const ONBOARDING = path.join(__dirname, "..", "..", "onboarding", "src");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const htmlPages = () => fs.readdirSync(PAGES).filter(name => name.endsWith(".html"));
const navOf = html => html.match(/<nav class="app-nav"[\s\S]*?<\/nav>/)[0];
const DESTINATIONS = [
  ["heute", "/", "Heute"],
  ["stellen", "/treffer", "Stellen"],
  ["bewerbungen", "/bewerbungen", "Bewerbungen"],
  ["angaben", "/angaben", "Meine Angaben"],
  ["dateien", "/dateien", "Lebenslauf und Dateien"],
  ["fragen", "/fragen", "Fragen an die KI"],
  ["einstellungen", "/einstellungen", "Einstellungen"],
];

test("every page shares the same sidebar with the seven destinations in order and no „Mehr“", () => {
  const reference = navOf(read("uebersicht.html"));
  const found = [...reference.matchAll(/<a class="app-nav__link" href="([^"]+)" data-target="([^"]+)">(?:<span[^>]*>)?([^<]+)</g)]
    .map(([, href, id, label]) => [id, href, label]);
  assert.deepEqual(found, DESTINATIONS);
  assert.doesNotMatch(reference, /Mehr|<details|menu__group/);
  assert.ok(reference.indexOf(">Meine Unterlagen<") < reference.indexOf('data-target="angaben"'), "head before Meine Angaben");
  assert.ok(reference.indexOf(">Hilfe<") < reference.indexOf('data-target="fragen"'), "head before Fragen an die KI");
  const pages = htmlPages();
  assert.ok(pages.length >= 13);
  for (const name of pages) assert.equal(navOf(read(name)), reference, name);
});

test("the narrow header keeps four main destinations and moves the rest behind „Menü“", () => {
  const nav = navOf(read("uebersicht.html"));
  const [main, more] = nav.split('<div class="app-nav__more" id="nav-more">');
  for (const id of ["heute", "stellen", "bewerbungen", "angaben"]) assert.match(main, new RegExp(`data-target="${id}"`));
  for (const id of ["dateien", "fragen", "einstellungen"]) assert.match(more, new RegExp(`data-target="${id}"`));
  assert.match(main, /<button type="button" class="app-nav__menu" id="nav-menu" aria-expanded="false" aria-controls="nav-more">/);
  assert.match(main, />Menü<\/button>/);
  assert.match(more, /id="nav-budget"[^>]*hidden/);
  assert.match(more, /id="nav-extension"[^>]*hidden/);
});

test("the questions link stands alone in its list item, so the server can take it out whole", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8");
  const link = app.match(/QUESTIONS_LINK = '([^']+)'/)[1];
  assert.match(link, /^<li><a [^>]*href="\/fragen"[^>]*>Fragen an die KI<\/a><\/li>$/);
  assert.ok(navOf(read("uebersicht.html")).includes(link));
});

test("every page loads the sidebar after app.js, with the overview logic it counts with", () => {
  for (const name of htmlPages()) {
    const scripts = [...read(name).matchAll(/<script src="([^"]+)"/g)].map(m => m[1]);
    const at = file => scripts.indexOf(file);
    assert.ok(at("/sidebar.js") > at("/app.js") && at("/app.js") >= 0, name);
    assert.ok(at("/uebersicht-logik.js") >= 0 && at("/uebersicht-logik.js") < at("/sidebar.js"), name);
    assert.ok(at("/sidebar-logic.js") >= 0 && at("/sidebar-logic.js") < at("/sidebar.js"), name);
    assert.equal(scripts.length, new Set(scripts).size, `${name} loads a script twice`);
  }
});

test("the page marks the destination it belongs to", () => {
  const cases = {
    "/": "heute", "/bewerbung": "bewerbungen", "/treffer": "stellen", "/suchbegriffe": "stellen", "/firmen": "stellen", "/suche-einstellen": "stellen",
    "/angaben": "angaben", "/inhalte": "angaben", "/dateien": "dateien", "/foto": "dateien", "/entwuerfe": "dateien",
    "/fragen": "fragen", "/einstellungen": "einstellungen", "/einrichtung": "einstellungen", "/unbekannt": null,
  };
  for (const [page, target] of Object.entries(cases)) assert.equal(sidebar.activeTarget(page), target, page);
});

test("a badge stands only where something waits", () => {
  assert.deepEqual(sidebar.badges({ open: 4, newHits: 8 }), {
    heute: { long: "4 offen", short: "4" }, stellen: { long: "8 neu", short: "8 neu" },
  });
  assert.deepEqual(sidebar.badges({ open: 0, newHits: 0 }), { heute: null, stellen: null });
  assert.deepEqual(sidebar.badges({}), { heute: null, stellen: null });
});

test("the budget of the mediation shows what is used, with a decimal point", () => {
  const status = { monat: "2026-11", eingerichtet: true, vermittlung: true, budget_usd: 10, verbraucht_usd: 3.2 };
  assert.deepEqual(sidebar.budgetView(status), {
    title: "KI-Budget im November", text: "USD 3.20 von 10.00 gebraucht", short: "KI-Budget: USD 6.80 frei",
    percent: 32, label: "32 Prozent des Budgets gebraucht",
  });
  assert.deepEqual(sidebar.budgetView({ ...status, verbraucht_usd: 0 }), {
    title: "KI-Budget im November", text: "USD 10.00 frei", short: "KI-Budget: USD 10.00 frei",
    percent: 0, label: "Noch nichts gebraucht",
  });
  const over = sidebar.budgetView({ ...status, verbraucht_usd: 12 });
  assert.equal(over.percent, 100);
  assert.equal(over.short, "KI-Budget: USD 0.00 frei");
});

test("with an own key the sidebar shows the costs of the month, and nothing without AI", () => {
  assert.deepEqual(sidebar.budgetView({ monat: "2026-03", eingerichtet: true, vermittlung: false, eigener_schluessel: true, kosten_usd: 1.5 }), {
    title: "KI-Kosten im März", text: "USD 1.50 mit eigenem Schlüssel", short: "KI-Kosten: USD 1.50", percent: null, label: "",
  });
  assert.equal(sidebar.budgetView({ monat: "2026-11", eingerichtet: false }), null);
  assert.equal(sidebar.budgetView({ monat: "2026-11", eingerichtet: true, vermittlung: true, hinweis: "nicht erreichbar" }), null);
  assert.equal(sidebar.budgetView(null), null);
});

test("the budget is asked once in a while, not on every page", () => {
  const now = 1_000_000;
  assert.equal(sidebar.isFresh({ at: now - 1000, status: {} }, now), true);
  assert.equal(sidebar.isFresh({ at: now - sidebar.BUDGET_MAX_AGE_MS - 1, status: {} }, now), false);
  assert.equal(sidebar.isFresh({ at: now + 60000, status: {} }, now), false);  // a clock that went back
  assert.equal(sidebar.isFresh(null, now), false);
  assert.equal(sidebar.isFresh({ at: "x" }, now), false);
});

test("the sidebar is 248 px wide from 900 px and uses the tokens of the design system", () => {
  const css = read("stil.css");
  const block = css.slice(css.indexOf("/* ---------- Sidebar"), css.indexOf("/* ---------- end of sidebar"));
  assert.ok(block.length > 200, "sidebar block in stil.css");
  assert.match(block, /@media \(min-width: 900px\)/);
  assert.match(block, /--width-sidebar/);
  assert.match(css, /--width-sidebar: 248px;/);
  const rules = block.replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(rules, /#[0-9a-fA-F]{3,6}\b|rgba?\(/, "colours only as tokens");
  const own = fs.readFileSync(path.join(ONBOARDING, "appnav.css"), "utf8");
  assert.match(own, /@media \(min-width: 900px\)/);
  assert.match(own, /\.app-nav__more/);
  assert.doesNotMatch(own, /menu__group|details/);
});

test("the logo, the version and „Beenden“ sit under Einstellungen, Über die App", () => {
  const settings = read("einstellungen.html");
  assert.match(settings, /<section class="card" id="ueber-die-app" aria-labelledby="ueber-titel" hidden>/);
  assert.match(settings, /<h2 id="ueber-titel">Über die App<\/h2>/);
  assert.match(settings, /<section class="card" id="daten" aria-labelledby="daten-titel">/);
  assert.match(settings, /href="\/einrichtung"/);
  assert.match(settings, /href="\/inhalte"/);
  const script = read("app.js");
  assert.doesNotMatch(script, /menu-app|app-nav__more|details/);
  assert.match(script, /getElementById\("ueber-die-app"\)/);
  assert.match(script, /getElementById\("daten-knoepfe"\)/);
});

test("pages that left the menu stay reachable from their neighbours", () => {
  assert.match(read("dateien.html"), /href="\/foto"/);
  assert.match(read("dateien.html"), /href="\/entwuerfe"/);
  assert.match(read("treffer.html"), /href="\/firmen"/);
});
