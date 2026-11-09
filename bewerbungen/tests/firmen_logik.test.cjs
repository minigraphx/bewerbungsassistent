// The page Firmen (G35, #188): states, numbers, filters and sorting, without a page. Invented companies only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/firmen-logik.js");

const HEUTE = "2026-11-09";

function firma(name, kununu = null, { treffer = [], bewerbungen = [] } = {}) {
  return { schluessel: name.toLowerCase().replace(/\W+/g, "-"), name, ort: "Bern", treffer, bewerbungen, kununu,
           suche: `https://www.kununu.com/ch/search?q=${encodeURIComponent(name)}` };
}

const gefunden = (wert, bewertungen, am = "2026-11-05") => ({ zustand: "gefunden", wert, bewertungen, geprueft_am: am });

test("the state follows what kununu said, with few reviews below 10", () => {
  assert.equal(logik.zustand(firma("Muster AG")), "ungeprueft");
  assert.equal(logik.zustand(firma("Muster AG", gefunden(3.8, 214))), "gefunden");
  assert.equal(logik.zustand(firma("Muster AG", gefunden(3.8, 10))), "gefunden");
  assert.equal(logik.zustand(firma("Muster AG", gefunden(4.6, 9))), "wenige");
  assert.equal(logik.zustand(firma("Muster AG", gefunden(4.6, 1))), "wenige");
  assert.equal(logik.zustand(firma("Muster AG", { zustand: "gefunden", bewertungen: 0 })), "keine");
  assert.equal(logik.zustand(firma("Muster AG", { zustand: "keine" })), "keine");
  for (const z of ["mehrere", "nicht_gefunden", "fehler", "zugeordnet"]) assert.equal(logik.zustand(firma("Muster AG", { zustand: z })), z);
});

test("a value checked more than 90 days ago is stale", () => {
  assert.equal(logik.veraltet(firma("Muster AG", gefunden(3.2, 57, "2026-08-11")), HEUTE), false);
  assert.equal(logik.veraltet(firma("Muster AG", gefunden(3.2, 57, "2026-08-10")), HEUTE), true);
  assert.equal(logik.veraltet(firma("Muster AG", { zustand: "nicht_gefunden", geprueft_am: "2026-01-01" }), HEUTE), false);
  assert.equal(logik.veraltet(firma("Muster AG"), HEUTE), false);
});

test("numbers are written as on the page", () => {
  assert.equal(logik.wert(3.8), "3.8");
  assert.equal(logik.wert(4), "4.0");
  assert.equal(logik.anzahl(1312), "1’312");
  assert.equal(logik.anzahl(214), "214");
  assert.equal(logik.bewertungen(1), "1 Bewertung");
  assert.equal(logik.bewertungen(1312), "1’312 Bewertungen");
  assert.equal(logik.prozent(78), "78 %");
  assert.equal(logik.datum("2026-11-05"), "05.11.2026");
  assert.equal(logik.seite({ seite: "de" }), "kununu.com/de");
  assert.equal(logik.seite({ seite: "ch" }), "kununu.com/ch");
});

test("the hits of a company read as a count with the new ones", () => {
  assert.equal(logik.trefferText([{ zustand: "neu" }, { zustand: "neu" }, { zustand: "uebernommen" }]), "3 Treffer, 2 neu");
  assert.equal(logik.trefferText([{ zustand: "verworfen" }]), "1 Treffer, verworfen");
  assert.equal(logik.trefferText([{ zustand: "uebernommen" }]), "1 Treffer");
  assert.equal(logik.trefferText([]), "");
});

const LISTE = [
  firma("Muster Industrie AG", gefunden(3.8, 214), { treffer: [{ zustand: "neu" }, { zustand: "neu" }, { zustand: "uebernommen" }] }),
  firma("Musterbank", gefunden(4.1, 1312), { treffer: [{ zustand: "neu" }], bewerbungen: [{ status: "Gespräch" }] }),
  firma("Beispiel Holding AG", { zustand: "mehrere" }, { treffer: [{ zustand: "neu" }, { zustand: "verworfen" }] }),
  firma("Probe Transport AG", gefunden(4.6, 3), { treffer: [{ zustand: "neu" }] }),
  firma("Testlogistik GmbH", { zustand: "nicht_gefunden" }, { treffer: [{ zustand: "uebernommen" }] }),
  firma("Beispiel Versicherung", { zustand: "fehler" }, { bewerbungen: [{ status: "Beworben" }] }),
  firma("Muster Informatik AG", null, { bewerbungen: [{ status: "Bewerben" }] }),
  firma("Kleinwerk Muster GmbH", { zustand: "keine" }, { treffer: [{ zustand: "neu" }] }),
  firma("Probe Medizintechnik AG", gefunden(3.5, 41), { treffer: [{ zustand: "verworfen" }], bewerbungen: [{ status: "Absage" }] }),
];
const namen = firmen => firmen.map(f => f.name);

