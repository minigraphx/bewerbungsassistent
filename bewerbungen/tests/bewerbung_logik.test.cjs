// The application page (MIN-369): six steps and the next one, without a page.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/bewerbung-logik.js");

const daten = (bewerbung = {}, sonst = {}) => ({
  bewerbung: { id: "a", firma: "Muster AG", stelle: "Sachbearbeiterin", status: "Bewerben", eingetragen_am: "2026-11-03", ...bewerbung },
  stellentext: "Wir suchen …", pdfs: { lebenslauf: false, anschreiben: false }, varianten: [], hat_anschreiben: false, ...sonst,
});
const naechster = (d, o) => logik.naechster(d, o).art;
const stand = (d, o) => Object.fromEntries(logik.schritte(d, o).map(s => [s.id, s.erledigt]));

test("without the ad text the first step is the ad", () => {
  assert.equal(naechster(daten({}, { stellentext: "" })), "inserat");
});

test("with variants one must be chosen, without them the whole CV counts", () => {
  assert.equal(naechster(daten({}, { varianten: [{ id: "einkauf" }] })), "variante");
  assert.equal(stand(daten()).lebenslauf, true);
  assert.equal(logik.schritte(daten({ variante: "einkauf" }, { varianten: [{ id: "einkauf" }] }))[1].meta, "Variante einkauf");
});

test("a missing letter is drafted with the AI, else uploaded", () => {
  assert.equal(naechster(daten(), { ki: true }), "entwerfen");
  assert.equal(naechster(daten(), { ki: false }), "eigenes");
});

test("a draft is read and approved before anything else, an approval made void counts as none", () => {
  const offen = daten({}, { hat_anschreiben: true, anschreiben_freigabe: { noetig: true, freigegeben: false } });
  assert.equal(naechster(offen), "freigeben");
  assert.equal(logik.schritte(offen)[2].meta, "lesen und freigeben");
  const frei = daten({}, { hat_anschreiben: true, anschreiben_freigabe: { noetig: true, freigegeben: true } });
  assert.equal(naechster(frei), "erstellen");
  assert.equal(logik.schritte(frei)[2].meta, "freigegeben");
  const eigenes = daten({}, { hat_anschreiben: true, eigenes_anschreiben: true, anschreiben_freigabe: { noetig: false, freigegeben: false } });
  assert.equal(naechster(eigenes), "erstellen");
});

test("with a letter the PDFs come next, then the check, then its errors", () => {
  const mitBrief = daten({}, { hat_anschreiben: true });
  assert.equal(naechster(mitBrief), "erstellen");
  const gebaut = daten({ formular_link: "https://example.ch/bewerben" }, { hat_anschreiben: true, pdfs: { lebenslauf: true, anschreiben: true } });
  assert.equal(naechster(gebaut), "pruefen");
  assert.equal(naechster(gebaut, { befunde: [{ stufe: "fehler", text: "x" }] }), "klaeren");
  assert.equal(naechster(gebaut, { befunde: [{ stufe: "hinweis", text: "x" }] }), "formular");
  assert.equal(logik.schritte(gebaut, { befunde: [{ stufe: "hinweis" }, { stufe: "hinweis" }] })[3].meta, "2 Hinweise");
});

test("without a link sending is recorded by hand", () => {
  const bereit = daten({ link: "" }, { hat_anschreiben: true, pdfs: { lebenslauf: true, anschreiben: true } });
  assert.equal(naechster(bereit, { befunde: [] }), "versand");
});

test("after sending: the Job-Room with RAV, waiting without", () => {
  const gesendet = daten({ status: "Beworben", beworben_am: "2026-11-06", versand: { datum: "2026-11-06", art: "elektronisch" } });
  assert.equal(naechster(gesendet, { rav: true }), "jobroom");
  assert.equal(naechster(gesendet, { rav: false }), "warten");
  assert.equal(stand(gesendet, { rav: false }).festhalten, true);
  assert.equal(logik.schritte(gesendet)[4].meta, "am 06.11.2026");
  assert.equal(naechster({ ...gesendet, bewerbung: { ...gesendet.bewerbung, status: "Gespräch" } }), "gespraech");
  const termin = { ...gesendet, bewerbung: { ...gesendet.bewerbung, gespraech_am: "2026-11-20" } };
  assert.equal(naechster(termin, { rav: false }), "gespraech", "an interview date counts before the stage is changed (#268)");
  assert.equal(naechster(termin, { rav: true }), "jobroom");
});

