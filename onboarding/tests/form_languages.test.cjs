// Meine Angaben, the form, in French and English (#431, G10, docs/design/sprachen.md): what dom.js shows of form.json
// (labels, hints, placeholders, options, cantons) speaks the app language with the catalog in bewerbungen/sprachen/ as
// /uebersetzung.js hands it to the page. What is stored stays German: the values of options and choices, the codes of
// the cantons, the suggestions of a field. The own words of dom.js follow with #432. The file for sharing loads no
// texte.js; its T gives the German back. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { findAll, loadScripts } = require("./fake_dom.cjs");

const CATALOG = path.join(__dirname, "..", "..", "bewerbungen", "sprachen");
const TEXTE = "../../bewerbungen/seiten/texte.js";
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);
const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const app = loadScripts([TEXTE, "words.js", "validate.js", "model.js", "dom.js"]);
const standalone = loadScripts(["words.js", "validate.js", "model.js", "dom.js"]);
const field = (sectionId, id) => form.sections.find((s) => s.id === sectionId).fields.find((f) => f.id === id);
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const fr = (text) => text.replaceAll("~", NBSP); // "~" stands for the no-break space French puts before « : ? »

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

function inLanguage(language, check) {
  app.Texte.setzeSprache(language, catalogFor(language));
  try {
    return check(app);
  } finally {
    app.Texte.setzeSprache();
  }
}

const inAll = (check) => ({ de: check(app), fr: inLanguage("fr", check), en: inLanguage("en", check) });

function view(page, sectionId, id, value, track = "job") {
  return page.fieldView(field(sectionId, id), {
    track, value, path: `${sectionId}.${id}`, cantons: form.cantons, tagSuggestions: [], onChange() {}, onBlur() {},
  });
}

const texts = (node, tag) => byTag(node, tag).map((n) => n.textContent);
const values = (node, tag) => byTag(node, tag).map((n) => n.value);

// The first option of a select without its own empty label, „– bitte wählen –“, is a word of dom.js (#432).
const options = (select) => texts(select, "option").slice(1);

test("a select shows its options in the app language and keeps their German values", () => {
  const shown = inAll((page) => {
    const select = byTag(view(page, "searchJob", "remote", "teilweise"), "select")[0];
    return { label: texts(view(page, "searchJob", "remote", ""), "label")[0], options: options(select), values: values(select, "option") };
  });

  assert.deepEqual(shown.de, { label: "Homeoffice erwünscht?", options: ["ja", "teilweise", "nein"], values: ["", "ja", "teilweise", "nein"] });
  assert.deepEqual(shown.fr, { label: fr("Télétravail souhaité~?"), options: ["oui", "en partie", "non"], values: ["", "ja", "teilweise", "nein"] });
  assert.deepEqual(shown.en, { label: "Working from home wanted?", options: ["yes", "partly", "no"], values: ["", "ja", "teilweise", "nein"] });
});

test("a value from cv.yaml outside the options is shown as it is in every language", () => {
  const own = inLanguage("fr", (page) => {
    const select = byTag(view(page, "searchJob", "remote", "zweimal pro Woche"), "select")[0];
    return { options: options(select), values: values(select, "option") };
  });

  assert.deepEqual(own, { options: ["oui", "en partie", "non", "zweimal pro Woche"],
    values: ["", "ja", "teilweise", "nein", "zweimal pro Woche"] });
});

test("the empty label of a select from form.json speaks the app language", () => {
  const shown = inAll((page) => texts(byTag(view(page, "languages", "x-level", ""), "select")[0], "option"));

  assert.deepEqual(shown.de, ["ohne Stufe", "A1", "A2", "B1", "B2", "C1", "C2"]);
  // Stufe is the rating the dossier draws, Niveau the level in words (UI/UX ruling on #431).
  assert.deepEqual(shown.fr, ["sans échelon", "A1", "A2", "B1", "B2", "C1", "C2"]);
  assert.deepEqual(shown.en, ["no rating", "A1", "A2", "B1", "B2", "C1", "C2"]);
});

