// The overview (MIN-369): next step per application, the views by stage (#165), what comes first, without a page.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/uebersicht-logik.js");

const NO_CV = "Lebenslauf-PDF fehlt: öffnen und „Unterlagen erstellen“ oder unter „Meine Dateien“ hochladen";
const NO_LINK = "Kein Link zum Formular: öffnen und Link eintragen";
const b = (id, status, felder = {}) => ({ id, firma: `Firma ${id}`, stelle: `Stelle ${id}`, status, eingetragen_am: "2026-11-01", ...felder });

test("the next step follows the status and what the app knows", () => {
  const schritt = (eintrag, gruende = {}) => logik.naechsterSchritt(eintrag, gruende).art;
  assert.equal(schritt(b("a", "Gemerkt")), "entscheiden");
  assert.equal(schritt(b("a", "Bewerben"), { grund: null }), "abschicken");
  assert.equal(schritt(b("a", "Bewerben"), { grund: NO_CV }), "unterlagen");
  assert.equal(schritt(b("a", "Bewerben"), { grund: NO_LINK }), "link");
  assert.equal(schritt(b("a", "Bewerben"), { grund: "Anschreiben noch nicht freigegeben: öffnen, lesen und „Freigeben“" }), "freigeben");
  assert.equal(schritt(b("a", "Gespräch", { gespraech_am: "2026-11-11" })), "gespraech");
  assert.equal(schritt(b("a", "Beworben", { beworben_am: "2026-11-04" }), { ravGrund: null }), "rav");
  assert.equal(schritt(b("a", "Absage", { beworben_am: "2026-11-04" }), { ravGrund: null }), "rav");
  assert.equal(schritt(b("a", "Absage"), { ravGrund: "Schon im RAV eingetragen." }), "fertig");
  assert.equal(schritt(b("a", "Absage")), "fertig");
});

test("waiting for an answer says from when to ask, without RAV or once entered", () => {
  const schritt = logik.naechsterSchritt(b("a", "Beworben", { beworben_am: "2026-11-04" }), { ravGrund: "Schon im RAV eingetragen." });
  assert.deepEqual(schritt, { art: "warten", zusatz: "2026-11-18" });
  assert.equal(logik.datum(schritt.zusatz), "18.11.2026");
});

test("the list puts an interview first, then sending, the closest deadline first", () => {
  const zeilen = logik.mitSchritten([
    b("gemerkt", "Gemerkt"),
    b("spaet", "Bewerben", { frist: "2026-11-30" }),
    b("frueh", "Bewerben", { frist: "2026-11-20" }),
    b("gespraech", "Gespräch", { gespraech_am: "2026-11-11" }),
    b("warten", "Beworben", { beworben_am: "2026-11-02" }),
  ], new Map([["spaet", null], ["frueh", null], ["gemerkt", null]]));
  assert.deepEqual(zeilen.map(z => z.bewerbung.id), ["gespraech", "frueh", "spaet", "gemerkt", "warten"]);
});

test("the views follow the stage: Gemerkt, Beworben, Abgeschlossen and Alle", () => {
  const zeilen = logik.mitSchritten([
    b("g", "Gemerkt"), b("w", "Bewerben"), b("a", "Beworben"), b("s", "Gespräch", { gespraech_am: "2026-11-11" }),
    b("z", "Zusage"), b("r", "Absage"), b("v", "Verworfen"), b("x", "Zurückgezogen"),
  ]);
  const ids = ansicht => logik.gefiltert(zeilen, ansicht, "").map(z => z.bewerbung.id).sort();
  assert.deepEqual(ids("gemerkt"), ["g", "w"]);
  assert.deepEqual(ids("beworben"), ["a", "s"]);
  assert.deepEqual(ids("abgeschlossen"), ["r", "v", "x", "z"]);
  assert.deepEqual(ids("alle"), ["a", "g", "r", "s", "v", "w", "x", "z"]);
  assert.deepEqual(logik.gefiltert(zeilen, "alle", "firma z").map(z => z.bewerbung.id), ["z"]);
  assert.deepEqual(logik.ansichtenZaehlen(zeilen), { gemerkt: 2, beworben: 2, abgeschlossen: 4, alle: 8 });
});