test("the filters: new hits, an open application, to settle", () => {
  assert.deepEqual(logik.zaehlen(LISTE), { alle: 9, neu: 5, bewerbung: 3, klaeren: 3 });
  assert.deepEqual(namen(logik.gefiltert(LISTE, "klaeren")), ["Beispiel Holding AG", "Testlogistik GmbH", "Beispiel Versicherung"]);
  assert.ok(!namen(logik.gefiltert(LISTE, "bewerbung")).includes("Probe Medizintechnik AG"));  // only under „Alle“
  assert.ok(!namen(logik.gefiltert(LISTE, "neu")).includes("Probe Medizintechnik AG"));
  assert.equal(logik.gefiltert(LISTE, "unbekannt").length, LISTE.length);
});

test("the search finds a company by part of its name in any case", () => {
  assert.deepEqual(namen(logik.gefiltert(LISTE, "alle", "  musterB ")), ["Musterbank"]);
  assert.deepEqual(namen(logik.gefiltert(LISTE, "neu", "probe")), ["Probe Transport AG"]);
  assert.deepEqual(logik.gefiltert(LISTE, "alle", "Gibt es nicht"), []);
});

test("by default the companies with new hits and the most links come first, not the best kununu value", () => {
  assert.deepEqual(namen(logik.sortiert(LISTE)).slice(0, 2), ["Muster Industrie AG", "Beispiel Holding AG"]);
  assert.deepEqual(logik.STANDARD_SORTIERUNG, { spalte: "verknuepft", richtung: "absteigend" });
});

test("by kununu few reviews come after the others and those without a value stay below in both directions", () => {
  const ab = namen(logik.sortiert(LISTE, { spalte: "kununu", richtung: "absteigend" }));
  assert.deepEqual(ab, ["Musterbank", "Muster Industrie AG", "Probe Medizintechnik AG", "Probe Transport AG", "Kleinwerk Muster GmbH",
                        "Beispiel Holding AG", "Testlogistik GmbH", "Beispiel Versicherung", "Muster Informatik AG"]);
  const auf = namen(logik.sortiert(LISTE, { spalte: "kununu", richtung: "aufsteigend" }));
  assert.deepEqual(auf.slice(0, 4), ["Probe Medizintechnik AG", "Muster Industrie AG", "Musterbank", "Probe Transport AG"]);
  assert.deepEqual(auf.slice(4), ab.slice(4));
});

test("by name and by date checked", () => {
  assert.equal(namen(logik.sortiert(LISTE, { spalte: "firma", richtung: "aufsteigend" }))[0], "Beispiel Holding AG");
  const datiert = [firma("A AG", gefunden(3, 20, "2026-10-01")), firma("B AG", gefunden(3, 20, "2026-11-01")), firma("C AG")];
  assert.deepEqual(namen(logik.sortiert(datiert, { spalte: "geprueft", richtung: "absteigend" })), ["B AG", "A AG", "C AG"]);
});

test("a click on a header turns its direction, another header starts in its own", () => {
  assert.deepEqual(logik.naechsteSortierung(logik.STANDARD_SORTIERUNG, "verknuepft"), { spalte: "verknuepft", richtung: "aufsteigend" });
  assert.deepEqual(logik.naechsteSortierung(logik.STANDARD_SORTIERUNG, "firma"), { spalte: "firma", richtung: "aufsteigend" });
  assert.deepEqual(logik.naechsteSortierung(logik.STANDARD_SORTIERUNG, "kununu"), { spalte: "kununu", richtung: "absteigend" });
  assert.deepEqual(logik.gueltigeSortierung({ spalte: "note" }), logik.STANDARD_SORTIERUNG);
});

test("checking opens the assigned page, else the search on kununu.com/ch", () => {
  assert.equal(logik.pruefenLink(firma("Muster AG", { zustand: "zugeordnet", link: "https://www.kununu.com/de/muster" })), "https://www.kununu.com/de/muster");
  assert.equal(logik.pruefenLink(firma("Muster & Co")), "https://www.kununu.com/ch/search?q=Muster%20%26%20Co");
});

test("the line under the title counts the companies found and the last check", () => {
  assert.deepEqual(logik.zusammenfassung(LISTE), { anzahl: 9, gefunden: 5, zuletzt: "2026-11-05" });
  assert.deepEqual(logik.zusammenfassung([]), { anzahl: 0, gefunden: 0, zuletzt: "" });
});