test("a placeholder, a hint and a label per track follow the app language", () => {
  const shown = inAll((page) => {
    const label = view(page, "person", "label", "");
    const name = view(page, "person", "name", "", "apprenticeship");
    return { placeholder: byTag(label, "input")[0].placeholder, label: texts(name, "label")[0], hint: texts(name, "p")[0] };
  });

  assert.deepEqual(shown.de, { placeholder: "z.B. Kaufmann EFZ – Buchhaltung und Administration", label: "Vor- und Nachname *",
    hint: "Schreib deinen Namen genau wie im Lebenslauf, mit denselben Akzenten und Umlauten. In dieser Schreibweise ersetzt die App den Namen, bevor ein Text zur KI geht." });
  assert.match(shown.fr.placeholder, /^p\. ex\. .*CFC/);
  assert.equal(shown.fr.label, "Prénom et nom *");
  assert.match(shown.fr.hint, /^Écris ton nom /);
  assert.match(shown.fr.hint, /l'IA/);
  assert.match(shown.en.placeholder, /^e\.g\. /);
  assert.equal(shown.en.label, "First and last name *");
  assert.match(shown.en.hint, /the AI/);
});

test("a choice says its sentences in the app language and stores the German one", () => {
  const changes = [];
  const shown = inLanguage("fr", (page) => {
    const node = page.fieldView(field("style", "tone"), {
      track: "job", value: "", path: "style.tone", onChange: (v) => changes.push(v), onBlur() {},
    });
    const radios = byTag(node, "input").filter((n) => n.type === "radio" && n.value);
    radios[1].onchange();
    // the last span, „Eigene Formulierung:“, is a word of dom.js (#432)
    return { legend: texts(node, "legend")[0], options: texts(node, "span").slice(0, -1), values: radios.map((r) => r.value) };
  });

  assert.deepEqual(shown, {
    legend: "Ton *",
    options: ["Factuel et aimable", "Personnel et chaleureux", "Bref et direct"],
    values: ["Sachlich und freundlich", "Persönlich und herzlich", "Kurz und direkt"],
  });
  assert.deepEqual(changes, ["Persönlich und herzlich"]);
});

test("the cantons show their names in the app language and keep their codes", () => {
  const shown = inAll((page) => {
    const node = view(page, "searchJob", "cantons", ["GE"]);
    const boxes = byTag(node, "input");
    const geneva = boxes.findIndex((box) => box.value === "GE");
    return { name: texts(node, "span")[geneva], code: boxes[geneva].value, checked: boxes[geneva].checked };
  });

  assert.deepEqual(shown.de, { name: "Genf", code: "GE", checked: true });
  assert.deepEqual(shown.fr, { name: "Genève", code: "GE", checked: true });
  assert.deepEqual(shown.en, { name: "Geneva", code: "GE", checked: true });
});

test("the portals keep their values and say their labels in the app language", () => {
  const shown = inLanguage("en", (page) => {
    const node = view(page, "searchJob", "portalsOff", []);
    return { labels: texts(node, "span"), values: values(node, "input") };
  });

  assert.deepEqual(shown.values, ["job-room", "jobs.ch", "jobscout24", "ictjobs"]);
  assert.deepEqual(shown.labels, ["job-room (RAV jobs, all occupations)", "jobs.ch (all occupations)",
    "jobscout24 (all occupations)", "ictjobs (IT only)"]);
});

test("the suggestions of a field stay German, its label and hint follow the app language", () => {
  const shown = inLanguage("fr", (page) => {
    const node = view(page, "languages", "fluency", "", "apprenticeship");
    return { label: texts(node, "label")[0], hint: texts(node, "p")[0], suggestions: values(node, "option") };
  });

  assert.equal(shown.label, "Niveau *");
  assert.equal(shown.hint, "Choisis une proposition ou écris le niveau avec tes propres mots.");
  assert.deepEqual(shown.suggestions, field("languages", "fluency").suggestions);
});

test("the file for sharing has no texte.js and stays German with the same T", () => {
  assert.equal(typeof standalone.Texte, "undefined");
  assert.equal(standalone.T("Ort"), "Ort");
  assert.equal(standalone.T("Zeile {nummer} entfernen", { nummer: 2 }), "Zeile 2 entfernen");
  const select = byTag(view(standalone, "searchJob", "remote", ""), "select")[0];
  assert.deepEqual(texts(select, "option"), ["– bitte wählen –", "ja", "teilweise", "nein"]);
});