test("the address decides who sends", () => {
  assert.equal(logik.schritte(daten(), { du: true })[4].meta, "machst du selbst");
  assert.equal(logik.schritte(daten())[4].meta, "machen Sie selbst");
});

test("the history lists the dates in order", () => {
  const b = { eingetragen_am: "2026-11-03", beworben_am: "2026-11-06", gespraech_am: "2026-11-11", versand: { datum: "2026-11-06", art: "elektronisch" } };
  assert.deepEqual(logik.verlauf(b).map(v => v.text), ["Erfasst", "Beworben", "Versand erfasst (elektronisch)", "Gespräch"]);
});

test("sent but not recorded: the sending is recorded afterwards, the steps before need nothing", () => {
  const nur = daten({ status: "Beworben", beworben_am: "2026-10-28" }, { stellentext: "" });
  assert.equal(naechster(nur), "nachtragen");
  assert.deepEqual(logik.schritte(nur).slice(0, 4).map(s => s.erledigt), [true, true, true, true]);
  assert.equal(logik.schritte(nur)[0].meta, "");
});

test("an application can be discarded before sending and withdrawn after, also past its deadline", () => {
  const pastDeadline = { firma: "Muster AG", stelle: "Sachbearbeiterin", frist: "2026-01-15" };
  const endFor = status => logik.beenden({ ...pastDeadline, status });
  for (const status of ["Gemerkt", "Bewerben"]) assert.equal(endFor(status).stand, "Verworfen");
  for (const status of ["Beworben", "Gespräch"]) assert.equal(endFor(status).stand, "Zurückgezogen");
  for (const status of ["Absage", "Zusage", "Verworfen", "Zurückgezogen"]) assert.equal(endFor(status), null);
});

// G52 (#237): a layout breach waits for the person before the application goes out
test("an unconfirmed layout breach keeps the check open, a confirmed one does not", () => {
  const gebaut = daten({}, { pdfs: { lebenslauf: true, anschreiben: true }, hat_anschreiben: true, anschreiben_freigabe: { noetig: true, freigegeben: true } });
  const offen = [{ stufe: "hinweis", text: "Lebenslauf, Seite 2: …", schluessel: "abc:fuellung:2", bestaetigt: false }];
  const bestaetigt = [{ ...offen[0], bestaetigt: true }];

  assert.equal(stand(gebaut, { befunde: offen }).pruefen, false);
  assert.equal(naechster(gebaut, { befunde: offen }), "bestaetigen");
  assert.equal(naechster(gebaut, { befunde: [...offen, { stufe: "fehler", text: "x" }] }), "klaeren");
  assert.equal(logik.schritte(gebaut, { befunde: offen })[3].meta, "1 Meldung bestätigen");
  assert.equal(stand(gebaut, { befunde: bestaetigt }).pruefen, true);
  assert.equal(logik.schritte(gebaut, { befunde: bestaetigt })[3].meta, "1 Hinweis");
});

test("a breach to confirm gets the button, a confirmed one says so and other findings stay as they are", () => {
  assert.deepEqual(logik.befundZeile({ stufe: "hinweis", text: "Lebenslauf, Seite 2: …", schluessel: "k", bestaetigt: false }),
    { text: "Lebenslauf, Seite 2: …", stufe: "hinweis", knopf: "So lassen" });
  assert.deepEqual(logik.befundZeile({ stufe: "hinweis", text: "Lebenslauf, Seite 2: …", schluessel: "k", bestaetigt: true }),
    { text: "Lebenslauf, Seite 2: … Bestätigt: so lassen.", stufe: "ok", knopf: null });
  assert.deepEqual(logik.befundZeile({ stufe: "fehler", text: "Firma fehlt" }), { text: "Firma fehlt", stufe: "fehler", knopf: null });
});

