// Every cost or time amount keeps number and unit together (#336, G45), also where no logic module builds it: the
// page „KI“, the setup step of the extension and the path on „Heute“. The currency stands first, as the design system
// says (#347). Read from the pages as written. Invented numbers.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const trefferLogik = require("../seiten/treffer-logik.js");
const suchlaufLogik = require("../seiten/suchlauf-logik.js");
const suchbegriffeLogik = require("../seiten/suchbegriffe-logik.js");

const NBSP = " ";
const PAGES = path.join(__dirname, "..", "seiten");
const page = name => fs.readFileSync(path.join(PAGES, name), "utf8");

/** `kosten` and `statusText` of ki.js as written, with `money` from treffer-logik.js and texte.js as the page gets them. */
function kiTexts(waehrung) {
  const source = page("ki.js");
  const kosten = /\n {2}const kosten = betrag => [\s\S]*?\);\n/.exec(source)[0];
  const statusText = /\n {2}function statusText\(s\) \{\n[\s\S]*?\n {2}\}\n/.exec(source)[0];
  const Texte = require("../seiten/texte.js");
  // since #427 ki.js keeps window.Texte in the constant Texte
  return new Function("waehrung", "money", "window", "Texte", `${kosten}${statusText}; return { kosten, statusText };`)(
    waehrung, trefferLogik.money, { Texte }, Texte);
}

test("the helpers of the pages put the currency first and keep units with their number", () => {
  assert.equal(trefferLogik.money(0.034, "CHF"), `CHF${NBSP}0.03`);
  assert.equal(trefferLogik.minutes(1), `1${NBSP}Minute`);
  assert.equal(trefferLogik.minutes(23), `23${NBSP}Minuten`);
  assert.equal(trefferLogik.seconds(1), `1${NBSP}Sekunde`);
  assert.equal(trefferLogik.seconds(40), `40${NBSP}Sekunden`);
});

test("the page „KI“ writes its costs as «etwa CHF 0.05»", () => {
  assert.equal(kiTexts("CHF").kosten(0.05), `etwa CHF${NBSP}0.05`);
  assert.equal(kiTexts("USD").kosten(1.5), `etwa USD${NBSP}1.50`);
  assert.equal(kiTexts("USD").kosten(null), "Kosten unbekannt");
  assert.equal(kiTexts("USD").kosten(undefined), "Kosten unbekannt");
});

test("the status of the page „KI“ puts the currency before every amount", () => {
  const own = { eingerichtet: true, vermittlung: false, kosten_usd: 0.05 };
  assert.equal(kiTexts("USD").statusText(own), `KI eingerichtet (direkt, Entwicklung). Diesen Monat etwa USD${NBSP}0.05.`);
  const mediation = { eingerichtet: true, vermittlung: true, guthaben_chf: 5, verbraucht_chf: 0.1 };
  assert.equal(kiTexts("CHF").statusText(mediation),
    `KI eingerichtet (über die Vermittlung). Guthaben: CHF${NBSP}0.10 von CHF${NBSP}5.00 verbraucht.`);
});

test("the application page loads treffer-logik.js before ki.js, which takes money from it", () => {
  const html = page("bewerbung.html");
  assert.ok(html.indexOf('src="/treffer-logik.js"') > 0);
  assert.ok(html.indexOf('src="/treffer-logik.js"') < html.indexOf('src="/ki.js"'));
  assert.match(page("ki.js"), /const \{ money \} = window\.TrefferLogik;/);
});

test("the search page loads treffer-logik.js before suchlauf-logik.js, which takes seconds from it", () => {
  const html = page("treffer.html");
  assert.ok(html.indexOf('src="/treffer-logik.js"') > 0);
  assert.ok(html.indexOf('src="/treffer-logik.js"') < html.indexOf('src="/suchlauf-logik.js"'));
});

test("the end of „Alle prüfen“ names the costs as «Kosten: CHF 0.06.»", () => {
  const stand = { bewertet: 3, von: 3, offen: [], ohneText: 0, gestoppt: false, kosten: 0.06 };
  assert.equal(trefferLogik.schlussText(stand, 0, "CHF"), `3 von 3 Treffern bewertet. Kosten: CHF${NBSP}0.06.`);
});

test("seconds stay with their number while a search waits or a package runs", () => {
  assert.deepEqual(suchlaufLogik.laufZeile({ portal: "jobs.ch", phase: "pause", etappe: 2, etappen: 3, sekunden: 40 }),
    [`jobs.ch: Pause vor Etappe 2 von 3, noch 40${NBSP}Sekunden …`]);
  assert.equal(trefferLogik.pruefSchritt({ bewertet: 0, von: 2 }, ["a", "b"], 12), `Stellen 1 bis 2 von 2 prüfen, seit 12${NBSP}Sekunden …`);
  for (const satz of ["stelle-sie", "stelle-du"]) {
    assert.match(suchbegriffeLogik.texte(satz).wartenNotiz, new RegExp(`^Meist unter 30${NBSP}Sekunden\\.`));
  }
});

test("the setup step of the extension keeps «2 Minuten» together", () => {
  const literal = /"1 bis 2[^"]*Minuten"/.exec(page("einrichtung.js"))[0];
  assert.equal(JSON.parse(literal), `1 bis 2${NBSP}Minuten`);
});

test("the next step on „Heute“ keeps «20 Minuten» together", () => {
  // the «·» line itself is whole parts (#342, dot_line_pages.test.cjs); here only the amount counts
  const eyebrow = /<p class="path__eyebrow">(.*?)<\/p>/.exec(page("uebersicht.html"))[1].replaceAll("&nbsp;", NBSP);
  assert.match(eyebrow, new RegExp(`>etwa 20${NBSP}Minuten<`));
});

test("no page writes an amount after its number or a duration with an ordinary space", () => {
  // the check of #347: «0.05 CHF» or «von 5.00 verbraucht» came from `toFixed(2)}` and a space, a parted duration
  // from a digit or a placeholder and a space before Sekunde or Minute
  const parted = [/toFixed\(2\)\} /, /[0-9}] (Sekunde|Minute)/];
  const found = fs.readdirSync(PAGES).filter(name => /\.(js|html)$/.test(name)).flatMap(name =>
    page(name).split("\n").flatMap((line, index) => (parted.some(rule => rule.test(line)) ? [`${name}:${index + 1}`] : [])));
  assert.deepEqual(found, []);
});
