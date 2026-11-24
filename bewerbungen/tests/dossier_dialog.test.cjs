// The dialog «Dossier gestalten» (#322, board A2 of docs/design/unterlagen-erstellen.md, G18, G19, G39): two groups,
// «Für diese Bewerbung» saved with «Übernehmen» and «Für alle Dossiers» saved at once, a cover preview, focus kept
// inside, Escape and «Abbrechen» asking before typed texts are lost. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const L = require("../seiten/dossier-dialog-logik.js");
const W = require("../seiten/unterlagen-wahl.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const lies = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const html = lies("bewerbung.html");
const step = html.slice(html.indexOf('id="s-pruefen"'), html.indexOf('id="s-abschicken"'));
const dialogHtml = html.slice(html.indexOf('<dialog class="dialog dossier-dialog"'), html.indexOf("</dialog>", html.indexOf('id="dossier-dialog"')));
const [forThis, forAll] = (() => {
  const second = dialogHtml.indexOf('id="d-zeichen-teil"');
  return [dialogHtml.slice(0, second), dialogHtml.slice(second)];
})();

// What the person can choose today stays reachable, now inside the dialog
const CONTROLS = ["d-design", "d-seite-deckblatt", "d-seite-anschreiben", "d-seite-lebenslauf", "d-seite-weitere",
  "dossier-gruss", "dossier-dank", "dossier-entwerfen", "d-zeichen-liste", "d-logo-datei", "d-initialen", "d-akzent-liste",
  "d-eigene-farbe", "d-eigene-farbe-wahl", "d-vorschlag", "d-zeichen-zuruecksetzen", "d-vorschau"];

test("the step no longer carries the controls; the dialog does", () => {
  assert.ok(dialogHtml.length > 0, "the page has the dialog");
  for (const id of CONTROLS) {
    assert.doesNotMatch(step, new RegExp(`id="${id}"`), `${id} left the step`);
    assert.match(dialogHtml, new RegExp(`id="${id}"`), `${id} is in the dialog`);
  }
});

test("the dialog is a native dialog named by its title", () => {
  assert.match(dialogHtml, /^<dialog class="dialog dossier-dialog" id="dossier-dialog" aria-labelledby="dossier-dialog-titel">/);
  assert.match(dialogHtml, /<h2 class="dialog__title dossier-dialog__title" id="dossier-dialog-titel">Dossier gestalten<\/h2>/);
});

test("«Für diese Bewerbung» holds the design as three tiles, «Design pro Seite» collapsed, greeting and thanks", () => {
  assert.match(forThis, /<section class="dossier-group" aria-labelledby="dossier-bewerbung-titel">\s*<h3 class="dossier-group__title" id="dossier-bewerbung-titel">Für diese Bewerbung<\/h3>/);
  assert.match(forThis, /<div class="design-tiles dossier-designs" id="d-design" role="radiogroup" aria-labelledby="d-design-titel">/);
  const radios = [...forThis.matchAll(/<input type="radio" name="d-design" value="([a-z]+)"/g)].map(m => m[1]);
  assert.deepEqual(radios, ["siegel", "raster", "register"]);
  for (const name of ["Siegel", "Raster", "Register"]) assert.match(forThis, new RegExp(`${name}</span><span class="design-tile__text">`));
  assert.match(forThis, /<details class="dossier-pages" id="d-erweitert"><summary>Design pro Seite<\/summary>/);
  assert.ok(forThis.indexOf('id="d-design"') < forThis.indexOf('id="d-erweitert"'));
  assert.ok(forThis.indexOf('id="d-erweitert"') < forThis.indexOf('id="dossier-gruss"'));
  assert.match(forThis, /Von der KI entwerfen/);
  assert.doesNotMatch(dialogHtml, /Texte speichern/, "the texts are saved with «Übernehmen»");
});

test("«Für alle Dossiers» holds sign and colour, says it applies to all and is saved at once", () => {
  assert.match(forAll, /^id="d-zeichen-teil" aria-labelledby="d-zeichen-titel" hidden>\s*<h3 class="dossier-group__title" id="d-zeichen-titel">Für alle Dossiers<\/h3>/);
  assert.match(forAll, /Zeichen und Farbe gelten für alle Dossiers\. Jede Wahl ist sofort gespeichert; «Abbrechen» nimmt sie nicht zurück\./);
  for (const text of ["Logo wählen", "Initialen", "Eigene Farbe", "Vorschlag übernehmen", "Zurück zur Voreinstellung"]) {
    assert.match(forAll, new RegExp(text), text);
  }
  assert.match(dialogHtml, /<figure class="mark-preview dossier-dialog__preview" id="d-vorschau-teil" hidden><div id="d-vorschau" role="img"><\/div>/);
});

test("the buttons are «Abbrechen» and «Übernehmen», and the question waits hidden", () => {
  assert.match(dialogHtml, /<div class="dialog__actions" id="dossier-aktionen"><button type="button" class="btn" id="dossier-abbrechen">Abbrechen<\/button><button type="button" class="btn btn--primary" id="dossier-uebernehmen">Übernehmen<\/button><\/div>/);
  assert.match(dialogHtml, /<div class="dialog__actions dossier-dialog__ask" id="dossier-verwerfen" role="group" aria-labelledby="dossier-verwerfen-frage" hidden><p class="dossier-dialog__question" id="dossier-verwerfen-frage">Änderungen verwerfen\?<\/p><button type="button" class="btn" id="dossier-weiter">Weiter bearbeiten<\/button><button type="button" class="btn btn--danger" id="dossier-verwerfen-ja">Verwerfen<\/button><\/div>/);
  assert.match(html, /<script src="\/dossier-dialog-logik.js"><\/script>\s*<script src="\/dossier-dialog.js"><\/script>/);
});

test("at phone width the dialog fills the screen and the buttons stay at the bottom", () => {
  const css = lies("unterlagen.css");
  assert.match(css, /\.dossier-dialog\[open\] \{ display: flex; flex-direction: column; \}/);
  assert.match(css, /\.dossier-dialog__body \{ position: relative; flex: 1 1 auto; min-height: 0; overflow-y: auto;/);
  assert.match(css, /\.dossier-dialog__footer \{ flex: none;/);
  const phone = css.slice(css.indexOf("@media (max-width: 600px)"));
  assert.match(phone, /\.dossier-dialog \{ inset: 0; width: 100%; max-width: 100%; height: 100dvh; max-height: 100dvh; margin: 0;/);
});

// The logic without DOM

test("«Abbrechen» and Escape ask only when texts were changed", () => {
  assert.equal(L.cancelAction(false), "close");
  assert.equal(L.cancelAction(true), "ask");
});

test("the message after «Übernehmen» says what was saved and which page falls away", () => {
  assert.equal(L.savedMessage(false, null), "");
  assert.equal(L.savedMessage(true, null), "Dossier übernommen. Mit «Unterlagen erstellen» entsteht es neu.");
  assert.equal(L.savedMessage(false, { gruss: "Guten Tag", dank: "" }),
    "Dossier übernommen. Mit «Unterlagen erstellen» entsteht es neu. Ohne Dank entfällt die Seite dazu.");
  assert.equal(L.savedMessage(true, { gruss: " ", dank: "" }),
    "Dossier übernommen. Mit «Unterlagen erstellen» entsteht es neu. Ohne Begrüssung und Dank entfällt die Seite dazu.");
});

test("Tab wraps at the ends of the dialog and is left alone in between", () => {
  assert.equal(L.wrapIndex(4, 5, false), 0);
  assert.equal(L.wrapIndex(0, 5, true), 4);
  assert.equal(L.wrapIndex(2, 5, false), -1);
  assert.equal(L.wrapIndex(2, 5, true), -1);
  assert.equal(L.wrapIndex(-1, 5, false), 0, "focus on the dialog itself goes to the first control");
  assert.equal(L.wrapIndex(-1, 5, true), 4);
  assert.equal(L.wrapIndex(0, 0, false), -1);
});

// The DOM, with a stand-in for the dialog and the texts

function fakePage({ textsChanged = false, failSave = false } = {}) {
  const state = { focused: null, modal: 0, saved: [], textsSaved: 0, textsDiscarded: 0, textsOpened: 0, events: [] };
  function node(tag, attrs = {}) {
    const handlers = {};
    const n = {
      tagName: tag.toUpperCase(), ...attrs, hidden: Boolean(attrs.hidden), textContent: "", disabled: false,
      addEventListener: (type, handler) => { (handlers[type] ||= []).push(handler); },
      dispatch: (type, event = {}) => {
        const e = { target: n, defaultPrevented: false, preventDefault() { e.defaultPrevented = true; }, ...event };
        for (const h of handlers[type] || []) h(e);
        return e;
      },
      click: () => n.dispatch("click"),
      focus: () => { state.focused = n; },
      get isConnected() { return n.connected !== false; },
    };
    return n;
  }
  const body = node("body");
  const radios = W.DESIGNS.map(value => node("input", { type: "radio", name: "d-design", value, checked: false }));
  const selects = W.SEITEN.map(seite => node("select", { value: "siegel", dataset: { seite } }));
  const byId = Object.fromEntries(["d-erweitert", "dossier-aktionen", "dossier-abbrechen", "dossier-uebernehmen",
    "dossier-verwerfen", "dossier-weiter", "dossier-verwerfen-ja", "dossier-dialog-status"].map(id => [id, node("div", { id })]));
  byId["dossier-verwerfen"].hidden = true;
  byId["d-design"] = Object.assign(node("div", { id: "d-design" }), { querySelectorAll: () => radios });
  byId["d-seiten"] = Object.assign(node("div", { id: "d-seiten" }), { querySelectorAll: () => selects });
  const visible = () => [radios.find(r => r.checked), ...selects, byId["dossier-abbrechen"], byId["dossier-uebernehmen"]]
    .filter(n => n && !n.hidden);
  const dialog = Object.assign(node("dialog", { id: "dossier-dialog", open: false }), {
    showModal() { dialog.open = true; state.modal += 1; },
    close() { dialog.open = false; dialog.dispatch("close"); },
    querySelectorAll: () => visible(),
  });
  byId["dossier-dialog"] = dialog;
  const opener = node("button", { id: "dossier-gestalten" });
  const docHandlers = {};
  const document = {
    body,
    getElementById: id => byId[id] || null,
    addEventListener: (type, handler) => { (docHandlers[type] ||= []).push(handler); },
    dispatchEvent: event => { state.events.push({ type: event.type, detail: event.detail }); (docHandlers[event.type] || []).forEach(h => h(event)); },
    get activeElement() { return state.focused; },
  };
  const window = {
    App: {
      senden: async (pfad, body) => {
        if (failSave) throw new Error("Die App antwortet nicht");
        state.saved.push({ pfad, body });
        return { ...body, unterlagen: "dossier" };
      },
      status: (element, text) => { element.textContent = text; },
    },
    Texte: require("../seiten/texte.js"),
    UnterlagenWahl: W,
    DossierDialogLogik: L,
    DossierTexte: {
      oeffnen: () => { state.textsOpened += 1; },
      geaendert: () => textsChanged,
      speichern: async () => { state.textsSaved += 1; return textsChanged ? { gruss: "Guten Tag", dank: "Danke" } : null; },
      verwerfen: () => { state.textsDiscarded += 1; },
    },
  };
  vm.runInNewContext(lies("dossier-dialog.js"), { window, document, setTimeout,
    CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } } });
  const load = entry => document.dispatchEvent({ type: "bewerbung-geladen", detail: { bewerbung: entry } });
  const settle = () => new Promise(resolve => setImmediate(resolve));
  return { D: window.DossierDialog, byId, dialog, radios, selects, opener, state, load, settle, node, body };
}

const ENTRY = { id: "muster-ag", unterlagen: "dossier", dossier_design: "raster" };
const drafts = state => state.events.filter(e => e.type === "dossier-entwurf").map(e => e.detail);

test("opening shows the design of the application with the focus on it, «Design pro Seite» closed", () => {
  const p = fakePage();
  p.load(ENTRY);
  p.D.open(p.opener);
  assert.equal(p.state.modal, 1, "a modal dialog: the page behind is inert");
  assert.deepEqual(p.radios.map(r => r.checked), [false, true, false]);
  assert.equal(p.state.focused, p.radios[1]);
  assert.equal(p.byId["d-erweitert"].open, false);
  assert.ok(p.selects.every(s => s.value === "raster"));
  assert.equal(p.state.textsOpened, 1);
  assert.deepEqual(drafts(p.state).at(-1), W.seitenDesigns(ENTRY), "the cover preview follows the draft");
});

test("with its own design per page, «Design pro Seite» opens", () => {
  const p = fakePage();
  p.load({ ...ENTRY, dossier_seiten: { lebenslauf: "siegel" } });
  p.D.open(p.opener);
  assert.equal(p.byId["d-erweitert"].open, true);
});

test("«Abbrechen» without changed texts closes, saves nothing and returns the focus", async () => {
  const p = fakePage();
  p.load(ENTRY);
  p.D.open(p.opener);
  p.radios[2].checked = true;
  p.byId["d-design"].dispatch("change", { target: p.radios[2] });
  p.byId["dossier-abbrechen"].click();
  await p.settle();
  assert.equal(p.dialog.open, false);
  assert.deepEqual(p.state.saved, []);
  assert.equal(p.state.focused, p.opener);
  assert.equal(drafts(p.state).at(-1), null, "the preview goes back to what is saved");
});

test("after a text edit «Abbrechen» asks «Änderungen verwerfen?» first", async () => {
  const p = fakePage({ textsChanged: true });
  p.load(ENTRY);
  p.D.open(p.opener);
  p.byId["dossier-abbrechen"].click();
  assert.equal(p.dialog.open, true);
  assert.equal(p.byId["dossier-verwerfen"].hidden, false);
  assert.equal(p.byId["dossier-aktionen"].hidden, true);
  assert.equal(p.state.focused, p.byId["dossier-weiter"], "the safe answer has the focus");

  p.byId["dossier-weiter"].click();
  assert.equal(p.dialog.open, true);
  assert.equal(p.byId["dossier-verwerfen"].hidden, true);
  assert.equal(p.state.focused, p.byId["dossier-abbrechen"]);

  p.byId["dossier-abbrechen"].click();
  p.byId["dossier-verwerfen-ja"].click();
  await p.settle();
  assert.equal(p.dialog.open, false);
  assert.equal(p.state.textsDiscarded, 1);
  assert.equal(p.state.textsSaved, 0);
  assert.equal(p.state.focused, p.opener);
});

test("Escape closes the dialog, asks first after a text edit and steps back out of the question", () => {
  const plain = fakePage();
  plain.load(ENTRY);
  plain.D.open(plain.opener);
  const event = plain.dialog.dispatch("cancel");
  assert.equal(event.defaultPrevented, true, "the dialog closes itself, so the focus goes back");
  assert.equal(plain.dialog.open, false);
  assert.equal(plain.state.focused, plain.opener);

  const typed = fakePage({ textsChanged: true });
  typed.load(ENTRY);
  typed.D.open(typed.opener);
  typed.dialog.dispatch("cancel");
  assert.equal(typed.dialog.open, true);
  assert.equal(typed.byId["dossier-verwerfen"].hidden, false);
  typed.dialog.dispatch("cancel");
  assert.equal(typed.dialog.open, true, "Escape on the question goes back to editing");
  assert.equal(typed.byId["dossier-verwerfen"].hidden, true);
});

test("a close the browser forces through with typed texts opens the dialog again with the question", () => {
  // Chrome holds back only one Escape without user activation in between; the next closes the dialog regardless
  const p = fakePage({ textsChanged: true });
  p.load(ENTRY);
  p.D.open(p.opener);
  p.dialog.close();
  assert.equal(p.dialog.open, true, "the typed texts are not lost unasked");
  assert.equal(p.state.modal, 2);
  assert.equal(p.byId["dossier-verwerfen"].hidden, false);
  assert.equal(p.state.focused, p.byId["dossier-weiter"]);
  assert.equal(p.state.textsDiscarded, 0);
  p.byId["dossier-verwerfen-ja"].click();
  assert.equal(p.dialog.open, false, "«Verwerfen» closes for good");
});

test("«Übernehmen» saves the chosen design and the texts, closes and tells the page", async () => {
  const p = fakePage({ textsChanged: true });
  p.load(ENTRY);
  p.D.open(p.opener);
  p.radios[2].checked = true;
  p.byId["d-design"].dispatch("change", { target: p.radios[2] });
  assert.ok(p.selects.every(s => s.value === "register"), "one design for all pages");
  p.selects[2].value = "siegel";
  p.byId["d-seiten"].dispatch("change", { target: p.selects[2] });
  assert.equal(drafts(p.state).at(-1).lebenslauf, "siegel");
  p.byId["dossier-uebernehmen"].click();
  await p.settle();
  assert.deepEqual(p.state.saved, [{ pfad: "/api/bewerbung",
    body: { id: "muster-ag", dossier_design: "register", dossier_seiten: { lebenslauf: "siegel" } } }]);
  assert.equal(p.state.textsSaved, 1);
  assert.equal(p.dialog.open, false);
  assert.equal(p.state.focused, p.opener);
  const done = p.state.events.find(e => e.type === "dossier-uebernommen");
  assert.equal(done.detail.meldung, "Dossier übernommen. Mit «Unterlagen erstellen» entsteht es neu.");
});

test("«Übernehmen» with nothing changed only closes", async () => {
  const p = fakePage();
  p.load(ENTRY);
  p.D.open(p.opener);
  p.byId["dossier-uebernehmen"].click();
  await p.settle();
  assert.deepEqual(p.state.saved, []);
  assert.equal(p.dialog.open, false);
  assert.ok(!p.state.events.some(e => e.type === "dossier-uebernommen"));
});

test("when saving fails, the dialog stays open and says why", async () => {
  const p = fakePage({ failSave: true });
  p.load(ENTRY);
  p.D.open(p.opener);
  p.radios[0].checked = true;
  p.byId["d-design"].dispatch("change", { target: p.radios[0] });
  p.byId["dossier-uebernehmen"].click();
  await p.settle();
  assert.equal(p.dialog.open, true);
  assert.equal(p.byId["dossier-dialog-status"].textContent, "Nicht übernommen: Die App antwortet nicht");
  assert.equal(p.byId["dossier-uebernehmen"].disabled, false);
});

test("Tab and Shift+Tab stay inside the dialog", () => {
  const p = fakePage();
  p.load(ENTRY);
  p.D.open(p.opener);
  p.byId["dossier-uebernehmen"].focus();
  const forward = p.dialog.dispatch("keydown", { key: "Tab", shiftKey: false });
  assert.equal(forward.defaultPrevented, true);
  assert.equal(p.state.focused, p.radios[1], "from the last control to the first");
  const back = p.dialog.dispatch("keydown", { key: "Tab", shiftKey: true });
  assert.equal(back.defaultPrevented, true);
  assert.equal(p.state.focused, p.byId["dossier-uebernehmen"], "from the first control to the last");
  p.selects[0].focus();
  assert.equal(p.dialog.dispatch("keydown", { key: "Tab", shiftKey: false }).defaultPrevented, false, "in between the browser moves on");
});

test("after «Übernehmen» from the tile link the focus finds the tile drawn anew, not the page", async () => {
  const p = fakePage({ textsChanged: true });
  p.load(ENTRY);
  const tile = p.node("button", { id: "doc-dossier-gestalten" });
  p.byId["doc-dossier-gestalten"] = tile;
  p.D.open(tile);
  p.byId["dossier-uebernehmen"].click();
  await p.settle();
  // the page loads anew and draws the tiles again: the old button is gone, and the focus with it
  tile.connected = false;
  p.state.focused = p.body;
  const drawn = p.node("button", { id: "doc-dossier-gestalten" });
  p.byId["doc-dossier-gestalten"] = drawn;
  p.D.refocus();
  assert.equal(p.state.focused, drawn);
});

test("refocus leaves a focus the person has moved on", async () => {
  const p = fakePage();
  p.load(ENTRY);
  p.D.open(p.opener);
  p.byId["dossier-abbrechen"].click();
  await p.settle();
  const elsewhere = p.node("input", { id: "f-notiz" });
  elsewhere.focus();
  p.D.refocus();
  assert.equal(p.state.focused, elsewhere);
});

test("the tile link keeps one id, and the page calls refocus once it has drawn the step anew", () => {
  assert.match(lies("unterlagen-schritt.js"), /el\("button", \{ type: "button", id: "doc-dossier-gestalten", class: "btn btn--quiet doc-tile__link"/);
  assert.match(lies("bewerbung.js"), /document\.addEventListener\("dossier-uebernommen", async event => \{\s*await laden\(\);\s*window\.DossierDialog\.refocus\(\);/);
});

test("Escape on the key is handled once, so the browser never closes the dialog by itself", () => {
  const typed = fakePage({ textsChanged: true });
  typed.load(ENTRY);
  typed.D.open(typed.opener);
  const key = typed.dialog.dispatch("keydown", { key: "Escape" });
  assert.equal(key.defaultPrevented, true);
  assert.equal(typed.dialog.open, true);
  assert.equal(typed.byId["dossier-verwerfen"].hidden, false, "the question shows");
  typed.dialog.dispatch("cancel"); // a browser that still sends its close request after the key
  assert.equal(typed.byId["dossier-verwerfen"].hidden, false, "the same Escape does not count twice");
  typed.dialog.dispatch("keydown", { key: "Escape" });
  assert.equal(typed.byId["dossier-verwerfen"].hidden, true, "the next Escape steps back out of the question");
  assert.equal(typed.dialog.open, true);

  const plain = fakePage();
  plain.load(ENTRY);
  plain.D.open(plain.opener);
  assert.equal(plain.dialog.dispatch("keydown", { key: "Escape" }).defaultPrevented, true);
  assert.equal(plain.dialog.open, false);
  assert.equal(plain.state.focused, plain.opener);
});

test("the confirmation after «Übernehmen» stays in the step, as a status line", () => {
  assert.match(step, /<div class="btn-row"><button type="button" class="btn btn--primary" id="erstellen">Unterlagen erstellen<\/button>.*<\/div>\s*<p class="status-line" id="dossier-meldung" role="status" aria-live="polite"><\/p>/);
  assert.match(lies("bewerbung.js"), /if \(event\.detail\.meldung\) status\(\$\("dossier-meldung"\), event\.detail\.meldung, "ok"\);/);
});

test("the dialog says that a draft of the AI is saved at once, and why the button is off", () => {
  assert.match(forThis, /<p class="field__hint">Gilt nur für dieses Dossier und wird mit «Übernehmen» gespeichert\. Ein Entwurf der KI ist sofort gespeichert\.<\/p>/);
  assert.match(forThis, /<button type="button" class="btn btn--sm" id="dossier-entwerfen" aria-describedby="dossier-ki-aus" disabled>Von der KI entwerfen<\/button><p class="field__hint" id="dossier-ki-aus" hidden>Für einen Entwurf zuerst die KI unter «Anschreiben» einrichten\. Die Texte lassen sich auch selbst schreiben\.<\/p>/);
  const texts = lies("dossier-texte.js");
  assert.match(texts, /\$\("dossier-ki-aus"\)\.hidden = kiBereit;/);
  assert.doesNotMatch(texts, /KI_AUS/, "the reason no longer fades as a message");
});

test("the hidden logo input scrolls with the body, so the dialog never scrolls its title away", () => {
  // an absolutely placed input finds the dialog as its box unless the body is positioned
  assert.match(dialogHtml, /<input type="file" id="d-logo-datei" class="visually-hidden/);
  assert.match(lies("unterlagen.css"), /\.dossier-dialog__body \{ position: relative; flex: 1 1 auto; min-height: 0; overflow-y: auto;/);
});

test("group titles are 18 px, both sub-labels the same element, the design sheets white paper in dark mode", () => {
  assert.match(forThis, /<h4 class="dossier-group__label" id="d-design-titel">Design<\/h4>/);
  assert.match(forThis, /<h4 class="dossier-group__label">Begrüssung und Dank<\/h4>/);
  const css = lies("unterlagen.css");
  assert.match(css, /\.application \.dossier-group__title, \.dossier-group__title \{ margin: 0; font-size: 18px; line-height: 26px; \}/);
  assert.match(css, /\.dossier-designs \.design-tile__sheet \{ background-color: #fff; \}/);
});

test("the page reloads after «Übernehmen» and the preview follows the draft", () => {
  const page = lies("bewerbung.js");
  assert.match(page, /document\.addEventListener\("dossier-uebernommen", async event => \{\s*await laden\(\);/);
  const mark = lies("zeichen.js");
  assert.match(mark, /document\.addEventListener\("dossier-entwurf",/);
});
