// The overview (MIN-369): next step per application, running or finished, what comes first, without a page.
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

test("running and finished split the list, a finished one still to enter in the Job-Room stays running", () => {
  const zeilen = logik.mitSchritten([b("a", "Beworben"), b("z", "Zusage"), b("r", "Absage", { beworben_am: "2026-11-02" })],
    new Map(), new Map([["r", null], ["a", "Schon im RAV eingetragen."]]));
  const ids = ansicht => logik.gefiltert(zeilen, ansicht, "").map(z => z.bewerbung.id).sort();
  assert.deepEqual(ids("laufend"), ["a", "r"]);
  assert.deepEqual(ids("abgeschlossen"), ["z"]);
  assert.deepEqual(ids("alle"), ["a", "r", "z"]);
  assert.deepEqual(logik.gefiltert(zeilen, "alle", "firma z").map(z => z.bewerbung.id), ["z"]);
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

test("finished ones are counted per status, not those still to enter in the Job-Room", () => {
  const zeilen = logik.mitSchritten([b("a", "Zusage"), b("b", "Absage"), b("c", "Absage"), b("d", "Beworben"), b("e", "Absage")],
    new Map(), new Map([["e", null]]));
  assert.deepEqual(logik.abgeschlossenZaehlen(zeilen), { Zusage: 1, Absage: 2 });
});
