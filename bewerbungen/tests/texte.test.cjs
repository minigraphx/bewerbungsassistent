// Text sets (MIN-369): every text that speaks to the person exists with Sie and with du, du is lower case.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const texte = require("../seiten/texte.js");

test("each set picks its form, an apprenticeship falls back to du", () => {
  assert.equal(texte.text("einrichtung.ordner.frage", "stelle-sie"), "Wo sollen Ihre Unterlagen liegen?");
  assert.equal(texte.text("einrichtung.ordner.frage", "stelle-du"), "Wo sollen deine Unterlagen liegen?");
  assert.equal(texte.text("einrichtung.ordner.frage", "lehrstelle-du"), "Wo sollen deine Unterlagen liegen?");
  assert.equal(texte.text("einrichtung.ki.aufgabe", "lehrstelle-du"), "Die KI schätzt Lehrstellen ein und entwirft Anschreiben.");
});

test("an unknown set is the default, an unknown key fails loudly", () => {
  assert.equal(texte.text("einrichtung.ki.code", "irgendwas"), texte.text("einrichtung.ki.code", "stelle-sie"));
  assert.throws(() => texte.text("gibt.es.nicht", "stelle-sie"), /Unbekannter Text/);
});

test("every entry has both forms, and they really differ in the address", () => {
  for (const [schluessel, eintrag] of Object.entries(texte.TEXTE)) {
    assert.ok(eintrag.sie && eintrag.du, `${schluessel}: Sie und du`);
    for (const form of ["du", "lehrstelle"].filter(f => eintrag[f])) {
      assert.doesNotMatch(eintrag[form], /\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b/, `${schluessel}.${form}: keine Sie-Form`);
      assert.doesNotMatch(eintrag[form], /[^.!?:]\s(Du|Dein|Deine|Deinem|Deinen|Deiner|Dir|Dich)\b/, `${schluessel}.${form}: du klein`);
    }
    assert.doesNotMatch(eintrag.sie, /\b(du|dein|deine|deinem|deinen|deiner|dir|dich)\b/i, `${schluessel}.sie: keine Du-Form`);
  }
});

test("values fill their places", () => {
  texte.TEXTE["test.wert"] = { sie: "Noch {anzahl} Schritte für Sie.", du: "Noch {anzahl} Schritte für dich." };
  assert.equal(texte.text("test.wert", "stelle-du", { anzahl: 3 }), "Noch 3 Schritte für dich.");
  delete texte.TEXTE["test.wert"];
});

test("for apprenticeships an interview reads as an invitation, the stored status stays", () => {
  assert.equal(texte.statusName("Gespräch", "lehrstelle-du"), "Einladung");
  assert.equal(texte.statusName("Gespräch", "stelle-du"), "Gespräch");
  assert.equal(texte.statusName("Absage", "lehrstelle-du"), "Absage");
});
