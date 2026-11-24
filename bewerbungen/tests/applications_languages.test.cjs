// The page Bewerbungen in French and English (#420, G10, docs/design/sprachen.md): the texts bewerbungen-logic.js and
// wieder-logik.js build at run time, a list row with its status name, grade and dates, discarding the ticked ones and a
// job advertised again, come in the app language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands
// it to the pages. Every stored stage has a name in fr and en; German stays as it was.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const texte = require("../seiten/texte.js");
const L = require("../seiten/uebersicht-logik.js");
const A = require("../seiten/bewerbungen-logic.js");
const W = require("../seiten/wieder-logik.js");

const CATALOG = path.join(__dirname, "..", "sprachen");
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);
const STAGES = ["Gemerkt", "Bewerben", "Beworben", "Gespräch", "Absage", "Zusage", "Verworfen", "Zurückgezogen"];

/** What translation_catalog.for_page hands a page of one language: plain texts and text sets. */
function catalogFor(language) {
  const files = fs.readdirSync(CATALOG).filter(name => name.endsWith(".json"));
  const entries = Object.assign({}, ...files.map(name => JSON.parse(fs.readFileSync(path.join(CATALOG, name), "utf8"))));
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
const row = (entry, reasons = new Map()) => L.mitSchritten([entry], reasons)[0];
const PLAN = { Verworfen: ["a", "b"], "Zurückgezogen": ["c"], kept: ["d"] };
const ONE_EACH = { Verworfen: ["a"], "Zurückgezogen": ["c"], kept: ["d"] };
const repost = (datum, portal = "jobs.ch") => ({ datum, portal, link: `https://www.${portal}/inserat/${datum}` });
const RUN = { wieder_ausgeschrieben: { bewerbungen: 0, verworfen: 2 } };

test("every stored stage has a name in French and English, in the singular", () => {
  assert.deepEqual(inLanguage("fr", () => STAGES.map(stage => texte.statusName(stage, "stelle-sie"))),
    ["Mise de côté", "À postuler", "Envoyée", "Entretien", "Refus", "Réponse positive", "Écartée", "Retirée"]);
  assert.deepEqual(inLanguage("fr", () => STAGES.map(stage => texte.statusName(stage, "stelle-du"))),
    ["Mise de côté", "À postuler", "Envoyée", "Entretien", "Refus", "Réponse positive", "Écartée", "Retirée"]);
  assert.deepEqual(inLanguage("en", () => STAGES.map(stage => texte.statusName(stage, "stelle-sie"))),
    ["Saved", "To apply", "Applied", "Interview", "Rejection", "Offer", "Discarded", "Withdrawn"]);
  assert.equal(inLanguage("en", () => texte.statusName("Gespräch", "lehrstelle-du")), "Invitation");
});

test("a list row names its stage, next step, deadline and date in the app language", () => {
  const rejected = row(b("r", "Absage", { passung: 4.5 }));
  assert.deepEqual(inLanguage("fr", () => A.rowTexts(rejected, "stelle-sie")),
    { stand: "Refus", schritt: "–", bis: "–", erfasst: "01.11.2026", geaendert: "" });
  const waiting = row(b("w", "Beworben", { beworben_am: "2026-11-02", stand_geaendert_am: "2026-11-02" }));
  assert.deepEqual(inLanguage("en", () => A.rowTexts(waiting, "stelle-sie")),
    { stand: "Applied", schritt: "Wait for the reply", bis: "follow up from 16.11.2026", erfasst: "01.11.2026", geaendert: "02.11.2026" });
  const interview = row(b("g", "Gespräch"));
  assert.equal(inLanguage("fr", () => A.rowTexts(interview, "stelle-sie").bis), "à définir");
  assert.equal(inLanguage("en", () => A.rowTexts(interview, "lehrstelle-du").stand), "Invitation");
});

test("the column labels and the grade of a row come in the app language", () => {
  assert.deepEqual(inLanguage("fr", () => A.columnLabels()),
    { stand: "Statut", note: "Note", schritt: "Prochaine étape", bis: "Échéance", erfasst: "Ajoutée", geaendert: "Statut modifié" });
  assert.deepEqual(inLanguage("en", () => A.columnLabels()),
    { stand: "Status", note: "Grade", schritt: "Next step", bis: "Due", erfasst: "Added", geaendert: "Status changed" });
  assert.equal(inLanguage("fr", () => A.gradeLabel(4.5)), "Note 4.5 sur 6, correspond bien");
  assert.equal(inLanguage("en", () => A.gradeLabel(6)), "Grade 6 of 6, fits very well");
  assert.deepEqual(inLanguage("en", () => [A.gradeWord(4), A.gradeWord(3), A.noGrade()]), ["barely fits", "fits poorly", "no grade"]);
});

test("discarding the ticked ones asks, notes and ends in French", () => {
  assert.equal(inLanguage("fr", () => A.discardQuestion(PLAN)), `Écarter 3 candidatures${NBSP}?`);
  assert.deepEqual(inLanguage("fr", () => A.discardNotes(PLAN)),
    ["1 déjà envoyée sera retirée.", "1 terminée reste telle quelle."]);
  assert.deepEqual(inLanguage("fr", () => A.discardNotes({ Verworfen: [], "Zurückgezogen": ["c", "e"], kept: ["d", "f"] })),
    ["2 déjà envoyées seront retirées.", "2 terminées restent telles quelles."]);
  assert.equal(inLanguage("fr", () => A.discardDone(PLAN)), "2 candidatures écartées, 1 retirée.");
  assert.equal(inLanguage("fr", () => A.discardDone(ONE_EACH)), "1 candidature écartée, 1 retirée.");
  assert.equal(inLanguage("fr", () => A.discardDone({ Verworfen: [], "Zurückgezogen": ["c"], kept: [] })), "1 candidature retirée.");
  assert.deepEqual(inLanguage("fr", () => [0, 1, 3].map(A.selectionHint)),
    ["Cocher d'abord des candidatures.", "1 cochée", "3 cochées"]);
});

test("discarding the ticked ones asks, notes and ends in English", () => {
  assert.equal(inLanguage("en", () => A.discardQuestion(ONE_EACH)), "Discard 2 applications?");
  assert.deepEqual(inLanguage("en", () => A.discardNotes(PLAN)), ["1 already sent will be withdrawn.", "1 closed stays as it is."]);
  assert.equal(inLanguage("en", () => A.discardDone(PLAN)), "2 applications discarded, 1 withdrawn.");
  assert.equal(inLanguage("en", () => A.discardDone({ Verworfen: ["a"], "Zurückgezogen": [], kept: [] })), "1 application discarded.");
  assert.deepEqual(inLanguage("en", () => [0, 2].map(A.selectionHint)), ["Tick applications first.", "2 ticked"]);
});

test("a job advertised again is worded in the app language, with the first of a month as 1er", () => {
  const twice = { status: "Beworben", wieder_ausgeschrieben: [repost("2026-11-18"), repost("2026-12-01")] };
  assert.equal(inLanguage("fr", () => W.listPart(twice)), "republiée le 01.12.");
  assert.equal(inLanguage("en", () => W.listPart(twice)), "advertised again on 01.12.");
  assert.deepEqual(inLanguage("fr", () => W.applicationNotice(twice)), {
    title: "Annonce republiée", text: `Dernière parution le 1er${NBSP}décembre sur jobs.ch, 2 fois en tout.`,
    link: "https://www.jobs.ch/inserat/2026-12-01", linkText: "Ouvrir la nouvelle annonce" });
  assert.equal(inLanguage("en", () => W.applicationNotice(twice).text), `Last seen on 1${NBSP}December on jobs.ch, 2 times in all.`);
  const full = { wieder_ausgeschrieben: Array.from({ length: 20 }, (_, day) => repost(`2026-11-${String(day + 1).padStart(2, "0")}`)) };
  assert.equal(inLanguage("fr", () => W.applicationNotice(full).text),
    `Dernière parution le 20${NBSP}novembre sur jobs.ch, au moins 20 fois en tout.`);
  assert.equal(inLanguage("en", () => W.applicationNotice(full).text),
    `Last seen on 20${NBSP}November on jobs.ch, at least 20 times in all.`);
  assert.equal(inLanguage("en", () => W.applicationNotice({ wieder_ausgeschrieben: [repost("2026-11-18")] }).text),
    `On 18${NBSP}November this ad appeared again on jobs.ch.`);
  assert.equal(inLanguage("fr", () => W.long("2026-11-18")), `18${NBSP}novembre`);
});

test("the Stellen parts of a known job are worded in the app language", () => {
  const hit = { portal: "jobs.ch", zustand: "verworfen", wieder_ausgeschrieben: [repost("2026-11-18")],
    weitere: [repost("2026-11-10"), repost("2026-11-12"), repost("2026-11-11", "jobscout24")] };
  assert.deepEqual(inLanguage("fr", () => W.discardedLine(hit)).text, "Republiée le 18.11. L'offre reste écartée.");
  assert.deepEqual(inLanguage("en", () => W.otherPortals(hit).map(other => other.text)), ["Also on jobscout24"]);
  assert.deepEqual(inLanguage("fr", () => W.sameAds(hit)), { summary: "La même annonce 2 fois de plus sur jobs.ch", links: [
    { text: "Ouvrir l'annonce du 10.11.", link: "https://www.jobs.ch/inserat/2026-11-10" },
    { text: "Ouvrir l'annonce du 12.11.", link: "https://www.jobs.ch/inserat/2026-11-12" }] });
  assert.equal(inLanguage("en", () => W.SUSPECT_MARK), "maybe the same job");
  assert.equal(inLanguage("fr", () => W.runHint(RUN, () => "")),
    `L'app connaissait déjà 2 annonces de la dernière recherche, avec un nouveau lien${NBSP}: 2 écartées. Elles n'apparaissent pas sous Nouvelles.`);
  assert.equal(inLanguage("en", () => W.suspected({ vielleicht_dieselbe: { satz: "", bewerbungen: [{ id: "x", stelle: "Planer" }] } })
    .entries[0].text), "Open “Planer”");
});

test("German stays as it was", () => {
  assert.deepEqual(STAGES.map(stage => texte.statusName(stage, "stelle-sie")), STAGES);
  assert.deepEqual(A.rowTexts(row(b("g", "Gespräch")), "stelle-sie"), { stand: "Gespräch", schritt: "Termin fürs Gespräch eintragen",
    bis: "offen", erfasst: "01.11.2026", geaendert: "" });
  assert.equal(A.columnLabels().geaendert, "Stand geändert");
  assert.equal(A.discardQuestion(PLAN), "3 Bewerbungen verwerfen?");
  assert.deepEqual(A.discardNotes(PLAN), ["1 schon verschickte wird zurückgezogen.", "1 abgeschlossene bleibt, wie sie ist."]);
  assert.equal(A.discardDone(PLAN), "2 Bewerbungen verworfen, 1 zurückgezogen.");
  assert.equal(A.selectionHint(2), "2 angehakt");
  assert.equal(A.gradeLabel(4.5), "Note 4.5 von 6, passt gut");
  assert.equal(W.listPart({ status: "Beworben", wieder_ausgeschrieben: [repost("2026-11-18")] }), "wieder ausgeschrieben am 18.11.");
  assert.equal(W.long("2026-12-01"), "1. Dezember");
  assert.equal(W.SUSPECT_MARK, "vielleicht dieselbe Stelle");
  assert.equal(W.runHint(RUN, () => ""), "2 Inserate aus dem letzten Suchlauf kannte die App schon, mit neuem Link: 2 verworfene. Sie stehen nicht unter Neu.");
});
