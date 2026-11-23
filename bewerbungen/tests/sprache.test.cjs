// Card «Sprache» under Einstellungen, KI, Budget und Sprache (G10, G12, #94, A10): the language of the app and the
// languages the person applies in, suggested from the CV until the person confirms them.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const logic = require("../seiten/sprache-logik.js");
const settings = require("../seiten/einstellungen-logik.js");
const Texte = require("../seiten/texte.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const card = html => {
  const start = html.indexOf('<section class="card" id="sprache"');
  assert.ok(start >= 0, "card sprache");
  return html.slice(start, html.indexOf("</section>", start));
};

const SUGGESTED = { app: "de", app_gewaehlt: false, bewerbung: ["de", "en"], bewerbung_gewaehlt: false,
                    vorschlag: [{ sprache: "de", stufe: "Muttersprache" }, { sprache: "en", stufe: "fliessend" }] };

test("the app is offered in German, French and English, each named in its own language", () => {
  assert.deepEqual(logic.APP_LANGUAGES.map(({ value, label, lang }) => [value, label, lang]),
    [["de", "Deutsch", "de"], ["fr", "Français", "fr"], ["en", "English", "en"]]);
});

test("the application languages follow the design's order, each suggested one with the CV's level", () => {
  const view = logic.view(SUGGESTED);

  assert.equal(view.app, "de");
  assert.deepEqual(view.options.map(({ value, checked, parts }) => [value, checked, parts]), [
    ["de", true, ["Deutsch", "vorgeschlagen: im Lebenslauf «Muttersprache»"]],
    ["en", true, ["Englisch", "vorgeschlagen: im Lebenslauf «fliessend»"]],
    ["fr", false, ["Französisch"]],
  ]);
  assert.equal(view.confirm, true, "an unconfirmed suggestion asks to be taken over");
});

test("a confirmed choice no longer asks, and a German fallback without a CV carries no reason", () => {
  const chosen = logic.view({ ...SUGGESTED, bewerbung: ["fr"], bewerbung_gewaehlt: true });
  assert.deepEqual(chosen.options.map(option => option.checked), [false, false, true]);
  assert.equal(chosen.confirm, false);

  const fallback = logic.view({ app: "de", app_gewaehlt: false, bewerbung: ["de"], bewerbung_gewaehlt: false, vorschlag: [] });
  assert.deepEqual(fallback.options.map(option => [option.checked, option.parts]),
    [[true, ["Deutsch"]], [false, ["Englisch"]], [false, ["Französisch"]]]);
});

test("only an app language other than German says that the translation is still coming", () => {
  assert.equal(logic.view(SUGGESTED).pending, null);
  assert.equal(logic.view({ ...SUGGESTED, app: "fr" }).pending, logic.PENDING_TRANSLATION);
  assert.equal(logic.view({ ...SUGGESTED, app: "en" }).pending, logic.PENDING_TRANSLATION);
});

test("an unknown state from the server falls back to German", () => {
  const view = logic.view({ app: "it", bewerbung: "de" });
  assert.equal(view.app, "de");
  assert.deepEqual(view.options.map(option => option.checked), [true, false, false]);
});

test("the checked boxes go to the server in the order of the list", () => {
  assert.deepEqual(logic.checkedValues([{ value: "fr", checked: true }, { value: "de", checked: false },
                                        { value: "en", checked: true }]), ["en", "fr"]);
});

test("the card stands under KI, Budget und Sprache with the design's texts", () => {
  const html = read("einstellungen.html");
  assert.equal(settings.SECTIONS[0].label, "KI, Budget und Sprache");
  assert.match(html, /<a href="#ki">KI, Budget und Sprache<\/a>/);
  assert.match(html, /id="bereich-ki" aria-label="KI, Budget und Sprache"/);
  assert.equal(settings.sectionOf("#sprache"), "ki");
  const part = card(html);
  assert.ok(html.indexOf('id="sprache"') > html.indexOf('id="bereich-ki"')
    && html.indexOf('id="sprache"') < html.indexOf('id="bereich-suche"'), "inside the panel KI");
  assert.match(part, /<h2 id="sprache-titel">Sprache<\/h2>/);
  assert.match(part, /<label class="field__label" for="sprache-app">Sprache der App<\/label>/);
  assert.match(part, /<legend[^>]*>Ich bewerbe mich auf<\/legend>/);
  assert.match(part, /data-text="einstellungen\.sprache-inserat"/);
  for (const script of ["/sprache-logik.js", "/sprache.js"]) {
    assert.match(html, new RegExp(`<script src="${script}"></script>`));
    assert.match(fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8"), new RegExp(`"${script}": "${script.slice(1)}",`));
  }
});

test("the note on the ad's language speaks to the person with Sie or du", () => {
  assert.equal(Texte.text("einstellungen.sprache-inserat", "stelle-sie"),
    "Das Anschreiben entsteht in der Sprache des Inserats, wenn Sie sich in dieser Sprache bewerben.");
  assert.equal(Texte.text("einstellungen.sprache-inserat", "stelle-du"),
    "Das Anschreiben entsteht in der Sprache des Inserats, wenn du dich in dieser Sprache bewirbst.");
});

test("the page script sets every text with textContent and joins the suggestion with DotLine", () => {
  const script = read("sprache.js");
  assert.doesNotMatch(script, /innerHTML/);
  assert.match(script, /DotLine\.render/);
});
