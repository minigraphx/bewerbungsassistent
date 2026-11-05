// What the form of an application sends: only what the person changed, so a page left open overwrites nothing (MIN-377).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { fehltAnschreiben, geaenderteFelder, notenHinweis } = require("../seiten/formular-logik.js");

test("only the fields the person changed go out", () => {
  const geladen = { id: "a-1", firma: "Muster AG", notiz: "alt", ort: "Bern" };

  assert.deepEqual(geaenderteFelder(geladen, { ...geladen, notiz: "neu" }), { notiz: "neu" });
});

test("a form shows numbers and missing values as text, and that is no change", () => {
  const geladen = { id: "a-1", passung: 3.5, rav_zuweisung: false };

  assert.deepEqual(geaenderteFelder(geladen, { id: "a-1", passung: "3.5", ort: "", notiz: "", rav_zuweisung: false }), {});
});

test("emptying a field counts as a change, and so does ticking a box", () => {
  const geladen = { id: "a-1", notiz: "alt" };

  assert.deepEqual(geaenderteFelder(geladen, { id: "a-1", notiz: "", rav_zuweisung: true }), { notiz: "", rav_zuweisung: true });
});

test("removing a tick counts as a change", () => {
  assert.deepEqual(geaenderteFelder({ id: "a-1", rav_zuweisung: true }, { id: "a-1", rav_zuweisung: false }), { rav_zuweisung: false });
});

const eintrag = (felder = {}) => ({ hat_anschreiben: false, eigenes_anschreiben: false, bewerbung: {}, ...felder });

test("a letter is only drafted when there is none at all", () => {
  assert.equal(fehltAnschreiben(eintrag()), true);
  assert.equal(fehltAnschreiben(eintrag({ hat_anschreiben: true })), false);
  assert.equal(fehltAnschreiben(eintrag({ eigenes_anschreiben: true })), false);
  assert.equal(fehltAnschreiben(eintrag({ bewerbung: { versand: { datum: "2026-11-05" } } })), false);
});

test("a new grade says how it compares to the one on record", () => {
  assert.equal(notenHinweis("", 3.5), "");
  assert.equal(notenHinweis("3.5", 3.5), "Das ist auch die eingetragene Note.");
  const anders = notenHinweis("4.5", 3.5);
  assert.match(anders, /Bisher eingetragen: Note 4\.5/);
  assert.match(anders, /abweichen/);
});
