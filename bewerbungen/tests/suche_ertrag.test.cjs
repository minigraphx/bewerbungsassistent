// What the search brings on Suche einstellen (G103, #375): the words of the yield per term and place, without DOM.
// Invented terms and places only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../seiten/suche-ertrag-logik.js");

const entry = (fields = {}) => ({ suchen: 36, treffer: 40, neu: 5, ab_note_4: 3, aussortiert: 12, ohne_ertrag: false, ...fields });

test("the yield line names searches, hits, new, good and screened out, the last only when there are some", () => {
  assert.deepEqual(L.teile(entry()), ["36 Suchen", "40 Treffer", "5 neu", "3 ab Note 4", "12 aussortiert"]);
  assert.deepEqual(L.teile(entry({ aussortiert: 0, neu: 0, ab_note_4: 0 })), ["36 Suchen", "40 Treffer", "0 neu", "0 ab Note 4"]);
  assert.deepEqual(L.teile(entry({ suchen: 1, treffer: 1, neu: 1, ab_note_4: 1, aussortiert: 1 })),
    ["1 Suche", "1 Treffer", "1 neu", "1 ab Note 4", "1 aussortiert"]);
});

test("a term that found nothing says so, with what the title filter screened out", () => {
  assert.deepEqual(L.teile(entry({ treffer: 0, neu: 0, ab_note_4: 0, aussortiert: 0 })), ["36 Suchen", "keine Treffer"]);
  assert.deepEqual(L.teile(entry({ treffer: 0, neu: 0, ab_note_4: 0, aussortiert: 9 })), ["36 Suchen", "keine Treffer", "9 aussortiert"]);
});

test("before the first run a term has no line", () => {
  assert.deepEqual(L.teile(entry({ suchen: 0, treffer: 0 }), 0), []);
  assert.deepEqual(L.teile(undefined), []);
});

test("once runs exist, a term no run has searched says so", () => {
  assert.deepEqual(L.teile(undefined, 2), ["noch nicht gesucht"]);
  assert.deepEqual(L.teile(entry({ suchen: 0, treffer: 0 }), 3), ["noch nicht gesucht"]);
  assert.deepEqual(L.teile(entry(), 3), ["36 Suchen", "40 Treffer", "5 neu", "3 ab Note 4", "12 aussortiert"]);
});

test("the places open with what their numbers come from and what «ohne Ort» means", () => {
  const rest = ", gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen.";
  assert.equal(L.ortHinweis(3), `Aus den letzten 3 Suchläufen${rest}`);
  assert.equal(L.ortHinweis(2), `Aus den letzten 2 Suchläufen${rest}`);
  assert.equal(L.ortHinweis(1), `Aus dem letzten Suchlauf${rest}`);
});

test("the caption says how many runs the numbers come from", () => {
  const rest = " Findet die Suche eine Stelle über mehrere Begriffe, zählt sie bei jedem. „Aussortiert“ heisst: Der Titelfilter hat den Titel nicht durchgelassen.";
  assert.equal(L.hinweis(3, false), `Die Zahlen stammen aus den letzten 3 Suchläufen.${rest}`);
  assert.equal(L.hinweis(2, false), `Die Zahlen stammen aus den letzten 2 Suchläufen.${rest}`);
  assert.equal(L.hinweis(1, false), `Die Zahlen stammen aus dem letzten Suchlauf.${rest}`);
  assert.equal(L.hinweis(0, false), "Nach dem nächsten Suchlauf steht hier bei jedem Begriff, was er bringt.");
});

test("for apprenticeships the caption speaks of professions and leaves out the title filter", () => {
  assert.equal(L.hinweis(3, true), "Die Zahlen stammen aus den letzten 3 Suchläufen. Findet die Suche eine Lehrstelle über mehrere Berufe, zählt sie bei jedem.");
  assert.equal(L.hinweis(0, true), "Nach dem nächsten Suchlauf steht hier bei jedem Beruf, was er bringt.");
});

test("hits from before the app kept the query are named once", () => {
  assert.equal(L.ohneAngabe(230, false), "Ohne Angabe: 230 Treffer aus Suchläufen vor Version 0.3.3. Über welchen Begriff sie kamen, hat die App damals nicht festgehalten.");
  assert.equal(L.ohneAngabe(1, true), "Ohne Angabe: 1 Treffer aus Suchläufen vor Version 0.3.3. Über welchen Beruf sie kamen, hat die App damals nicht festgehalten.");
  assert.equal(L.ohneAngabe(0, false), "");
});

test("the details on empty searches count them and name term, portal, searches and runs", () => {
  assert.equal(L.leerTitel(4, false), "Wo ein Begriff nichts findet (4)");
  assert.equal(L.leerTitel(1, true), "Wo ein Beruf nichts findet (1)");
  assert.equal(L.leerZeile({ begriff: "Lernbegleiter", portal: "ictjobs", suchen: 18, laeufe: 3 }),
    "„Lernbegleiter“ auf ictjobs: 18 Suchen in 3 Suchläufen, kein Treffer.");
  assert.equal(L.leerZeile({ begriff: "Kursleiter", portal: "jobs.ch", suchen: 1, laeufe: 1 }),
    "„Kursleiter“ auf jobs.ch: 1 Suche in 1 Suchlauf, kein Treffer.");
  assert.equal(L.leerZeile({ begriff: "Lernatelier", portal: "job-room", suchen: 3, laeufe: 3, nische: true }),
    "„Lernatelier“ (Nische) auf job-room: 3 Suchen in 3 Suchläufen, kein Treffer.");
});

