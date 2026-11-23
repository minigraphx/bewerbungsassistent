// Stellen (#262, A3, G55, G56, G58, #374): the page is called Stellen, Neu, In Bewerbungen, Verworfen and Firmen are
// its tabs, and every new hit is decided with Bewerbung vorbereiten as the main button, Merken or Verwerfen.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const texte = require("../seiten/texte.js");
const logik = require("../seiten/treffer-logik.js");
const anzeige = require("../seiten/suche-anzeige.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const tabsOf = html => html.slice(html.indexOf('<nav class="tabs"'), html.indexOf("</nav>", html.indexOf('<nav class="tabs"')));

test("the page is called Stellen in the tab and the title (G55)", () => {
  const html = read("treffer.html");
  assert.match(html, /<title>Stellen<\/title>/);
  assert.match(html, /<h1 id="titel" data-text="nav.stellen">Stellen<\/h1>/);
  assert.match(read("treffer.js"), /document\.title = Texte\.text\("nav\.stellen", satz\)/);
});

test("Neu, In Bewerbungen, Verworfen and Firmen are the tabs of Stellen, on both pages (G56, #374)", () => {
  for (const [page, current] of [["treffer.html", "neu"], ["firmen.html", "firmen"]]) {
    const tabs = tabsOf(read(page));
    const names = [...tabs.matchAll(/data-reiter="([\w-]+)"/g)].map(m => m[1]);
    assert.deepEqual(names, ["neu", "in-bewerbungen", "verworfen", "firmen"], page);
    assert.match(tabs, new RegExp(`data-reiter="${current}"[^>]*aria-current="page"`), page);
    assert.match(tabs, /href="\/firmen"/, page);
    // one label for Sie, du and Lehrstelle: the tab carries no data-text of its own
    assert.match(tabs, /data-reiter="in-bewerbungen"[^>]*>In Bewerbungen <span class="num" data-zahl="uebernommen">/, page);
    assert.doesNotMatch(tabs, />Gemerkt </, page);
  }
  assert.match(tabsOf(read("treffer.html")), /href="#in-bewerbungen"/);
  assert.match(tabsOf(read("firmen.html")), /href="\/treffer#in-bewerbungen"/);
  assert.match(read("firmen.html"), /<h1 id="titel" data-text="nav.stellen">Stellen<\/h1>/);
  assert.doesNotMatch(read("treffer.html"), /Firmen ansehen<\/a>/);
});

test("a tab is chosen by the address, so Firmen can lead back to In Bewerbungen", () => {
  assert.equal(logik.reiterAus("#in-bewerbungen"), "uebernommen");
  assert.equal(logik.reiterAus("#verworfen"), "verworfen");
  assert.equal(logik.reiterAus("#neu"), "neu");
  assert.equal(logik.reiterAus(""), "neu");
  assert.equal(logik.reiterAus("#etwas"), "neu");
  assert.equal(logik.reiterAus(undefined), "neu");
  assert.equal(logik.reiterName("uebernommen"), "in-bewerbungen");
  assert.equal(logik.reiterName("neu"), "neu");
});

test("#gemerkt, the address of the tab before #374, still leads to In Bewerbungen", () => {
  assert.equal(logik.reiterAus("#gemerkt"), "uebernommen");
  assert.equal(logik.reiterAus("gemerkt"), "uebernommen");
});

test("only the tab In Bewerbungen says what it holds, for Sie and du (#374)", () => {
  const html = read("treffer.html");
  assert.match(html, /<p id="reiter-erklaerung" class="search__caption" data-text="suche.in-bewerbungen" hidden>/);
  assert.ok(html.indexOf('id="reiter-erklaerung"') < html.indexOf('id="liste"'), "the caption stands above the list");
  assert.equal(texte.text("suche.in-bewerbungen", "stelle-sie"),
    "Treffer aus der Suche, die Sie gemerkt oder vorbereitet haben, mit ihrem Stand unter Bewerbungen.");
  assert.equal(texte.text("suche.in-bewerbungen", "stelle-du"),
    "Treffer aus der Suche, die du gemerkt oder vorbereitet hast, mit ihrem Stand unter Bewerbungen.");
  assert.equal(texte.text("suche.in-bewerbungen", "lehrstelle-du"),
    "Treffer aus der Suche, die du gemerkt oder vorbereitet hast, mit ihrem Stand unter Bewerbungen.");
});

test("the empty tab In Bewerbungen says how a hit comes there (#374)", () => {
  assert.deepEqual(anzeige.leer("uebernommen", true, ""),
    { titel: "Noch nichts in Bewerbungen", text: "Mit Merken oder Bewerbung vorbereiten kommt ein Treffer hierher." });
});

test("each new hit asks what to do, with Bewerbung vorbereiten as the main button (G58)", () => {
  const code = read("treffer.js");
  assert.match(code, /el\("button", \{ type: "button", class: "btn btn--primary" \}, Texte\.t\("Bewerbung vorbereiten"\)\)/);
  assert.match(code, /"\/api\/bewerbungen\/stand", \{ ids: \[neu\.bewerbung_id\], status: "Bewerben" \}/);
  assert.equal(texte.text("suche.entscheiden", "stelle-sie"), "Was möchten Sie mit dieser Stelle tun?");
  assert.equal(texte.text("suche.entscheiden", "stelle-du"), "Was möchtest du mit dieser Stelle tun?");
  assert.equal(texte.text("suche.entscheiden", "lehrstelle-du"), "Was möchtest du mit dieser Lehrstelle tun?");
});

test("the own stars stand under the AI and say they never reach it (G22)", () => {
  assert.equal(texte.text("suche.eigene", "stelle-sie"), "Ihre eigene Bewertung");
  assert.equal(texte.text("suche.eigene", "stelle-du"), "Deine eigene Bewertung");
  assert.equal(texte.text("suche.eigene-hinweis", "stelle-sie"), "Ihr Urteil, getrennt von der Note der KI. Geht nicht an die KI.");
  assert.equal(texte.text("suche.eigene-hinweis", "stelle-du"), "Dein Urteil, getrennt von der Note der KI. Geht nicht an die KI.");
});

test("hits without a grade are named above the list with the rating buttons (G44)", () => {
  const html = read("treffer.html");
  const box = html.indexOf('id="offen-box"');
  assert.ok(box > 0 && box < html.indexOf('id="liste"'), "the box stands above the list");
  assert.equal(logik.offenText(1, false), "1 Stelle ist noch nicht geprüft.");
  assert.equal(logik.offenText(2, false), "2 Stellen sind noch nicht geprüft.");
  assert.equal(logik.offenText(3, true), "3 Lehrstellen sind noch nicht geprüft.");
});