test("a rejection is finished even while its Job-Room entry is open, which still shows under Das steht an", () => {
  const zeilen = logik.mitSchritten([b("a", "Beworben"), b("z", "Zusage"), b("r", "Absage", { beworben_am: "2026-11-02" })],
    new Map(), new Map([["r", null], ["a", "Schon im RAV eingetragen."]]));
  const ids = ansicht => logik.gefiltert(zeilen, ansicht, "").map(z => z.bewerbung.id).sort();
  assert.deepEqual(ids("beworben"), ["a"]);
  assert.deepEqual(ids("abgeschlossen"), ["r", "z"]);
  assert.deepEqual(logik.stehtAn(zeilen).map(e => [e.art, e.eintraege.map(z => z.bewerbung.id)]), [["rav", ["r"]]]);
});

test("the stored view is kept, the former Laufend becomes Beworben, anything else the default", () => {
  for (const ansicht of ["gemerkt", "beworben", "abgeschlossen", "alle"]) assert.equal(logik.gueltigeAnsicht(ansicht), ansicht);
  assert.equal(logik.gueltigeAnsicht("laufend"), "beworben");
  for (const falsch of [undefined, null, "", "quer", 3, {}]) assert.equal(logik.gueltigeAnsicht(falsch), logik.STANDARD_ANSICHT);
  assert.ok(logik.ANSICHTEN.includes(logik.STANDARD_ANSICHT));
  assert.deepEqual(logik.ANSICHTEN, ["gemerkt", "beworben", "abgeschlossen", "alle"]);
});

test("two or more ready ones become one item to open together, waiting ones never show", () => {
  const zeilen = logik.mitSchritten([
    b("x", "Bewerben"), b("y", "Bewerben"), b("g", "Gespräch", { gespraech_am: "2026-11-11" }),
    b("w", "Beworben"), b("m", "Gemerkt"),
  ], new Map([["x", null], ["y", null]]));
  const an = logik.stehtAn(zeilen);
  assert.deepEqual(an.map(e => [e.art, e.eintraege.map(z => z.bewerbung.id)]),
    [["gespraech", ["g"]], ["abschicken", ["x", "y"]], ["entscheiden", ["m"]]]);
});

test("finished ones are counted per status, also those still to enter in the Job-Room", () => {
  const zeilen = logik.mitSchritten([b("a", "Zusage"), b("b", "Absage"), b("c", "Absage"), b("d", "Beworben"), b("e", "Absage")],
    new Map(), new Map([["e", null]]));
  assert.deepEqual(logik.abgeschlossenZaehlen(zeilen), { Zusage: 1, Absage: 3 });
});

// Sorting the list by a column (MIN-404)

function reihe(...werte) {
  return werte.map(([stelle, status, passung, art, frist]) => ({ bewerbung: { stelle, status, passung }, schritt: { art, frist } }));
}
const SORTIERBAR = reihe(["Beta", "Beworben", 4.5, "warten", "2026-12-01"],
                         ["alpha", "Absage", undefined, "fertig", undefined],
                         ["Gamma", "Gemerkt", 5.5, "gespraech", "2026-11-10"]);
const stellen = zeilen => zeilen.map(z => z.bewerbung.stelle);

test("without a chosen column the list keeps the order of the app", () => {
  assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, null)), ["Beta", "alpha", "Gamma"]);
  assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, { spalte: "gibt-es-nicht", richtung: "auf" })), ["Beta", "alpha", "Gamma"]);
});

test("positions sort by the alphabet, ignoring case, in both directions", () => {
  assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, { spalte: "stelle", richtung: "auf" })), ["alpha", "Beta", "Gamma"]);
  assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, { spalte: "stelle", richtung: "ab" })), ["Gamma", "Beta", "alpha"]);
});

