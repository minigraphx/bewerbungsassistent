// Einstellungen in sections (#265, A10): sections on the left, access to the AI as a choice, the budget of the month
// (G46), Erweitert with the pre-releases (G41, G47) and Über die App with the logo (G4).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const logic = require("../seiten/einstellungen-logik.js");
const access = require("../seiten/ki-zugang.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const panel = (html, id) => {
  const start = html.indexOf(`id="bereich-${id}"`);
  assert.ok(start > 0, `panel ${id}`);
  const next = html.indexOf('class="settings__panel"', start);
  return html.slice(start, next > 0 ? next : html.indexOf("</main>"));
};

const MEDIATION = { monat: "2026-11", eingerichtet: true, vermittlung: true, eigener_schluessel: false,
                    budget_usd: 10, verbraucht_usd: 3.2, kosten_usd: 3.2 };
const OWN_KEY = { monat: "2026-11", eingerichtet: true, vermittlung: false, eigener_schluessel: true, kosten_usd: 1.5 };
const NOTHING = { monat: "2026-11", eingerichtet: false, einladung: true, kosten_usd: 0 };
const COSTS = {
  monat_usd: 3.2, gesamt_usd: 7.45, aufrufe: 120,
  aufgaben: {
    rate_package: { aufrufe: 40, usd: 1.6 }, rate: { aufrufe: 31, usd: 0.5 },
    draft: { aufrufe: 6, usd: 0.9 }, chat: { aufrufe: 14, usd: 0.2 }, made_up: { aufrufe: 1, usd: 0 },
  },
};

test("the sections stand on the left in the order of the design, Über die App last", () => {
  assert.deepEqual(logic.SECTIONS.map(section => section.label), [
    "KI und Budget", "Suche und Portale", "Browser-Erweiterung", "Stelle, Lehrstelle, RAV",
    "Daten und Sicherung", "Erweitert", "Über die App"]);
  const html = read("einstellungen.html");
  const nav = html.match(/<nav class="settings__nav"[\s\S]*?<\/nav>/)[0];
  const links = [...nav.matchAll(/<a href="#([a-z]+)"[^>]*>([^<]+)<\/a>/g)].map(([, id, label]) => [id, label]);
  assert.deepEqual(links, logic.SECTIONS.map(section => [section.id, section.label]));
  for (const { id } of logic.SECTIONS) assert.match(html, new RegExp(`<section class="settings__panel" id="bereich-${id}"`));
  assert.match(nav, /<a href="#ueber" id="ueber-link" hidden>/, "Über die App only where the packaged app fills it");
});

test("an anchor opens the section that holds it, old anchors included", () => {
  assert.equal(logic.sectionOf(""), "ki");
  assert.equal(logic.sectionOf("#erweitert"), "erweitert");
  assert.equal(logic.sectionOf("#schluessel-teil"), "ki");
  assert.equal(logic.sectionOf("#claude-abo"), "ki");
  assert.equal(logic.sectionOf("#kosten"), "ki");
  assert.equal(logic.sectionOf("#einwilligung"), "ki");
  assert.equal(logic.sectionOf("#vorabversionen"), "erweitert");
  assert.equal(logic.sectionOf("#daten"), "daten");
  assert.equal(logic.sectionOf("#ueber-die-app"), "ueber");
  assert.equal(logic.sectionOf("#gibt-es-nicht"), "ki");
});

test("an anchor of one way to the AI opens that way", () => {
  assert.equal(logic.wayOf("#schluessel-teil"), "schluessel");
  assert.equal(logic.wayOf("#claude-abo"), "abo");
  assert.equal(logic.wayOf("#einladung"), "einladung");
  assert.equal(logic.wayOf("#kosten"), null);
});

test("the chosen way follows what the app actually uses", () => {
  assert.equal(logic.currentWay(OWN_KEY, { zugang: true }), "schluessel");  // the key wins for the buttons of the app
  assert.equal(logic.currentWay(MEDIATION, null), "einladung");
  assert.equal(logic.currentWay(NOTHING, { zugang: true }), "abo");
  assert.equal(logic.currentWay(NOTHING, { zugang: false }), null);
  assert.equal(logic.currentWay(null, null), null);
});

test("the invitation says what applies: running, enter a code, behind the own key, or not built in", () => {
  assert.equal(logic.invitationState(MEDIATION), "aktiv");
  assert.equal(logic.invitationState(NOTHING), "eingeben");
  assert.equal(logic.invitationState(OWN_KEY), "schluessel");
  assert.equal(logic.invitationState({ ...NOTHING, einladung: false }), "keine");
  assert.equal(logic.invitationState(null), "keine");
});

