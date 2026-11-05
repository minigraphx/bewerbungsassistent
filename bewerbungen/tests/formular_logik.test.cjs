// What the form of an application sends: only what the person changed, so a page left open overwrites nothing (MIN-377).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { geaenderteFelder } = require("../seiten/formular-logik.js");

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