// G92 (#323): a CV over its limit is cut or allowed three pages, never confirmed with «So lassen»
const zuLang = {
  stufe: "hinweis", text: "Lebenslauf: 3 Seiten, erlaubt sind höchstens 2. Auch enger gesetzt sind es etwa 7 Zeilen zu viel.",
  schluessel: "abc:seiten:3", bestaetigt: false,
  kuerzen: { zeilen: 7, optionen: [{ id: "stichpunkte:a", text: "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)" }], drei_seiten: true },
};

test("a CV over its limit gets the cuts instead of «So lassen»", () => {
  const zeile = logik.befundZeile(zuLang);
  assert.equal(zeile.knopf, null);
  assert.equal(zeile.kuerzen, zuLang.kuerzen);
  assert.equal(zeile.stufe, "hinweis");
});

// G94 (#325): a letter over one page is cut in the letter or confirmed as it is, with its longest paragraph marked
const briefZuLang = {
  stufe: "fehler", text: "Anschreiben: 2 Seiten, erlaubt ist eine. Auch so eng wie möglich gesetzt sind es etwa 6 Zeilen zu viel.",
  schluessel: "abc:seiten:2", bestaetigt: false, letter_cut: { lines: 6, paragraph: 3, pages: 2 },
};

test("a letter over one page offers «Im Anschreiben kürzen» before «So lassen»", () => {
  assert.deepEqual(logik.befundZeile(briefZuLang),
    { text: briefZuLang.text, stufe: "fehler", knopf: "So lassen", cutInLetter: "Im Anschreiben kürzen" });
});

test("a letter left as it is stays a hint, so the line matches «1 Hinweis» of the step", () => {
  const bestaetigt = { ...briefZuLang, stufe: "hinweis", bestaetigt: true };
  assert.deepEqual(logik.befundZeile(bestaetigt),
    { text: "Anschreiben: 2 Seiten, etwa 6 Zeilen zu viel. Bestätigt: so lassen.", stufe: "hinweis", knopf: null });
  assert.equal(logik.befundZeile({ ...bestaetigt, letter_cut: { lines: 1, paragraph: 3, pages: 2 } }).text,
    "Anschreiben: 2 Seiten, etwa 1 Zeile zu viel. Bestätigt: so lassen.");
});

test("the longest paragraph is marked only while the letter is over one page and not confirmed", () => {
  assert.equal(logik.LONGEST_LABEL, "Längster Absatz");
  assert.equal(logik.longestParagraph([{ stufe: "ok", text: "x" }, briefZuLang]), 3);
  assert.equal(logik.longestParagraph([{ ...briefZuLang, bestaetigt: true }]), null);
  assert.equal(logik.longestParagraph([{ ...briefZuLang, letter_cut: { lines: 6, paragraph: null } }]), null);
  assert.equal(logik.longestParagraph(null), null);
});

test("with a CV over its limit the next step is to cut it, and the step says so", () => {
  const gebaut = daten({}, { pdfs: { lebenslauf: true, anschreiben: true }, hat_anschreiben: true, anschreiben_freigabe: { noetig: true, freigegeben: true } });
  const breach = { stufe: "hinweis", text: "Lebenslauf, Seite 2: …", schluessel: "abc:fuellung:2", bestaetigt: false };

  assert.equal(naechster(gebaut, { befunde: [zuLang] }), "kuerzen");
  assert.equal(naechster(gebaut, { befunde: [breach, zuLang] }), "kuerzen");
  assert.equal(naechster(gebaut, { befunde: [zuLang, { stufe: "fehler", text: "x" }] }), "klaeren");
  assert.equal(stand(gebaut, { befunde: [zuLang] }).pruefen, false);
  assert.equal(logik.schritte(gebaut, { befunde: [zuLang] })[3].meta, "Lebenslauf zu lang");
  assert.equal(logik.schritte(gebaut, { befunde: [breach, zuLang] })[3].meta, "Lebenslauf zu lang");
});