test("the status follows the course of an application, not the alphabet", () => {
  assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, { spalte: "stand", richtung: "auf" })), ["Gamma", "Beta", "alpha"]);
});

test("the next step sorts by what comes first", () => {
  assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, { spalte: "schritt", richtung: "auf" })), ["Gamma", "Beta", "alpha"]);
});

test("no grade and no date stay at the bottom in both directions", () => {
  for (const [spalte, auf, ab] of [["note", ["Beta", "Gamma", "alpha"], ["Gamma", "Beta", "alpha"]],
                                   ["frist", ["Gamma", "Beta", "alpha"], ["Beta", "Gamma", "alpha"]]]) {
    assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, { spalte, richtung: "auf" })), auf);
    assert.deepEqual(stellen(logik.sortiert(SORTIERBAR, { spalte, richtung: "ab" })), ab);
  }
});

test("equal values keep the order of the app, and the list itself stays as it is", () => {
  const gleich = reihe(["Zwei", "Beworben", 5, "warten"], ["Eins", "Beworben", 5, "warten"]);
  assert.deepEqual(stellen(logik.sortiert(gleich, { spalte: "note", richtung: "ab" })), ["Zwei", "Eins"]);
  logik.sortiert(SORTIERBAR, { spalte: "stelle", richtung: "auf" });
  assert.deepEqual(stellen(SORTIERBAR), ["Beta", "alpha", "Gamma"]);
});

test("clicks go first direction, other direction, back to the order of the app", () => {
  const erster = logik.naechsteSortierung(null, "frist");
  assert.deepEqual(erster, { spalte: "frist", richtung: "auf" });
  const zweiter = logik.naechsteSortierung(erster, "frist");
  assert.deepEqual(zweiter, { spalte: "frist", richtung: "ab" });
  assert.equal(logik.naechsteSortierung(zweiter, "frist"), null);
  assert.deepEqual(logik.naechsteSortierung(zweiter, "stelle"), { spalte: "stelle", richtung: "auf" });
});

test("the best grade comes first on the first click", () => {
  const erster = logik.naechsteSortierung(null, "note");
  assert.deepEqual(erster, { spalte: "note", richtung: "ab" });
  const zweiter = logik.naechsteSortierung(erster, "note");
  assert.deepEqual(zweiter, { spalte: "note", richtung: "auf" });
  assert.equal(logik.naechsteSortierung(zweiter, "note"), null);
});

test("a stored sorting only counts when it is one the page knows", () => {
  assert.deepEqual(logik.gueltigeSortierung({ spalte: "note", richtung: "ab" }), { spalte: "note", richtung: "ab" });
  for (const falsch of [null, "note", {}, { spalte: "note" }, { spalte: "x", richtung: "ab" }, { spalte: "note", richtung: "quer" }]) {
    assert.equal(logik.gueltigeSortierung(falsch), null);
  }
});

// Sorting by the date an application was entered (#168)

const ERFASST = [["Mitte", "2026-10-15"], ["Ohne", undefined], ["Neu", "2026-11-02"], ["Leer", ""], ["Alt", "2026-09-30"]]
  .map(([stelle, eingetragen_am]) => ({ bewerbung: { stelle, status: "Beworben", eingetragen_am }, schritt: { art: "warten" } }));

test("the entry date sorts both ways, entries without a date stay at the bottom", () => {
  assert.deepEqual(stellen(logik.sortiert(ERFASST, { spalte: "erfasst", richtung: "ab" })), ["Neu", "Mitte", "Alt", "Ohne", "Leer"]);
  assert.deepEqual(stellen(logik.sortiert(ERFASST, { spalte: "erfasst", richtung: "auf" })), ["Alt", "Mitte", "Neu", "Ohne", "Leer"]);
});

test("the newest entry comes first on the first click", () => {
  const erster = logik.naechsteSortierung(null, "erfasst");
  assert.deepEqual(erster, { spalte: "erfasst", richtung: "ab" });
  const zweiter = logik.naechsteSortierung(erster, "erfasst");
  assert.deepEqual(zweiter, { spalte: "erfasst", richtung: "auf" });
  assert.equal(logik.naechsteSortierung(zweiter, "erfasst"), null);
});

