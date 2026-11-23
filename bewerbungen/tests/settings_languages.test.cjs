// The page Einstellungen in French and English (#417, G10, docs/design/sprachen.md): the texts einstellungen-logik.js
// builds at run time, such as the card „KI-Budget“ and the sentence of a used-up budget, come in the app language with
// the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages. German stays as it was.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const texte = require("../seiten/texte.js");
const logic = require("../seiten/einstellungen-logik.js");
const overview = require("../seiten/uebersicht-logik.js");

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

// An invented monthly budget of the mediation, used up in November and renewed on the first of December.
const USED_UP = { monat: "2026-11", erneuert_am: "2026-12-01", eingerichtet: true, vermittlung: true,
                  eigener_schluessel: false, guthaben_chf: 5, verbraucht_chf: 5, kosten_usd: 5 };
const COSTS = { monat_usd: 5, gesamt_usd: 7.5, aufrufe: 12,
                aufgaben: { rate: { aufrufe: 10, usd: 4 }, made_up: { aufrufe: 2, usd: 1 } } };
const OWN_KEY = { monat: "2026-11", eingerichtet: true, vermittlung: false, eigener_schluessel: true, kosten_usd: 1.5 };

const view = () => logic.budgetView(USED_UP, COSTS);
const card = found => ({ title: found.title, renewal: found.renewal, usedUp: found.usedUp, total: found.total,
                         rows: found.rows.map(row => row.label) });

test("the card of a used-up monthly budget comes in French", () => {
  assert.deepEqual(inLanguage("fr", () => card(view())), {
    title: "Budget IA en novembre",
    renewal: `Nouveau budget le 1er${NBSP}décembre`,
    usedUp: `Le budget IA pour novembre est épuisé. L'IA fonctionne à nouveau dès le 1er${NBSP}décembre${NBSP}; `
      + "tout le reste continue de fonctionner.",
    total: `Depuis le début, CHF${NBSP}7.50 pour 12 appels`,
    rows: ["Évaluer les offres", "Autres"],
  });
  assert.equal(inLanguage("fr", () => logic.invitationUsedUp(USED_UP)),
               `Le budget IA pour novembre est épuisé. L'IA fonctionne à nouveau dès le 1er${NBSP}décembre.`);
});

test("the card of a used-up monthly budget comes in English", () => {
  assert.deepEqual(inLanguage("en", () => card(view())), {
    title: "AI budget in November",
    renewal: `New budget on 1${NBSP}December`,
    usedUp: `The AI budget for November is used up. The AI works again from 1${NBSP}December; everything else keeps working.`,
    total: `Since the start CHF${NBSP}7.50 in 12 calls`,
    rows: ["Rating jobs", "Other"],
  });
  assert.equal(inLanguage("en", () => logic.budgetView(OWN_KEY, COSTS).title), "Costs in November");
});

test("the sections on the left come in the app language", () => {
  assert.deepEqual(inLanguage("fr", () => logic.SECTIONS.map(section => section.label)),
                   ["IA, budget et langue", "Recherche et portails", "Navigateur et extension", "Poste, apprentissage, ORP",
                    "Données et sauvegarde", "Avancé", "À propos de l'app"]);
});

test("one and three pick the French singular and plural, never a form with (s)", () => {
  const forms = count => inLanguage("fr", () => ({
    selected: overview.selectionLabel(count),
    discarded: overview.abgeschlossenTeil("Verworfen", count),
    withdrawn: overview.abgeschlossenTeil("Zurückgezogen", count),
    done: overview.stageDone(count, "Absage", "Absage", "alle"),
  }));
  assert.deepEqual(forms(1), { selected: "1 sélectionnée", discarded: "1 écartée", withdrawn: "1 retirée",
                               done: `1 candidature passée à «${NBSP}Absage${NBSP}».` });
  assert.deepEqual(forms(3), { selected: "3 sélectionnées", discarded: "3 écartées", withdrawn: "3 retirées",
                               done: `3 candidatures passées à «${NBSP}Absage${NBSP}».` });
});

test("the views keep their plural names in French, apart from the stage names", () => {
  assert.deepEqual(inLanguage("fr", () => overview.stageDone(1, "Bewerben", "Bewerben", "beworben")),
                   `1 candidature passée à «${NBSP}Bewerben${NBSP}». Elle figure maintenant sous «${NBSP}Mises de côté${NBSP}».`);
  assert.equal(inLanguage("en", () => overview.stageDone(3, "Beworben", "Beworben", "gemerkt")),
               "3 applications set to “Beworben”. They are now under “Applied”.");
});

test("German stays as it was", () => {
  assert.equal(overview.selectionLabel(1), "1 ausgewählt");
  assert.equal(overview.abgeschlossenTeil("Verworfen", 1), "1 verworfen");
  assert.equal(overview.stageDone(1, "Absage", "Absage", "alle"), "1 Bewerbung auf „Absage“ gesetzt.");
  assert.equal(overview.stageDone(3, "Gemerkt", "Gemerkt", "beworben"),
               "3 Bewerbungen auf „Gemerkt“ gesetzt. Sie stehen jetzt unter „Gemerkt“.");
  assert.deepEqual(card(view()), {
    title: "KI-Budget im November",
    renewal: `Neues Budget am 1.${NBSP}Dezember`,
    usedUp: `Das KI-Budget für November ist aufgebraucht. Die KI geht wieder ab 1.${NBSP}Dezember; alles andere funktioniert weiterhin.`,
    total: `Seit Beginn CHF${NBSP}7.50 in 12 Aufrufen`,
    rows: ["Stellen einschätzen", "Weitere"],
  });
  assert.equal(logic.invitationUsedUp(USED_UP),
               `Das KI-Budget für November ist aufgebraucht. Die KI geht wieder ab 1.${NBSP}Dezember.`);
  assert.equal(logic.SECTIONS[0].label, "KI, Budget und Sprache");
});
