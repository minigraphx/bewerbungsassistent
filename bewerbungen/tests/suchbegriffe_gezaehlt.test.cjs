// «Was die App gezählt hat» on /suchbegriffe (G108, #383), without DOM: the marks «ohne Ertrag» and «überlappend» in
// words, the table of all keywords, too few runs, the new kinds of change and what goes to the AI. All terms invented.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/suchbegriffe-logik.js");

const entry = fields => ({ begriff: "Lernbegleiter", suchen: 12, suchen_pro_lauf: 4, treffer_portale: 10, aussortiert: 0,
  treffer: 6, nur_hier: 6, ab_note_4: 2, laeufe_ohne_treffer: 0, marke: null, auch_ueber: null, alle_ueber: false, ...fields });
const AUTHOR = entry({ begriff: "E-Learning-Autor", suchen: 36, treffer_portale: 0, treffer: 0, nur_hier: 0, ab_note_4: 0, marke: "ohne_ertrag" });
const SCREENED = entry({ begriff: "E-Learning-Autor", suchen: 36, treffer_portale: 9, aussortiert: 9, treffer: 0, nur_hier: 0,
  ab_note_4: 0, marke: "ohne_ertrag" });
const NARROW = entry({ begriff: "Kursleiter Informatik", treffer: 14, nur_hier: 0, marke: "ueberlappend", auch_ueber: "Kursleiter", alle_ueber: true });
const SPREAD = entry({ begriff: "Kursleiter Informatik", treffer: 14, nur_hier: 0, marke: "ueberlappend", auch_ueber: "Kursleiter", alle_ueber: false });
const COUNTS = { laeufe: 3, noetig: 3, genug: true, begriffe: [entry({}), AUTHOR, NARROW] };

test("the caption says the app counted, not the AI", () => {
  assert.equal(L.GEZAEHLT_TITEL, "Was die App gezählt hat");
  assert.equal(L.gezaehltUnterzeile(COUNTS), "Aus den letzten 3 Suchläufen, gezählt von der App, nicht von der KI.");
});

test("only flagged keywords are listed, each with its mark and numbers", () => {
  assert.deepEqual(L.markiert(COUNTS), [
    { name: "„E-Learning-Autor“", marke: "ohne Ertrag", rest: ": 36 Suchen, kein Treffer." },
    { name: "„Kursleiter Informatik“", marke: "überlappend", rest: ": 14 Treffer, alle auch über „Kursleiter“." },
  ]);
});

test("titles the title filter screened out are named, and several covering terms by the most frequent", () => {
  assert.equal(L.markiert({ ...COUNTS, begriffe: [SCREENED] })[0].rest,
    ": 36 Suchen, kein Treffer in der Liste; 9 Titel hat der Titelfilter aussortiert.");
  assert.equal(L.markiert({ ...COUNTS, begriffe: [SPREAD] })[0].rest, ": 14 Treffer, alle auch über andere Begriffe, meist „Kursleiter“.");
  assert.equal(L.markiert({ ...COUNTS, begriffe: [{ ...NARROW, treffer: 1 }] })[0].rest, ": 1 Treffer, auch über „Kursleiter“.");
  assert.equal(L.markiert({ ...COUNTS, begriffe: [{ ...AUTHOR, suchen: 1 }] })[0].rest, ": 1 Suche, kein Treffer.");
});

test("with nothing flagged the section says so", () => {
  assert.deepEqual(L.markiert({ ...COUNTS, begriffe: [entry({})] }), []);
  assert.equal(L.NICHTS_MARKIERT, "Jeder Suchbegriff hat in den letzten 3 Suchläufen eigene Treffer gebracht.");
});

test("with too few runs there are no marks, only how many runs it needs", () => {
  const few = { laeufe: 1, noetig: 3, genug: false, begriffe: [entry({})] };
  assert.equal(L.zuWenigeLaeufe(few), "Für diese Zahlen braucht die App 3 Suchläufe seit Version 0.3.3, bisher sind es 1.");
  assert.equal(L.zuWenigeLaeufe({ ...few, laeufe: 0 }), "Für diese Zahlen braucht die App 3 Suchläufe seit Version 0.3.3, bisher gibt es noch keinen.");
  assert.equal(L.zuWenigeLaeufe(COUNTS), null);
  assert.deepEqual(L.markiert(few), []);
});

