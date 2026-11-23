// The page Einrichtung in French and English (#418, G10, docs/design/sprachen.md): the texts einrichtung-logik.js
// builds at run time, the end's open points, its title and the summary of the choice, come in the app language with
// the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages. German stays as it was.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const texte = require("../seiten/texte.js");
const logik = require("../seiten/einrichtung-logik.js");

const CATALOG = path.join(__dirname, "..", "sprachen");
const SET_PREFIX = "texte:";

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

const NOTHING_DONE = { kiVerbunden: false, erweiterungMoeglich: true, erweiterungGeladen: "" };
const openPoints = () => logik.offenePunkte(NOTHING_DONE).map(p => [p.titel, p.text, p.knopf]);
const JOB = { gesucht: "stelle", anrede: "sie", rav: true };
const APPRENTICESHIP = { gesucht: "lehrstelle", anrede: "du", rav: false };

test("the end of the setup names what is open in French", () => {
  assert.deepEqual(inLanguage("fr", openPoints), [
    ["IA", "Pas encore connectée. Sans IA, pas de notes ni de brouillons.", "Configurer l'IA"],
    ["Extension", "Pas encore chargée. Sans elle, l'app ne cherche pas sur les portails.", "Charger l'extension"],
  ]);
  assert.equal(inLanguage("fr", () => logik.abschlussTitel(logik.offenePunkte(NOTHING_DONE))), "Presque terminé");
  assert.equal(inLanguage("fr", () => logik.abschlussTitel([])), "Tout est configuré");
});

test("the end of the setup names what is open in English", () => {
  assert.deepEqual(inLanguage("en", openPoints), [
    ["AI", "Not connected yet. Without AI there are no grades and no drafts.", "Set up AI"],
    ["Extension", "Not loaded yet. Without it, the app does not search the portals.", "Load the extension"],
  ]);
  assert.equal(inLanguage("en", () => logik.abschlussTitel([])), "All set up");
});

test("the summary of the choice comes in the app language", () => {
  assert.equal(inLanguage("fr", () => logik.zusammenfassung(JOB)), "un poste, vous, avec ORP");
  assert.equal(inLanguage("fr", () => logik.zusammenfassung(APPRENTICESHIP)), "une place d'apprentissage, tu, sans ORP");
  assert.equal(inLanguage("en", () => logik.zusammenfassung(JOB)), "a job, formal, with RAV");
  assert.equal(inLanguage("en", () => logik.zusammenfassung(APPRENTICESHIP)), "an apprenticeship, informal, without RAV");
});

test("German stays as it was", () => {
  assert.deepEqual(openPoints(), [
    ["KI", "Noch nicht verbunden. Ohne KI gibt es keine Noten und keine Entwürfe.", "KI einrichten"],
    ["Erweiterung", "Noch nicht geladen. Ohne sie sucht die App nicht auf den Portalen.", "Erweiterung laden"],
  ]);
  assert.equal(logik.abschlussTitel([]), "Alles eingerichtet");
  assert.equal(logik.zusammenfassung(JOB), "eine Stelle, Sie, mit RAV");
  assert.equal(logik.zusammenfassung(APPRENTICESHIP), "eine Lehrstelle, du, ohne RAV");
  assert.equal(logik.zusammenfassung(null), "");
});
