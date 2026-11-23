// The page Heute in French and English (#419, G10, docs/design/sprachen.md): the texts heute-logic.js builds at run
// time, dates and deadlines, the stand by stage, the line under the title and the pass over saved jobs, come in the app
// language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages. German stays as it was.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const texte = require("../seiten/texte.js");
const L = require("../seiten/uebersicht-logik.js");
const H = require("../seiten/heute-logic.js");

const CATALOG = path.join(__dirname, "..", "sprachen");
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);
const TODAY = "2026-11-12";

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

const b = (id, status, fields = {}) => ({ id, firma: `Firma ${id}`, stelle: `Stelle ${id}`, status, eingetragen_am: "2026-11-01", ...fields });
const ROWS = L.mitSchritten([
  b("a", "Gemerkt", { frist: "2026-11-20", stelle: "Netzplaner:in", firma: "Beispiel Energie AG" }),
  b("w", "Beworben", { beworben_am: "2026-11-10", firma: "Beispiel Versicherung" }),
  b("g", "Gespräch", { gespraech_am: "2026-11-18", firma: "Muster Bank" }),
]);
const shown = options => H.dates(ROWS, TODAY, options).map(entry => [entry.day, entry.text]);
const STAND_ROWS = L.mitSchritten([
  b("m1", "Gemerkt", { frist: "2026-11-16" }), b("m2", "Gemerkt", { frist: "2026-11-17" }), b("w", "Beworben"),
  b("g", "Gespräch"), b("z", "Zusage"), b("a1", "Absage"), b("a2", "Absage"), b("v", "Verworfen"),
]);
const hints = (options, hits = { count: 8, last: "2026-11-10T09:00:00" }) =>
  Object.values(H.stand(STAND_ROWS, hits, TODAY, options)).map(({ hint }) => hint);
const FIRST_OF_DECEMBER = new Date(2026, 11, 1);
const MONDAY = new Date(2026, 10, 23);

test("dates and deadlines come in French", () => {
  assert.deepEqual(inLanguage("fr", () => shown()), [
    ["16.11.", "Préparer l'entretien chez Muster Bank"],
    ["18.11.", "Entretien chez Muster Bank"],
    ["20.11.", "Délai pour Netzplaner:in, Beispiel Energie AG"],
    ["24.11.", "Relancer Beispiel Versicherung si aucune réponse n'est arrivée"],
  ]);
  assert.deepEqual(inLanguage("fr", () => shown({ apprenticeship: true }).slice(0, 2)), [
    ["16.11.", "Se préparer à l'invitation de Muster Bank"],
    ["18.11.", "Invitation de Muster Bank"],
  ]);
});

test("dates and deadlines come in English", () => {
  assert.deepEqual(inLanguage("en", () => shown()), [
    ["16.11.", "Prepare for the interview at Muster Bank"],
    ["18.11.", "Interview at Muster Bank"],
    ["20.11.", "Deadline for Netzplaner:in, Beispiel Energie AG"],
    ["24.11.", "Follow up with Beispiel Versicherung if there is no answer yet"],
  ]);
});

test("the stand by stage words its hints in the app language, one and more apart", () => {
  assert.deepEqual(inLanguage("fr", () => hints()),
    ["de la recherche du 10.11.", "2 délais cette semaine", "1 entretien", "1 réponse positive, 2 refus, 1 écartée"]);
  assert.deepEqual(inLanguage("en", () => hints()),
    ["from the search on 10.11.", "2 deadlines this week", "1 interview", "1 offer, 2 rejections, 1 discarded"]);
  assert.equal(inLanguage("fr", () => H.stand([], null, TODAY).neu.hint), "pas encore de recherche");
  assert.equal(inLanguage("en", () => H.stand(L.mitSchritten([b("g", "Gespräch"), b("h", "Gespräch")]), null, TODAY,
    { apprenticeship: true }).beworben.hint), "2 invitations");
});

test("the line under the title counts in words in the app language", () => {
  assert.equal(inLanguage("fr", () => H.waiting(4).values.anzahl), "Quatre");
  assert.equal(inLanguage("en", () => H.waiting(12).values.anzahl), "Twelve");
  assert.equal(inLanguage("fr", () => texte.text("heute.wartet.viele", "stelle-du", H.waiting(3).values)),
    "Trois choses t'attendent, la plus importante en premier.");
  assert.equal(H.waiting(13).values.anzahl, "13");
});

test("the date in the line under the title is French with the first of a month as 1er", () => {
  assert.equal(inLanguage("fr", () => H.todayLine(FIRST_OF_DECEMBER)), "Mardi 1er décembre");
  assert.equal(inLanguage("fr", () => H.todayLine(MONDAY)), "Lundi 23 novembre");
  assert.equal(inLanguage("en", () => H.todayLine(FIRST_OF_DECEMBER)), "Tuesday 1 December");
});

test("the pass over saved jobs counts and ends in the app language", () => {
  assert.equal(inLanguage("fr", () => H.passProgress(0, 3)), "1 sur 3");
  assert.equal(inLanguage("fr", () => H.passResult({ bewerben: 2, verworfen: 1, spaeter: 1 })),
    `Tri terminé${NBSP}: 2 à postuler, 1 écartée, 1 pour plus tard.`);
  assert.equal(inLanguage("en", () => H.passResult({ verworfen: 3 })), "Review finished: 3 discarded.");
  assert.equal(inLanguage("en", () => H.passResult({})), "Review finished.");
  assert.deepEqual(inLanguage("fr", () => H.passAd({ link: "" }, "", null).zeilen), ["Le texte de l'annonce manque pour cette offre."]);
});

test("the stage of an application is named in the singular, as the #420 ruling says", () => {
  assert.deepEqual(inLanguage("fr", () => ["Gemerkt", "Bewerben", "Beworben", "Gespräch"].map(s => texte.statusName(s, "stelle-sie"))),
    ["Mise de côté", "À postuler", "Envoyée", "Entretien"]);
  assert.equal(inLanguage("fr", () => texte.statusName("Gespräch", "lehrstelle-du")), "Invitation");
  assert.equal(inLanguage("en", () => texte.statusName("Beworben", "stelle-sie")), "Applied");
});

test("German stays as it was", () => {
  assert.deepEqual(shown().map(([, text]) => text), ["Gespräch bei Muster Bank vorbereiten", "Gespräch bei Muster Bank",
    "Frist für Netzplaner:in, Beispiel Energie AG", "Nachfragen bei Beispiel Versicherung, falls keine Antwort da ist"]);
  assert.equal(shown({ apprenticeship: true })[1][1], "Einladung bei Muster Bank");
  assert.deepEqual(hints(), ["aus der Suche vom 10.11.", "2 Fristen in dieser Woche", "1 Gespräch", "1 Zusage, 2 Absagen, 1 verworfen"]);
  assert.equal(H.waiting(4).values.anzahl, "Vier");
  assert.equal(H.todayLine(FIRST_OF_DECEMBER), FIRST_OF_DECEMBER.toLocaleDateString("de-CH", { weekday: "long", day: "numeric", month: "long" }));
  assert.equal(H.todayLine(MONDAY), "Montag, 23. November");
  assert.equal(H.passResult({ bewerben: 1, verworfen: 2 }), "Durchgang fertig: 1 zum Bewerben, 2 verworfen.");
  assert.deepEqual(["Gemerkt", "Beworben", "Gespräch", "Absage"].map(s => texte.statusName(s, "stelle-sie")),
    ["Gemerkt", "Beworben", "Gespräch", "Absage"]);
});
