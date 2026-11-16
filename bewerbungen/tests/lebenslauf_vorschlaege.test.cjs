// Suggestions of the AI in „Lebenslauf erstellen“ (#293, G75): applied on opening, each recommendation undone as a
// whole, the person's own changes stay. Without DOM; invented data.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/lebenslauf-erstellen-logik.js");
const Texte = require("../seiten/texte.js");
const Treffer = require("../seiten/treffer-logik.js");

const ANSWER = {
  stand: "abc", ki: "bereit", eigene_variante: null,
  abschnitte: [
    { abschnitt: "work", titel: "Berufserfahrung", stationen: [
      { index: 0, titel: "Entwicklerin", zusatz: "Beispiel AG", zeit: "2019 – heute", gewaehlt: true },
      { index: 1, titel: "Junior", zusatz: "Muster GmbH", zeit: "2015 – 2019", gewaehlt: true },
    ] },
    { abschnitt: "projects", titel: "Projekte", stationen: [
      { index: 0, titel: "datenatlas", zusatz: "", zeit: "", gewaehlt: true },
      { index: 1, titel: "kurs-tools", zusatz: "", zeit: "", gewaehlt: true },
      { index: 2, titel: "Spiel", zusatz: "", zeit: "", gewaehlt: true },
    ] },
  ],
  berufsbezeichnung: "Entwicklerin", kurzprofil: "Erster Satz. Zweiter Satz.", design: "zweispaltig", bezeichnung: "Daten",
};

const SUGGESTION = { empfehlungen: [
  { nummer: 0, was: "«Spiel» weglassen, «kurs-tools» nach vorne", grund: "Kurse passen.",
    weglassen: [{ abschnitt: "projects", index: 2 }], voran: [{ abschnitt: "projects", index: 1 }], kurzprofil: null },
  { nummer: 1, was: "«Junior, Muster GmbH» weglassen, Kurzprofil gekürzt", grund: "Keine Webstelle.",
    weglassen: [{ abschnitt: "work", index: 1 }], voran: [], kurzprofil: "Zweiter Satz." },
] };

const section = (state, name) => state.sections.find(part => part.name === name);
const texts = { berufsbezeichnung: "Entwicklerin", kurzprofil: "", bezeichnung: "Daten" };

test("the suggestion is applied as a whole: stations left out, moved up, and the shorter summary", () => {
  const state = L.suggest(L.start(ANSWER), SUGGESTION);
  assert.deepEqual(section(state, "projects").order, [1, 0, 2]);
  assert.deepEqual(section(state, "projects").chosen, [1, 0]);
  assert.deepEqual(section(state, "work").chosen, [0]);
  assert.equal(L.summary(state), "Zweiter Satz.");
  assert.deepEqual(state.recommendations.map(r => r.on), [true, true]);
  assert.deepEqual(L.request(state, { id: "b1", ...texts }).stationen, { work: [0], projects: [1, 0] });
});

test("undoing one recommendation brings back exactly its changes and keeps the others", () => {
  const applied = L.suggest(L.start(ANSWER), SUGGESTION);
  const undone = L.setRecommendation(applied, 0, false);
  assert.deepEqual(section(undone, "projects").order, [0, 1, 2]);
  assert.deepEqual(section(undone, "projects").chosen, [0, 1, 2]);
  assert.deepEqual(section(undone, "work").chosen, [0]);
  assert.equal(L.summary(undone), "Zweiter Satz.");
  assert.deepEqual(section(applied, "projects").chosen, [1, 0], "the state before stays");
  const summaryBack = L.setRecommendation(undone, 1, false);
  assert.equal(L.summary(summaryBack), "Erster Satz. Zweiter Satz.");
  assert.deepEqual(section(summaryBack, "work").chosen, [0, 1]);
  assert.deepEqual(section(L.setRecommendation(summaryBack, 0, true), "projects").order, [1, 0, 2]);
});

test("changes by hand stay when a recommendation is undone", () => {
  let state = L.suggest(L.start(ANSWER), SUGGESTION);
  state = L.toggle(state, "work", 0);
  state = L.move(state, "projects", 0, -1);
  assert.deepEqual(section(state, "projects").order, [0, 1, 2]);
  state = L.setRecommendation(state, 1, false);
  assert.deepEqual(section(state, "work").chosen, [1]);
  assert.deepEqual(section(state, "projects").order, [0, 1, 2]);
  assert.deepEqual(section(state, "projects").chosen, [0, 1]);
});