test("a stored sorting by the entry date is kept", () => {
  for (const richtung of ["auf", "ab"]) {
    assert.deepEqual(logik.gueltigeSortierung({ spalte: "erfasst", richtung }), { spalte: "erfasst", richtung });
  }
});

// Changing the stage of several applications at once (#170, G29)

const shownRows = ids => ids.map(id => ({ bewerbung: b(id, "Beworben"), schritt: { art: "warten" } }));

test("a checkbox adds a row to the selection or takes it out, without changing the old selection", () => {
  const before = new Set(["a"]);
  const added = logik.toggleOne(before, "b");
  assert.deepEqual([...added], ["a", "b"]);
  assert.deepEqual([...logik.toggleOne(added, "a")], ["b"]);
  assert.deepEqual([...before], ["a"]);
});

test("select all takes every row of the view, and once all are taken it clears them", () => {
  const rows = shownRows(["a", "b", "c"]);
  const all = logik.toggleAll(new Set(["a", "hidden"]), rows);
  assert.deepEqual([...all].sort(), ["a", "b", "c", "hidden"]);
  assert.deepEqual([...logik.toggleAll(all, rows)], ["hidden"]);
});

test("the state of select all only looks at the rows of the view", () => {
  const rows = shownRows(["a", "b"]);
  assert.equal(logik.selectionState(new Set(["hidden"]), rows), "none");
  assert.equal(logik.selectionState(new Set(["a", "hidden"]), rows), "some");
  assert.equal(logik.selectionState(new Set(["a", "b"]), rows), "all");
  assert.equal(logik.selectionState(new Set(), []), "none");
});

test("only the selected rows the view shows are changed, in the order of the list", () => {
  const rows = shownRows(["c", "a", "b"]);
  assert.deepEqual(logik.selectedIds(new Set(["a", "c", "hidden"]), rows), ["c", "a"]);
});

test("rows gone from the register leave the selection", () => {
  const rows = shownRows(["a"]);
  assert.deepEqual([...logik.keepKnown(new Set(["a", "gone"]), rows)], ["a"]);
});

test("the count of the selection is said in words", () => {
  assert.equal(logik.selectionLabel(0), "Keine ausgewählt");
  assert.equal(logik.selectionLabel(1), "1 ausgewählt");
  assert.equal(logik.selectionLabel(4), "4 ausgewählt");
});

test("the confirmation names how many applications change and to which stage", () => {
  assert.equal(logik.stageQuestion(1, "Absage"), "1 Bewerbung auf „Absage“ setzen?");
  assert.equal(logik.stageQuestion(3, "Zurückgezogen"), "3 Bewerbungen auf „Zurückgezogen“ setzen?");
});

test("each stage belongs to one view", () => {
  assert.equal(logik.viewOfStage("Gemerkt"), "gemerkt");
  assert.equal(logik.viewOfStage("Bewerben"), "gemerkt");
  assert.equal(logik.viewOfStage("Gespräch"), "beworben");
  assert.equal(logik.viewOfStage("Verworfen"), "abgeschlossen");
});

test("after the change the status line says where the rows went when they left the view", () => {
  assert.equal(logik.stageDone(2, "Absage", "Absage", "beworben"),
    "2 Bewerbungen auf „Absage“ gesetzt. Sie stehen jetzt unter „Abgeschlossen“.");
  assert.equal(logik.stageDone(1, "Gemerkt", "Gemerkt", "beworben"),
    "1 Bewerbung auf „Gemerkt“ gesetzt. Sie steht jetzt unter „Gemerkt“.");
  assert.equal(logik.stageDone(2, "Gespräch", "Einladung", "beworben"), "2 Bewerbungen auf „Einladung“ gesetzt.");
  assert.equal(logik.stageDone(2, "Absage", "Absage", "alle"), "2 Bewerbungen auf „Absage“ gesetzt.");
});
