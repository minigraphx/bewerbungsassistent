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