test("opening never asks the AI: the person sees text and cost first (G95, G15)", () => {
  assert.equal(L.autoSuggest(ANSWER), false);
  assert.equal(L.autoSuggest({ ...ANSWER, eigene_variante: "b1" }), false);
  assert.equal(L.autoSuggest({ ...ANSWER, ki: "aus" }), false);
  assert.equal(L.autoSuggest({ ...ANSWER, ki: "ohne_inserat" }), false);
});

test("without AI the state is the one of today and nothing is recommended", () => {
  const state = L.start({ ...ANSWER, ki: "aus" });
  assert.deepEqual(state.recommendations, []);
  assert.equal(L.summary(state), "Erster Satz. Zweiter Satz.");
  assert.deepEqual(L.request(state, { id: "b1", ...texts }).stationen, { work: [0, 1], projects: [0, 1, 2] });
});

test("what the page says about the suggestion and each undo", () => {
  assert.equal(L.suggestedText(SUGGESTION.empfehlungen.length), "Vorschlag der KI angewendet: 2 Empfehlungen.");
  assert.equal(L.suggestedText(1), "Vorschlag der KI angewendet: 1 Empfehlung.");
  assert.equal(L.suggestedText(0), "Die KI schlägt für diese Stelle nichts anderes vor.");
  const rec = SUGGESTION.empfehlungen[0];
  assert.equal(L.recommendationText(rec, false), "Zurückgenommen: «Spiel» weglassen, «kurs-tools» nach vorne.");
  assert.equal(L.recommendationText(rec, true), "Wieder angewendet: «Spiel» weglassen, «kurs-tools» nach vorne.");
});

test("the announcement names what the suggestion cost, and a repeat from the cache adds nothing", () => {
  assert.equal(L.suggestedText(2, "Berechnet: 0.01 CHF."), "Vorschlag der KI angewendet: 2 Empfehlungen. Berechnet: 0.01 CHF.");
  assert.equal(L.suggestedText(0, "Berechnet: 0.01 CHF."),
               "Die KI schlägt für diese Stelle nichts anderes vor. Berechnet: 0.01 CHF.");
  assert.equal(L.suggestedText(2, ""), "Vorschlag der KI angewendet: 2 Empfehlungen.");
});

test("what the box offers when nothing is applied on opening: a line and a button, both from texte.js", () => {
  assert.deepEqual(L.aiOffer({ ...ANSWER, ki: "aus" }),
                   { line: "lebenslauf.ki-aus", button: "lebenslauf.ki-einschalten", action: "einrichten" });
  assert.deepEqual(L.aiOffer({ ...ANSWER, ki: "ohne_inserat" }),
                   { line: "lebenslauf.ki-ohne-inserat", button: "lebenslauf.ki-zum-stellentext", action: "stellentext" });
  assert.deepEqual(L.aiOffer({ ...ANSWER, eigene_variante: "b1" }),
                   { line: "lebenslauf.ki-gespeichert", button: "lebenslauf.ki-neu", action: "vorschlagen" });
  assert.deepEqual(L.aiOffer(ANSWER), { line: "lebenslauf.ki-bereit", button: "lebenslauf.ki-holen", action: "vorschlagen" });
  assert.equal(L.APPLIED_LINE, "lebenslauf.ki-angewendet");
});