test("the three ways read as in the design, without the subscription where the app cannot offer it", () => {
  const all = access.options({ abo: true });
  assert.deepEqual(all.map(option => [option.value, option.title]), [
    ["einladung", "Einladungscode"], ["abo", "Eigenes Claude-Abo"], ["schluessel", "Eigener Schlüssel von Anthropic"]]);
  assert.match(all[1].link.href, /docs\/eigenes-abo\.md$/);
  assert.match(all[2].link.href, /docs\/installation\.md#eigener-api-schlüssel-freiwillig$/);
  assert.equal(all[2].link.text, "Woher der Schlüssel kommt und was er kostet");
  assert.deepEqual(access.options({ abo: false }).map(option => option.value), ["einladung", "schluessel"]);
  for (const option of all) assert.doesNotMatch(option.text, /\b(Sie|Ihr|Ihre|du|dein)\b/, "no address in a shared text");
});

test("the way in use says so in its line", () => {
  assert.match(access.line(access.options({ abo: true })[0], "einladung"), /^Eingerichtet\. Kostenlos im Pilot/);
  assert.doesNotMatch(access.line(access.options({ abo: true })[0], "schluessel"), /Eingerichtet/);
});

test("the budget of the mediation: used of the budget, the next one and what it went to", () => {
  const view = logic.budgetView(MEDIATION, COSTS);
  assert.equal(view.title, "Budget im November");
  assert.equal(view.headline, "USD 3.20 von 10.00 gebraucht");
  assert.equal(view.renewal, "Neues Budget am 01.12.2026");
  assert.equal(view.percent, 32);
  assert.deepEqual(view.rows, [
    { label: "Stellen einschätzen", count: 71, usd: "USD 2.10" },
    { label: "Anschreiben entwerfen", count: 6, usd: "USD 0.90" },
    { label: "Fragen an die KI", count: 14, usd: "USD 0.20" },
    { label: "Weitere", count: 1, usd: "USD 0.00" },
  ]);
  assert.equal(view.note, "Ist das Budget aufgebraucht, läuft die App weiter, nur ohne KI. Protokolliert werden Kosten, keine Inhalte.");
  assert.equal(view.total, "Seit Beginn USD 7.45 in 120 Aufrufen");
});

test("December rolls over into the next year, and a spent budget fills the bar", () => {
  const view = logic.budgetView({ ...MEDIATION, monat: "2026-12", verbraucht_usd: 12 }, COSTS);
  assert.equal(view.renewal, "Neues Budget am 01.01.2027");
  assert.equal(view.percent, 100);
});

test("with the own key there is no budget, only the costs of the month", () => {
  const view = logic.budgetView(OWN_KEY, { ...COSTS, monat_usd: 1.5 });
  assert.equal(view.title, "Kosten im November");
  assert.equal(view.headline, "USD 1.50 mit eigenem Schlüssel");
  assert.equal(view.renewal, null);
  assert.equal(view.percent, null);
  assert.match(view.note, /^Massgebend ist die Abrechnung von Anthropic\./);
});

test("without an answer of the AI the local costs still show", () => {
  const view = logic.budgetView(null, { monat_usd: 0, gesamt_usd: 0, aufrufe: 0, aufgaben: {} });
  assert.equal(view.title, "Kosten in diesem Monat");
  assert.equal(view.headline, "USD 0.00");
  assert.deepEqual(view.rows, []);
  assert.equal(view.total, "Seit Beginn USD 0.00 in 0 Aufrufen");
});

test("the panels hold what the criterion names", () => {
  const html = read("einstellungen.html");
  const ki = panel(html, "ki");
  assert.match(ki, /id="zugang-wahl"/);
  assert.match(ki, /id="zugang-einladung"/);
  assert.match(ki, /<section class="card" id="claude-abo"/);
  assert.match(ki, /id="schluessel-teil"/);
  assert.match(ki, /id="einwilligung"/);
  assert.match(ki, /<section class="card" id="kosten"/);
  assert.match(ki, /id="budget-balken"/);
  const advanced = panel(html, "erweitert");
  assert.match(advanced, /id="vorabversionen"/);
  assert.match(advanced, /href="\/inhalte"/);
  assert.match(panel(html, "ueber"), /<section class="card" id="ueber-die-app" aria-labelledby="ueber-titel" hidden>/);
  assert.match(panel(html, "daten"), /<section class="card" id="daten" aria-labelledby="daten-titel">/);
  assert.match(panel(html, "suche"), /href="\/suche-einstellen"/);
  assert.match(panel(html, "erweiterung"), /href="\/einrichtung#erweiterung"/);
  assert.match(panel(html, "wahl"), /href="\/einrichtung"/);
  assert.match(html, /<title>Einstellungen<\/title>/);
  assert.match(html, /<h1>Einstellungen<\/h1>/);
  assert.doesNotMatch(html, /Erweiterte Einstellungen/);
});

test("the page loads its parts, the access choice before the page script", () => {
  const html = read("einstellungen.html");
  assert.match(html, /<link rel="stylesheet" href="\/einstellungen\.css">/);
  const order = ["/einstellungen-logik.js", "/ki-zugang.js", "/einstellungen.js"].map(src => html.indexOf(`src="${src}"`));
  assert.ok(order.every(index => index > 0), "scripts present");
  assert.deepEqual([...order].sort((a, b) => a - b), order);
});

test("the page styles use the tokens of the design system only", () => {
  const css = read("einstellungen.css").replace(/\/\*[\s\S]*?\*\//g, "");
  assert.ok(css.length > 200);
  assert.doesNotMatch(css, /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/, "colours only as tokens");
  assert.match(css, /var\(--accent-subtle\)/);
  assert.match(css, /@media \(max-width: 760px\)/);
});

test("the subscription section shows only as the chosen way", () => {
  assert.doesNotMatch(read("claude-abo.js"), /\$\("claude-abo"\)\.hidden = false/);
});