test("a place is named the way its portal searches it", () => {
  assert.equal(L.ortName({ portal: "jobs.ch", ort: "Aarau", ort_name: "Aarau" }), "jobs.ch, Aarau");
  assert.equal(L.ortName({ portal: "jobscout24", ort: "5000", ort_name: "5000" }), "jobscout24, PLZ 5000");
  assert.equal(L.ortName({ portal: "ictjobs", ort: "aargau", ort_name: "Aargau" }), "ictjobs, Aargau");
  assert.equal(L.ortName({ portal: "job-room", ort: "AG, SO", ort_name: "AG, SO" }), "job-room, Kantone AG, SO");
  assert.equal(L.ortName({ portal: "job-room", ort: "AG", ort_name: "AG" }), "job-room, Kanton AG");
  assert.equal(L.ortName({ portal: "jobs.ch", ort: "", ort_name: "" }), "jobs.ch, ohne Ort");
});

test("the mark for a term or place without yield has its word", () => {
  assert.equal(L.OHNE_ERTRAG, "ohne Ertrag");
});

// Hits without a required word (G110, #386)

test("the yield line names hits without a required word at its end, only when there are some", () => {
  assert.deepEqual(L.teile(entry({ ohne_pflichtbezug: 18 })),
    ["36 Suchen", "40 Treffer", "5 neu", "3 ab Note 4", "12 aussortiert", "18 ohne Pflichtbezug"]);
  assert.deepEqual(L.teile(entry({ aussortiert: 0, ohne_pflichtbezug: 1 })),
    ["36 Suchen", "40 Treffer", "5 neu", "3 ab Note 4", "1 ohne Pflichtbezug"]);
  assert.deepEqual(L.teile(entry({ ohne_pflichtbezug: 0 })), ["36 Suchen", "40 Treffer", "5 neu", "3 ab Note 4", "12 aussortiert"]);
});

test("the details count the screened-out hits and name each term with up to three titles", () => {
  const entries = [{ begriff: "Berufsbildner", anzahl: 18,
    beispiele: ["Koch/Köchin EFZ – Berufsbildner/in", "Berufsbildner/in Logistik", "Detailhandel – Berufsbildner/in"] },
  { begriff: "Kursleiter", anzahl: 1, beispiele: ["Kursleiter Yoga"] }];
  assert.equal(L.pflichtTitel(entries), "Ohne Pflichtbezug aussortiert (19)");
  // hits over three runs, not postings counted once («Stellen» since #383)
  assert.equal(L.pflichtZeile(entries[0]), "„Berufsbildner“: 18 Treffer, zum Beispiel „Koch/Köchin EFZ – Berufsbildner/in“, "
    + "„Berufsbildner/in Logistik“, „Detailhandel – Berufsbildner/in“");
  assert.equal(L.pflichtZeile(entries[1]), "„Kursleiter“: 1 Treffer, „Kursleiter Yoga“");
  assert.equal(L.pflichtZeile({ begriff: "Kursleiter", anzahl: 2, beispiele: [] }), "„Kursleiter“: 2 Treffer");
});

test("the caption says what «ohne Pflichtbezug» means only when the reason occurs", () => {
  const rest = " Findet die Suche eine Stelle über mehrere Begriffe, zählt sie bei jedem. „Aussortiert“ heisst: Der Titelfilter hat den Titel nicht durchgelassen.";
  const pflicht = " „Ohne Pflichtbezug“: Titel und Inserat nennen keines der Pflichtwörter des Begriffs.";
  assert.equal(L.hinweis(3, false, true), `Die Zahlen stammen aus den letzten 3 Suchläufen.${rest}${pflicht}`);
  assert.equal(L.hinweis(3, false, false), `Die Zahlen stammen aus den letzten 3 Suchläufen.${rest}`);
  assert.equal(L.hinweis(3, true, true), "Die Zahlen stammen aus den letzten 3 Suchläufen. Findet die Suche eine Lehrstelle über mehrere Berufe, zählt sie bei jedem.");
});

test("Suche einstellen has the details on hits without a required word after the empty searches", () => {
  const html = require("node:fs").readFileSync(require("node:path").join(__dirname, "..", "seiten", "suche-einstellen.html"), "utf8");
  const empty = html.indexOf('<details id="ertrag-leer"');
  const unrelated = html.indexOf('<details id="ertrag-pflicht" class="ertrag-details" hidden><summary id="ertrag-pflicht-titel"></summary><ul id="ertrag-pflicht-liste" class="ertrag-liste"></ul></details>');
  assert.ok(empty > 0 && unrelated > empty, `${empty} ${unrelated}`);
});

test("the yield of a term is found by its name as the list shows it", () => {
  const ertrag = { begriffe: [{ begriff: "Lernbegleiter", suchen: 2 }, { begriff: "Kursleiter", suchen: 0 }] };
  assert.deepEqual(L.nachBegriff(ertrag).get("Lernbegleiter"), { begriff: "Lernbegleiter", suchen: 2 });
  assert.equal(L.nachBegriff(null).size, 0);
});