test("the table names every keyword with searches, hits, its own hits and those graded 4 or more", () => {
  assert.equal(L.TABELLE_TITEL, "Alle Suchbegriffe mit Zahlen");
  assert.deepEqual(L.TABELLE_SPALTEN, ["Begriff", "Suchen", "Treffer", "nur über diesen Begriff", "ab Note 4"]);
  assert.deepEqual(L.tabellenZeilen(COUNTS), [
    { begriff: "Lernbegleiter", marke: "", zahlen: [12, 6, 6, 2] },
    { begriff: "E-Learning-Autor", marke: "ohne Ertrag", zahlen: [36, 0, 0, 0] },
    { begriff: "Kursleiter Informatik", marke: "überlappend", zahlen: [12, 14, 0, 2] },
  ]);
});

test("a card names the mark of the keyword it concerns", () => {
  assert.equal(L.kartenMarke({ marke: "ueberlappend" }), "überlappend");
  assert.equal(L.kartenMarke({ marke: null }), "");
});

const NICHE = { nummer: 2, bereich: "keywords", art: "niche", verschoben: "Lernbegleiter", verschoben_wort: "zu den Nischen", entfaellt: [], neu: [] };
const LIMIT = { nummer: 3, bereich: "keywords", art: "portals", verschoben: "Kursleiter", verschoben_wort: "nur jobs.ch, job-room", entfaellt: [], neu: [] };
const START = { suchbegriffe: ["Kursleiter"], positiv: [], ausschluss: [], verschoben: ["Lernbegleiter", "Kursleiter"] };

test("moving to the niches or limiting to portals is one chip that switches the whole change", () => {
  const [chip] = L.chips(NICHE);
  assert.deepEqual(L.chips(NICHE), [{ bereich: "verschoben", begriff: "Lernbegleiter", art: "move", wort: "zu den Nischen" }]);
  assert.equal(L.chipAn(START, chip), true);
  assert.equal(L.chipWort(chip, true), "zu den Nischen");
  assert.equal(L.chipWort(L.chips(LIMIT)[0], true), "nur jobs.ch, job-room");
  const off = L.schalteKarte(START, NICHE, false);
  assert.deepEqual(off.verschoben, ["Kursleiter"]);
  assert.equal(L.chipWort(chip, false), "bleibt");
  assert.equal(L.karteStand(off, NICHE), "keine");
  assert.equal(L.karteStand(START, LIMIT), "alle");
});

test("«So sucht die App danach» shows the niches and the «Nur» lines", () => {
  const answer = { nischen: [{ begriff: "Lernatelier", neu: false }, { begriff: "Lernbegleiter", neu: true }],
    nur_zeilen: [{ portale: ["jobs.ch", "job-room"], begriffe: [{ begriff: "Kursleiter", neu: true }] }] };
  assert.deepEqual(L.endstandZeilen(answer), [
    { name: "Nischen (ohne Ort suchen)", begriffe: [{ begriff: "Lernatelier", neu: false }, { begriff: "Lernbegleiter", neu: true }] },
    { name: "Nur jobs.ch, job-room", begriffe: [{ begriff: "Kursleiter", neu: true }] },
  ]);
  assert.deepEqual(L.endstandZeilen({ nischen: [], nur_zeilen: [] }), []);
});

test("what goes to the AI names the counts and the screened-out titles, in Sie and du", () => {
  assert.equal(L.texte("stelle-sie").wasGeht, "An die KI gehen Ihr Suchprofil und Ihr Lebenslauf mit Platzhaltern für Name, "
    + "Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, Titel aussortierter Stellen und Zahlen zu jedem Suchbegriff, ohne Inseratstexte.");
  assert.equal(L.texte("stelle-du").wasGeht, "An die KI gehen dein Suchprofil und dein Lebenslauf mit Platzhaltern für Name, "
    + "Adresse und Kontakte sowie Titel und Note der eingeschätzten Treffer, Titel aussortierter Stellen und Zahlen zu jedem Suchbegriff, ohne Inseratstexte.");
});
