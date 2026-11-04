// Rating hits in packages (MIN-372): choosing, buttons and the run, without a page.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const logik = require("../seiten/treffer-logik.js");

test("only new hits with a text and without a rating are rated, the newest first", () => {
  const found = logik.zuBewerten([
    { id: "alt", zustand: "neu", gefunden_am: "2026-11-01" },
    { id: "jung", zustand: "neu", gefunden_am: "2026-11-04" },
    { id: "bewertet", zustand: "neu", bewertung: { note: 4 } },
    { id: "weg", zustand: "verworfen" },
    { id: "ohne", zustand: "neu", ohne_text: true },
  ]);
  assert.deepEqual(found.map((t) => t.id), ["jung", "alt"]);
});

test("the buttons follow the number of open hits", () => {
  assert.deepEqual(logik.knoepfe(0, 10, 30), []);
  assert.deepEqual(logik.knoepfe(1, 10, 30), [{ text: "Bewerten (1)", anzahl: 1 }]);
  assert.deepEqual(logik.knoepfe(10, 10, 30), [{ text: "Bewerten (10)", anzahl: 10 }]);
  assert.deepEqual(logik.knoepfe(11, 10, 30), [{ text: "Nächste 10 bewerten", anzahl: 10 }, { text: "Alle bewerten (11)", anzahl: 11 }]);
  assert.deepEqual(logik.knoepfe(30, 10, 30)[1], { text: "Alle bewerten (30)", anzahl: 30 });
  assert.deepEqual(logik.knoepfe(31, 10, 30)[1], { text: "Nächste 30 bewerten", anzahl: 30 });
});

test("own stars come before the grade", () => {
  const hits = [
    { id: "a", beruf: "Koch", bewertung: { note: 6 } },
    { id: "b", beruf: "Pflege", bewertung: { note: 3 } },
    { id: "c", beruf: "Pflege", bewertung: { note: 5 } },
    { id: "d", bewertung: { note: 5.5 } },
  ];
  assert.deepEqual(logik.sortiert(hits, { Pflege: 5, Koch: 2 }).map((t) => t.id), ["c", "b", "a", "d"]);
  assert.deepEqual(logik.sortiert(hits, {}).map((t) => t.id), ["a", "d", "c", "b"]);
  assert.equal(hits[0].id, "a");
});

const mittel = (sende, angehalten = () => false) => {
  const gesehen = [];
  return { gesehen, paket: 2, sende, angehalten, fortschritt: (stand) => gesehen.push(stand.bewertet) };
};
const alles = (ids) => ({ bewertet: ids.map((id) => ({ id })), offen: [], kosten_usd: 0.01 * ids.length });

test("ids go out in packages and progress is reported", async () => {
  const calls = [];
  const m = mittel(async (ids) => { calls.push(ids); return alles(ids); });
  const stand = await logik.bewerteAlle(["a", "b", "c"], m);
  assert.deepEqual(calls, [["a", "b"], ["c"]]);
  assert.deepEqual(m.gesehen, [2, 3]);
  assert.equal(stand.bewertet, 3);
  assert.ok(Math.abs(stand.kosten - 0.03) < 1e-9);
});

test("hits a package did not rate are tried once on their own, then they stay open", async () => {
  const calls = [];
  const m = mittel(async (ids) => {
    calls.push(ids);
    if (ids.length > 1) return { bewertet: [{ id: ids[0] }], offen: [ids[1]] };
    return { bewertet: [], offen: ids };
  });
  const stand = await logik.bewerteAlle(["a", "b"], m);
  assert.deepEqual(calls, [["a", "b"], ["b"]]);
  assert.deepEqual(stand.offen, ["b"]);
  assert.equal(stand.bewertet, 1);
  assert.equal(stand.fehler, "");
});

test("an error of access or budget ends the run and keeps what was rated", async () => {
  let call = 0;
  const m = mittel(async (ids) => {
    call += 1;
    if (call === 2) throw new Error("Budget aufgebraucht");
    return alles(ids);
  });
  const stand = await logik.bewerteAlle(["a", "b", "c", "d", "e"], m);
  assert.equal(call, 2);
  assert.equal(stand.bewertet, 2);
  assert.equal(stand.fehler, "Budget aufgebraucht");
});

test("stopping ends the run after the running package", async () => {
  let sent = 0;
  const m = mittel(async (ids) => { sent += 1; return alles(ids); }, () => sent >= 1);
  const stand = await logik.bewerteAlle(["a", "b", "c"], m);
  assert.equal(sent, 1);
  assert.equal(stand.gestoppt, true);
});

test("the cost per hit comes from the ratings so far", () => {
  assert.equal(logik.kostenProTreffer([{ bewertung: {} }, {}]), null);
  assert.equal(logik.kostenProTreffer([{ bewertung: { kosten_usd: 0.02 } }, { bewertung: { kosten_usd: 0.04 } }]), 0.03);
});

test("all rated only when every new hit has a grade", () => {
  const rated = { zustand: "neu", bewertung: { note: 4 } };
  assert.equal(logik.alleBewertet([rated]), true);
  assert.equal(logik.alleBewertet([rated, { zustand: "neu", ohne_text: true }]), false);
  assert.equal(logik.alleBewertet([{ zustand: "verworfen" }]), false);
  assert.equal(logik.alleBewertet([]), false);
});

test("the search button names what is searched", () => {
  assert.equal(logik.sucheText(["schnupperlehre"]), "Schnupperlehren suchen");
  assert.equal(logik.sucheText(["lehrstelle", "schnupperlehre"]), "Lehrstellen und Schnupperlehren suchen");
  assert.equal(logik.sucheText(["lehrstelle"]), "Lehrstellen suchen");
  assert.equal(logik.sucheText([]), "Lehrstellen suchen");
});

test("the wish on the page comes from the offers", () => {
  assert.equal(logik.wahlAus(["schnupperlehre"]), "schnupperlehre");
  assert.equal(logik.wahlAus(["lehrstelle", "schnupperlehre"]), "beides");
  assert.equal(logik.wahlAus(["lehrstelle"]), "lehrstelle");
});

test("the filter by kind appears when both kinds are there and keeps hits without a kind with apprenticeships", () => {
  const hits = [{ id: "a", art: "Lehrstelle" }, { id: "b", art: "Schnupperlehre" }, { id: "c" }];
  assert.equal(logik.beideArten(hits), true);
  assert.equal(logik.beideArten([hits[0], hits[2]]), false);
  assert.deepEqual(logik.nachArt(hits, "Schnupperlehre").map(t => t.id), ["b"]);
  assert.deepEqual(logik.nachArt(hits, "Lehrstelle").map(t => t.id), ["a", "c"]);
  assert.equal(logik.nachArt(hits, "").length, 3);
});

test("near the home comes before the rest, but not before the grade", () => {
  const hits = [
    { id: "far", gefunden_am: "2026-11-03" }, { id: "near", nah: true, gefunden_am: "2026-11-01" },
    { id: "rated", bewertung: { note: 5 }, gefunden_am: "2026-10-01" },
  ];
  assert.deepEqual(logik.sortiert(hits, {}).map((t) => t.id), ["rated", "near", "far"]);
});
