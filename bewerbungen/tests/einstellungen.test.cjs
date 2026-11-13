// Einstellungen in sections (#265, A10): sections on the left, access to the AI as a choice, the budget of the month
// (G46) with a row per task, Erweitert with the pre-releases (G41, G47) and Über die App with the logo (G4).
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
// A card inside a panel, up to its end; cards hold no sections of their own.
const card = (html, id) => {
  const start = html.indexOf(`<section class="card" id="${id}"`);
  assert.ok(start >= 0, `card ${id}`);
  return html.slice(start, html.indexOf("</section>", start));
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

test("KI und Budget: the access to the AI is a choice of invitation code, own Claude subscription and own key", () => {
  const ki = panel(read("einstellungen.html"), "ki");
  const choice = card(ki, "zugang");
  assert.match(choice, /<h2 id="zugang-titel">Zugang zur KI<\/h2>/);
  assert.match(choice, /<fieldset class="access-choice" id="zugang-wahl">/);
  assert.match(read("einstellungen.js"), /KiZugang\.render\(\$\("zugang-wahl"\)/, "the page draws the choice into its fieldset");
  const ways = access.options({ abo: true }).map(option => option.value);
  assert.deepEqual(ways, ["einladung", "abo", "schluessel"]);
  assert.deepEqual(Object.keys(logic.WAY_CARDS), ways, "every way has the card that asks for what it needs");
  const invitation = card(ki, logic.WAY_CARDS.einladung);
  assert.match(invitation, /<h2 id="einladung-titel">Einladungscode<\/h2>/);
  assert.match(invitation, /<input class="input" id="einladung-code"/);
  assert.match(invitation, /id="einladung-einloesen"[^>]*>Einladung einlösen<\/button>/);
  const subscription = card(ki, logic.WAY_CARDS.abo);
  assert.match(subscription, /<h2 id="abo-titel">Claude mit eigenem Abo<\/h2>/);
  assert.match(subscription, /<ul id="abo-skills"><\/ul>/);
  assert.match(subscription, /id="abo-einschalten"[^>]*>Zugang einschalten<\/button>/);
  const key = card(ki, logic.WAY_CARDS.schluessel);
  assert.match(key, /<h2 id="schluessel-titel">Eigener API-Schlüssel<\/h2>/);
  assert.match(key, /<input id="schluessel" type="password"/);
  assert.match(key, /id="speichern"[^>]*>Prüfen und speichern<\/button>/);
  for (const way of ways) assert.match(ki, new RegExp(`<section class="card" id="${logic.WAY_CARDS[way]}"[^>]*hidden>`),
    `${way} shows only once chosen`);
});

test("KI und Budget: the budget of the month (G46) with a bar and a row per task", () => {
  const budget = card(panel(read("einstellungen.html"), "ki"), "kosten");
  assert.match(budget, /<h2 id="kosten-titel">Budget<\/h2>/);
  assert.match(budget, /id="budget-zeile"/);
  assert.match(budget, /id="budget-neu"/);
  assert.match(budget, /<div class="budget__bar" id="budget-balken" role="img" hidden><div class="budget__fill" id="budget-fuellung">/);
  assert.match(budget, /<dl class="budget__rows" id="budget-aufgaben"><\/dl>/);
  assert.match(budget, /id="budget-hinweis"/);
  assert.match(budget, /id="budget-gesamt"/);
  const script = read("einstellungen.js");
  assert.match(script, /\$\("budget-aufgaben"\)\.replaceChildren\(\.\.\.view\.rows\.flatMap\(row => \[/, "one row per task");
  assert.match(script, /el\("dt", \{\}, `\$\{row\.label\} \(\$\{row\.count\}\)`\), el\("dd", \{ class: "num" \}, row\.usd\)/);
  assert.ok(logic.budgetView(MEDIATION, COSTS).rows.length > 1, "the costs of the month come split by task");
});

test("Erweitert: the finer settings stay hidden until opened (G41) and hold the pre-releases (G47)", () => {
  const html = read("einstellungen.html");
  const advanced = panel(html, "erweitert");
  assert.match(advanced, /<h2 id="erweitert-titel">Erweitert<\/h2>/);
  assert.match(advanced, /Ohne sie läuft die App mit den Voreinstellungen\./);
  assert.match(advanced, /<a href="\/inhalte">Inhalte als Text bearbeiten<\/a>/);
  assert.notEqual(logic.sectionOf(""), "erweitert", "the page opens elsewhere");
  assert.match(read("einstellungen.css"), /\.settings\[data-tabs\] \.settings__panel:not\(\[data-aktiv\]\) \{ display: none; \}/,
    "a section not chosen stays hidden");
  const beta = card(advanced, "vorabversionen");
  assert.match(beta, /<h2 id="beta-titel">Vorabversionen<\/h2>/);
  assert.match(beta, /<label class="schalter"><input type="checkbox" id="beta-an"> Vorabversionen als Update anbieten<\/label>/,
    "off by default: only released versions");
  assert.match(html, /<script src="\/vorabversionen\.js"><\/script>/);
  assert.match(read("vorabversionen.js"), /senden\("\/api\/app\/vorabversionen", \{ an \}\)/);
});

test("Über die App: the logo, the name and the version (G4)", () => {
  const about = card(panel(read("einstellungen.html"), "ueber"), "ueber-die-app");
  assert.match(about, /<h2 id="ueber-titel">Über die App<\/h2>/);
  const script = read("app.js");
  assert.match(script, /el\("img", \{ class: "about__logo", src: "\/as-logo\.svg"[^}]*alt: "Logo AS" \}\)/);
  assert.match(script, /el\("p", \{ class: "about__name" \}, "Bewerbungsbegleiter"\)/);
  assert.match(script, /const ort = document\.getElementById\("ueber-die-app"\)/);
  assert.match(script, /ort\.append\(ueberDieApp\(info\.version\)/);
  const logo = read("as-logo.svg");
  const colours = new Set(logo.replace(/@media[^{]*\{[^}]*\}\}/g, "").match(/#[0-9a-fA-F]{3,8}\b/g));
  assert.equal(colours.size, 1, "the logo is one colour");
});

test("the remaining sections lead to where their settings live", () => {
  const html = read("einstellungen.html");
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

test("Erweitert: a switch allows three pages for the CV (G51), off by default", () => {
  const html = read("einstellungen.html");
  const length = card(panel(html, "erweitert"), "seitengrenze");
  assert.match(length, /<h2 id="seitengrenze-titel">Länge des Lebenslaufs<\/h2>/);
  assert.match(length, /höchstens zwei Seiten, das Anschreiben genau eine/);
  assert.match(length, /<label class="schalter"><input type="checkbox" id="drei-seiten"> Drei Seiten für den Lebenslauf erlauben<\/label>/);
  assert.equal(logic.sectionOf("#seitengrenze"), "erweitert");
  assert.match(html, /<script src="\/seitengrenze\.js"><\/script>/);
  const script = read("seitengrenze.js");
  assert.match(script, /senden\("\/api\/unterlagen\/seitengrenze", \{ lebenslauf_seiten: an \? 3 : 2 \}\)/);
  assert.match(script, /holen\("\/api\/unterlagen\/seitengrenze"\)/);
});
