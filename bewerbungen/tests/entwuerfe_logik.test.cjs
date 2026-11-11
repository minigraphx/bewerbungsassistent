// Entwürfe und Versionen grouped by document (#120).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/entwuerfe-logik.js");

const version = (id, zeit) => ({ id, zeit, beschreibung: `Fassung ${id}`, datei: "cv.yaml" });
const gruppen = [
  { art: "lebenslauf", titel: "Lebenslauf", dokumente: [
    { datei: "cv.yaml", titel: "Lebenslauf", fassungen: [version("c", "2026-11-03"), version("b", "2026-11-02"), version("a", "2026-11-01")] },
    { datei: "jobs/daten.yaml", titel: "Lebenslauf-Zuschnitt daten", fassungen: [version("z", "2026-10-01")] },
  ] },
  { art: "anschreiben", titel: "Anschreiben", dokumente: [
    { datei: "bewerbungen/muster-ag/anschreiben.yaml", titel: "Anschreiben Muster AG", fassungen: [version("m", "2026-11-04")] },
  ] },
];

test("all groups show by default", () => {
  assert.deepEqual(logik.sichtbar(gruppen).map(g => g.art), ["lebenslauf", "anschreiben"]);
});

test("a filter keeps one kind of group", () => {
  assert.deepEqual(logik.sichtbar(gruppen, { art: "anschreiben" }).map(g => g.art), ["anschreiben"]);
});

test("a file from the link of an editor keeps only its document", () => {
  const shown = logik.sichtbar(gruppen, { datei: "jobs/daten.yaml" });
  assert.deepEqual(shown.map(g => g.dokumente.map(d => d.titel)), [["Lebenslauf-Zuschnitt daten"]]);
});

test("a file without drafts shows nothing", () => {
  assert.deepEqual(logik.sichtbar(gruppen, { datei: "suchprofil.md" }), []);
});

test("the filter counts documents per group", () => {
  assert.deepEqual(logik.filter(gruppen).map(f => [f.art, f.zahl]), [["alle", 3], ["lebenslauf", 2], ["anschreiben", 1]]);
});

test("the newest version shows and the older ones fold away", () => {
  const { neueste, aeltere } = logik.fassungen(gruppen[0].dokumente[0]);
  assert.equal(neueste.id, "c");
  assert.deepEqual(aeltere.map(v => v.id), ["b", "a"]);
  assert.equal(logik.aeltereTitel(aeltere), "Ältere Fassungen (2)");
});

test("a single version has nothing to fold", () => {
  const { neueste, aeltere } = logik.fassungen(gruppen[0].dokumente[1]);
  assert.equal(neueste.id, "z");
  assert.equal(logik.aeltereTitel(aeltere), null);
});

// Nur verwendete (#240): documents that went out with an application
const gesendet = (id, firma, datum) => ({ ...version(id, "2026-10-20"), versendet: [{ firma, datum }] });
const mitVersand = [
  { art: "lebenslauf", titel: "Lebenslauf", dokumente: [
    { datei: "cv.yaml", titel: "Lebenslauf", verwendet: true,
      fassungen: [version("c", "2026-11-03"), gesendet("b", "Beispiel AG", "2026-10-24"), version("a", "2026-10-01")] },
    { datei: "jobs/daten.yaml", titel: "Lebenslauf-Zuschnitt daten", verwendet: false, fassungen: [version("z", "2026-10-01")] },
  ] },
  { art: "suchprofil", titel: "Suchprofil", dokumente: [
    { datei: "suchprofil.md", titel: "Suchprofil", verwendet: false, fassungen: [version("s", "2026-10-02")] },
  ] },
];

test("only used hides documents never sent, and groups left empty", () => {
  const shown = logik.sichtbar(mitVersand, { nurVerwendet: true });
  assert.deepEqual(shown.map(g => g.dokumente.map(d => d.titel)), [["Lebenslauf"]]);
});

test("a used document keeps all its versions, older ones included", () => {
  const [cv] = logik.sichtbar(mitVersand, { nurVerwendet: true })[0].dokumente;
  assert.deepEqual(cv.fassungen.map(f => f.id), ["c", "b", "a"]);
});

test("only used combines with the type filter", () => {
  assert.deepEqual(logik.sichtbar(mitVersand, { art: "suchprofil", nurVerwendet: true }), []);
  assert.equal(logik.sichtbar(mitVersand, { art: "lebenslauf", nurVerwendet: true })[0].dokumente.length, 1);
});

test("without only used every document shows", () => {
  assert.equal(logik.sichtbar(mitVersand).flatMap(g => g.dokumente).length, 3);
});

test("the filter counts only used documents when only used is on", () => {
  assert.deepEqual(logik.filter(mitVersand, { nurVerwendet: true }).map(f => [f.art, f.zahl]),
    [["alle", 1], ["lebenslauf", 1], ["suchprofil", 0]]);
});

test("a sent version names the company and the date", () => {
  assert.equal(logik.versandText(gesendet("b", "Beispiel AG", "2026-10-24")), "versendet an Beispiel AG am 24.10.2026");
  assert.equal(logik.versandText(version("c", "2026-11-03")), null);
});

test("a version sent twice names both applications", () => {
  const zweimal = { ...version("b", "2026-10-20"), versendet: [{ firma: "Beispiel AG", datum: "2026-10-24" }, { firma: "Muster AG", datum: "2026-10-30" }] };
  assert.equal(logik.versandText(zweimal), "versendet an Beispiel AG am 24.10.2026 und an Muster AG am 30.10.2026");
});

test("a sending whose application is gone shows what was recorded", () => {
  const alt = { ...version("b", "2026-10-20"), versendet: [{ firma: null, datum: null, zweck: "Versand: Alt AG – Tester (01.02.2026)" }] };
  assert.equal(logik.versandText(alt), "versendet (Versand: Alt AG – Tester (01.02.2026))");
});

test("the choice is read back from what the page stored", () => {
  assert.equal(logik.gespeichert("1"), true);
  assert.equal(logik.gespeichert("0"), false);
  assert.equal(logik.gespeichert(null), false);
  assert.equal(logik.speicherwert(true), "1");
  assert.equal(logik.speicherwert(false), "0");
});

test("only used puts the sent versions on top and folds the others, newer ones included", () => {
  const cv = mitVersand[0].dokumente[0];
  const { oben, gefaltet, faltTitel } = logik.ansicht(cv, { nurVerwendet: true });
  assert.deepEqual(oben.map(f => f.id), ["b"]);
  assert.deepEqual(gefaltet.map(f => f.id), ["c", "a"]);
  assert.equal(faltTitel, "Nicht versendete Fassungen (2)");
});

test("without only used the newest is on top and the older ones fold as before", () => {
  const { oben, gefaltet, faltTitel } = logik.ansicht(mitVersand[0].dokumente[0]);
  assert.deepEqual(oben.map(f => f.id), ["c"]);
  assert.deepEqual(gefaltet.map(f => f.id), ["b", "a"]);
  assert.equal(faltTitel, "Ältere Fassungen (2)");
});

test("a document whose versions all went out has nothing to fold", () => {
  const alle = { datei: "x", titel: "X", verwendet: true, fassungen: [gesendet("y", "Muster AG", "2026-10-30"), gesendet("x", "Beispiel AG", "2026-10-24")] };
  const { oben, faltTitel } = logik.ansicht(alle, { nurVerwendet: true });
  assert.deepEqual(oben.map(f => f.id), ["y", "x"]);
  assert.equal(faltTitel, null);
});
