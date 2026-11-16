// Every cost or time amount keeps number and unit together (#336, G45), also where no logic module builds it: the
// page „KI“, the setup step of the extension and the path on „Heute“. Read from the pages as written. Invented numbers.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const NBSP = " ";
const page = name => fs.readFileSync(path.join(__dirname, "..", "seiten", name), "utf8");

test("the page „KI“ joins the amount and its currency", () => {
  const line = /\n {2}const kosten = betrag => .*;\n/.exec(page("ki.js"))[0];
  const kosten = new Function("waehrung", `${line}; return kosten;`);
  assert.equal(kosten("CHF")(0.034), `ca. 0.03${NBSP}CHF`);
  assert.equal(kosten("USD")(1.5), `ca. 1.50${NBSP}USD`);
  assert.equal(kosten("USD")(null), "Kosten unbekannt");
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
