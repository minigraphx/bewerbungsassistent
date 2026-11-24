// The catalog of bewerbungen/sprachen/ as /uebersetzung.js hands it to a page of one language (#431, #432), for the
// tests of Meine Angaben in French and English.
"use strict";
const fs = require("node:fs");
const path = require("node:path");

const CATALOG = path.join(__dirname, "..", "..", "bewerbungen", "sprachen");
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);

/** What translation_catalog.for_page hands a page of one language: plain texts and text sets. */
function catalogFor(language) {
  const files = fs.readdirSync(CATALOG).filter((name) => name.endsWith(".json"));
  const entries = Object.assign({}, ...files.map((name) => JSON.parse(fs.readFileSync(path.join(CATALOG, name), "utf8"))));
  const texts = {};
  const sets = {};
  for (const [key, entry] of Object.entries(entries)) {
    if (key.startsWith(SET_PREFIX)) sets[key.slice(SET_PREFIX.length)] = entry[language];
    else texts[key] = entry[language];
  }
  return { sprache: language, texte: texts, saetze: sets };
}

/** "~" stands for the no-break space French puts before « : ? ! ; » and inside « ». */
const fr = (text) => text.replaceAll("~", NBSP);

module.exports = { catalogFor, fr };