test("the box speaks to each text set, and an apprenticeship reads Lehrstelle", () => {
  const t = (key, satz) => Texte.text(key, satz);
  assert.equal(t("lebenslauf.ki-titel", "stelle-sie"), "Vorschläge der KI für diese Stelle");
  assert.equal(t("lebenslauf.ki-titel", "stelle-du"), "Vorschläge der KI für diese Stelle");
  assert.equal(t("lebenslauf.ki-titel", "lehrstelle-du"), "Vorschläge der KI für diese Lehrstelle");
  assert.equal(t("lebenslauf.ki-aus", "stelle-sie"),
               "Mit KI schlägt die App für diese Stelle Stationen, Reihenfolge und Kurzprofil vor.");
  assert.equal(t("lebenslauf.ki-aus", "lehrstelle-du"),
               "Mit KI schlägt die App für diese Lehrstelle Stationen, Reihenfolge und Kurzprofil vor.");
  for (const satz of Texte.SAETZE) {
    assert.equal(t("lebenslauf.ki-ohne-inserat", satz), "Für Vorschläge der KI fehlt noch der Stellentext.");
    assert.equal(t("lebenslauf.ki-zum-stellentext", satz), "Zum Stellentext");
    assert.equal(t("lebenslauf.ki-angewendet", satz),
                 "Schon angewendet. Ohne Häkchen gilt eine Empfehlung als Ganzes nicht mehr.");
    assert.equal(t("lebenslauf.ki-neu", satz), "Neu vorschlagen lassen");
    assert.equal(t("lebenslauf.ki-einschalten", satz), "KI einschalten");
  }
  assert.equal(t("lebenslauf.ki-gespeichert", "stelle-sie"),
               "Für diese Bewerbung ist Ihre Auswahl gespeichert. Die KI kann neu vorschlagen; gespeichert wird erst mit «Lebenslauf übernehmen».");
  assert.equal(t("lebenslauf.ki-gespeichert", "stelle-du"),
               "Für diese Bewerbung ist deine Auswahl gespeichert. Die KI kann neu vorschlagen; gespeichert wird erst mit «Lebenslauf übernehmen».");
  for (const satz of ["stelle-sie", "stelle-du"]) {
    assert.equal(t("lebenslauf.ki-bereit", satz), "Die KI kann für diese Stelle Stationen, Reihenfolge und Kurzprofil "
                 + "vorschlagen. Gespeichert wird erst mit «Lebenslauf übernehmen».");
  }
  assert.equal(t("lebenslauf.ki-bereit", "lehrstelle-du"), "Die KI kann für diese Lehrstelle Stationen, Reihenfolge und "
               + "Kurzprofil vorschlagen. Gespeichert wird erst mit «Lebenslauf übernehmen».");
  assert.equal(t("lebenslauf.ki-holen", "stelle-sie"), "Vorschläge holen");
  assert.equal(t("lebenslauf.ki-schaetzen", "stelle-sie"), "Kosten und Dauer werden geschätzt …");
  assert.equal(t("lebenslauf.ki-neu-schaetzen", "lehrstelle-du"), "Neu schätzen");
});

// What GET /api/lebenslauf/erstellen/schaetzung answers, worded by TrefferLogik.estimateLine (G95).
const OWN_KEY = { anzahl: 1, kosten: 0.03, waehrung: "USD", guthaben: null, danach: null, dauer_minuten: 1, reicht_fuer: null };
const CODE = { ...OWN_KEY, kosten: 0.04, waehrung: "CHF", guthaben: 4.25, danach: 4.21 };

test("the cost line before the click is the estimate line of Alle prüfen", () => {
  assert.deepEqual(Treffer.costLine(OWN_KEY), { text: "Etwa USD 0.03 und 1 Minute.", usedUp: false });
  assert.deepEqual(Treffer.costLine(CODE),
                   { text: "Etwa CHF 0.04 und 1 Minute. Danach bleiben CHF 4.21 im Guthaben.", usedUp: false });
});

test("over the credit the line says it may not be enough; the button stays usable", () => {
  assert.deepEqual(Treffer.costLine({ ...CODE, guthaben: 0.02, danach: 0 }), {
    text: "Etwa CHF 0.04 und 1 Minute. Im Guthaben sind noch CHF 0.02, das reicht vielleicht nicht.", usedUp: false });
});

test("with the credit used up the line says where to ask for a new code, and the button is locked", () => {
  assert.deepEqual(Treffer.costLine({ ...CODE, guthaben: 0, danach: 0 }), {
    text: "Etwa CHF 0.04 und 1 Minute. Das Guthaben ist aufgebraucht: neuen Code anfordern.", usedUp: true });
});

test("a failed estimate names its reason", () => {
  assert.equal(Treffer.estimateFailedText("Die App antwortet nicht."), "Die Schätzung fehlt: Die App antwortet nicht.");
});
