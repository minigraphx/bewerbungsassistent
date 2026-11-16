// Cut with one click or allow three pages (G92, #323), without a page: the rows, what is sent and what is said.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const K = require("../seiten/kuerzen-logik.js");
const texte = require("../seiten/texte.js");

const kuerzen = {
  zeilen: 7,
  optionen: [
    { id: "stichpunkte:a", text: "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)" },
    { id: "abschnitt:interests", text: "Abschnitt «Interessen»" },
  ],
  drei_seiten: true,
};

test("the first cut is preselected, the others are not", () => {
  assert.deepEqual(K.rows(kuerzen).map(row => [row.id, row.text, row.checked]), [
    ["stichpunkte:a", "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)", true],
    ["abschnitt:interests", "Abschnitt «Interessen»", false],
  ]);
});

test("the main button comes first, «Drei Seiten erlauben» only where it is offered, and there is no «So lassen»", () => {
  assert.deepEqual(K.buttons(kuerzen).map(b => [b.action, b.text, b.primary]),
    [["kuerzen", "Gekürzt neu erstellen", true], ["drei-seiten", "Drei Seiten erlauben", false]]);
  assert.deepEqual(K.buttons({ ...kuerzen, drei_seiten: false }).map(b => b.action), ["kuerzen"]);
  assert.deepEqual(K.buttons({ ...kuerzen, optionen: [] }).map(b => b.action), ["drei-seiten"]);
  const words = JSON.stringify([K.buttons(kuerzen), K.LEGEND]);
  assert.doesNotMatch(words, /So lassen/);
});

test("what is sent: the ticked cuts, or three pages", () => {
  assert.deepEqual(K.body("a-1", "kuerzen", ["stichpunkte:a"]), { id: "a-1", weglassen: ["stichpunkte:a"] });
  assert.deepEqual(K.body("a-1", "drei-seiten", ["stichpunkte:a"]), { id: "a-1", drei_seiten: true });
  assert.equal(K.body("a-1", "kuerzen", []), null, "nothing ticked sends nothing");
});

test("the note says that Meine Angaben and variants stay and where cuts come back, in both forms", () => {
  assert.equal(texte.text("kuerzen.hinweis", "stelle-sie"),
    "Meine Angaben und Varianten bleiben, wie sie sind. Weggelassenes holen Sie im Schritt Lebenslauf zurück.");
  assert.equal(texte.text("kuerzen.hinweis", "stelle-du"),
    "Meine Angaben und Varianten bleiben, wie sie sind. Weggelassenes holst du im Schritt Lebenslauf zurück.");
});

const page = name => fs.readFileSync(path.join(__dirname, "..", "seiten", name), "utf8");

test("the next step for a CV over its limit names the choice, not «So lassen»", () => {
  assert.equal(texte.text("bewerbung.kuerzen", "stelle-sie"), "Der Lebenslauf ist zu lang, auch enger gesetzt. "
    + "Wählen Sie unter «Unterlagen erstellen und prüfen», was für diese Bewerbung wegfällt, oder erlauben Sie drei Seiten.");
  for (const satz of ["stelle-du", "lehrstelle-du"]) {
    assert.equal(texte.text("bewerbung.kuerzen", satz), "Der Lebenslauf ist zu lang, auch enger gesetzt. "
      + "Wähle unter «Unterlagen erstellen und prüfen», was für diese Bewerbung wegfällt, oder erlaube drei Seiten.");
  }
  assert.match(page("bewerbung.js"), /kuerzen: \[K\.NEXT_TITLE, t\("bewerbung\.kuerzen"\)/);
});

test("«Zur Prüfung» on the card scrolls to the check and puts the focus on the first finding", () => {
  const source = page("bewerbung.js");
  assert.match(source, /kuerzen: \[K\.NEXT_TITLE, t\("bewerbung\.kuerzen"\), \[knopf\("Zur Prüfung", zuBefund\)\]\]/);
  assert.match(source, /const zuBefund = \(\) => \{\s*zuAbschnitt\("s-pruefen"\)\(\);\s*S\.focusFirstFinding\(\);/);
});

test("the cut finding has no close button and is named by its sentence alone", () => {
  const source = page("bewerbung.js");
  assert.match(source, /listenZeile\(document, [^;]*cut-finding[^;]*, zeile\.stufe, \{ schliessbar: false \}\)/);
  assert.match(source, /setAttribute\("aria-labelledby", K\.SENTENCE_ID\)/);
});

test("what is left out sits after the buttons of the step Lebenslauf", () => {
  const html = page("bewerbung.html");
  assert.ok(html.indexOf('id="cv-anpassen"') < html.indexOf('id="weggelassen"'));
  assert.ok(html.indexOf('id="weggelassen"') < html.indexOf('id="cv-erstellen"'));
});

test("what is left out is listed with «Zurückholen»; three pages is a line of its own with «Zurücknehmen»", () => {
  const kuerzungen = { weggelassen: [{ id: "stichpunkte:a", text: "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)" }], drei_seiten: true };
  assert.deepEqual(K.leftOut(kuerzungen).map(r => [r.id, r.text, r.button]), [
    ["stichpunkte:a", "3 Stichpunkte bei «Leiterin, Muster AG» (2015–2018)", "Zurückholen"],
  ]);
  assert.deepEqual(K.threePages(kuerzungen),
    { id: "drei-seiten", text: "Drei Seiten erlaubt, nur für diese Bewerbung.", button: "Zurücknehmen" });
  assert.equal(K.threePages({ weggelassen: [], drei_seiten: false }), null);
  assert.deepEqual(K.leftOut({ weggelassen: [], drei_seiten: false }), []);
  assert.deepEqual(K.leftOut(undefined), []);
  assert.equal(K.threePages(undefined), null);
});

test("the message after building anew says what happened", () => {
  assert.equal(K.doneMessage("kuerzen", { neu_erstellt: true }, false), "Gekürzt und neu erstellt.");
  assert.equal(K.doneMessage("drei-seiten", { neu_erstellt: true }, false), "Drei Seiten erlaubt und neu erstellt.");
  assert.equal(K.doneMessage("zurueck", { neu_erstellt: true }, true), "Zurückgeholt und neu erstellt.");
  assert.equal(K.doneMessage("kuerzen", { neu_erstellt: false, fehler: "Variante fehlt." }, true),
    "Gespeichert, aber nicht neu erstellt: Variante fehlt.");
  assert.equal(K.doneLevel("kuerzen", { neu_erstellt: true }, false), "ok");
  assert.equal(K.doneLevel("kuerzen", { neu_erstellt: false }, false), "hinweis");
});

test("a cut that was not enough says so and that the next cut is ticked", () => {
  assert.equal(K.doneMessage("kuerzen", { neu_erstellt: true }, true),
    "Gekürzt und neu erstellt. Der Lebenslauf ist noch zu lang; die nächste Kürzung ist angehakt.");
  assert.equal(K.doneLevel("kuerzen", { neu_erstellt: true }, true), "hinweis");
  assert.equal(K.doneMessage("drei-seiten", { neu_erstellt: true }, true), "Drei Seiten erlaubt und neu erstellt.");
  assert.equal(K.stillOver([{ text: "Lebenslauf: Text extrahierbar" }, { text: "Lebenslauf: 3 Seiten", kuerzen: kuerzen }]), true);
  assert.equal(K.stillOver([{ text: "Lebenslauf: Text extrahierbar" }]), false);
  assert.equal(K.stillOver(undefined), false);
});

test("the approval line is written only when its text changes", () => {
  assert.match(page("bewerbung.js"), /zeigeNeu\(\$\("freigabe-status"\)/);
});
