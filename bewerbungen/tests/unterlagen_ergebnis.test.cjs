// The shorter step «Unterlagen erstellen und prüfen» (#321, option A in docs/design/unterlagen-erstellen.md, G40, G41):
// form as two tiles, one line for the dossier and the attachments, after creating the findings with the passed checks
// collapsed and one tile per document with a link to where it is adapted.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const R = require("../seiten/unterlagen-ergebnis.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const lies = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const ALL = { lebenslauf: true, anschreiben: true, dossier: true };
const OK = text => ({ stufe: "ok", text });

test("the step is called «Unterlagen erstellen und prüfen»", () => {
  assert.equal(R.STEP_TITLE, "Unterlagen erstellen und prüfen");
  assert.match(lies("bewerbung.html"), /<h2 id="pruefen-titel" tabindex="-1">Unterlagen erstellen und prüfen<\/h2>/);
});

test("with the two files there is one tile each, CV first, each with page 1 as thumbnail and Als PDF öffnen", () => {
  const tiles = R.tiles({ lebenslauf: true, anschreiben: true }, "einzeln", {});
  assert.deepEqual(tiles.map(t => t.art), ["lebenslauf", "anschreiben"]);
  assert.deepEqual(tiles.map(t => t.alt), ["Lebenslauf, Seite 1", "Anschreiben, Seite 1"]);
  assert.ok(tiles.every(t => t.open === "Als PDF öffnen"));
});

test("each document links to where it is adapted", () => {
  const byArt = Object.fromEntries(R.tiles(ALL, "dossier", {}).map(t => [t.art, t.adapt]));
  assert.deepEqual(byArt.lebenslauf, { text: "Für diese Stelle anpassen", target: "variant" });
  assert.deepEqual(byArt.anschreiben, { text: "Anschreiben ändern", target: "letter" });
  assert.deepEqual(byArt.dossier, { text: "Dossier gestalten", target: "dossier" });
  assert.deepEqual(R.tiles(ALL, "dossier", {}).map(t => t.art), ["dossier", "anschreiben", "lebenslauf"]);
});

test("an own CV PDF is changed in Lebenslauf und Dateien, and nothing is adapted once sent", () => {
  const own = R.tiles({ lebenslauf: true }, "einzeln", { ownCv: true })[0];
  assert.deepEqual(own.adapt, { text: "In Lebenslauf und Dateien ändern", target: "files", href: "/dateien" });
  assert.ok(R.tiles(ALL, "dossier", { sent: true }).every(t => t.adapt === null));
  assert.deepEqual(R.tiles({}, "einzeln", {}), []);
});

test("passed checks are counted and collapsed, problems and confirmed breaches stay in view", () => {
  const findings = [
    { stufe: "hinweis", text: "Lebenslauf: 3 Seiten", schluessel: "k1", bestaetigt: false },
    { stufe: "hinweis", text: "Anschreiben: letzte Seite fast leer", schluessel: "k2", bestaetigt: true },
    ...["a", "b", "c", "d", "e", "f"].map(OK),
  ];
  const groups = R.findingGroups(findings);
  assert.deepEqual(groups.shown.map(f => f.schluessel), ["k1", "k2"]);
  assert.equal(groups.ok.length, 6);
  assert.equal(groups.okLabel, "6 Prüfungen in Ordnung");
  assert.equal(R.findingGroups([OK("a")]).okLabel, "1 Prüfung in Ordnung");
  assert.equal(R.findingGroups([]).okLabel, "");
});

test("the findings are summed up in one sentence for the status line", () => {
  assert.equal(R.announcement([{ stufe: "fehler", text: "x" }, { stufe: "hinweis", text: "y" }, OK("a"), OK("b")]),
    "Geprüft: 1 Fehler, 1 Hinweis, 2 Prüfungen in Ordnung.");
  assert.equal(R.announcement([OK("a")]), "Geprüft: 1 Prüfung in Ordnung.");
  assert.equal(R.announcement([{ stufe: "hinweis", text: "y" }, { stufe: "hinweis", text: "z" }]), "Geprüft: 2 Hinweise.");
  assert.equal(R.announcement(null), "");
});

test("the attachments fit in one line", () => {
  const available = ["dokumente/zertifikate/Diplom-Muster.pdf", "dokumente/zertifikate/Zertifikat-Beispiel.pdf"];
  assert.equal(R.attachmentsLine([], null, []), "Beilagen: noch keine Zertifikate hochgeladen.");
  assert.equal(R.attachmentsLine(available, [], []), "Beilagen: keine gewählt.");
  assert.equal(R.attachmentsLine(available, [available[0]], []), "Beilagen: Diplom-Muster.pdf");
  assert.equal(R.attachmentsLine(available, null, [available[1]]), "Beilagen: Zertifikat-Beispiel.pdf (Vorschlag, noch nicht gespeichert)");
  assert.equal(R.attachmentsLine(available, null, []), "Beilagen: keine gewählt.");
});

test("the dossier line names design and the state of greeting and thanks", () => {
  assert.equal(R.designLine({}), "Design Siegel");
  assert.equal(R.designLine({ dossier_design: "raster" }), "Design Raster");
  assert.equal(R.designLine({ dossier_design: "raster", dossier_seiten: { deckblatt: "siegel" } }), "Design pro Seite");
  assert.equal(R.textsState({ gruss: "Hallo", dank: "Danke" }), "Begrüssung und Dank geschrieben");
  assert.equal(R.textsState({ gruss: "Hallo", dank: "" }), "Begrüssung geschrieben, ohne Dank");
  assert.equal(R.textsState({ gruss: " ", dank: "Danke" }), "Dank geschrieben, ohne Begrüssung");
  assert.equal(R.textsState({ gruss: "", dank: "" }), "Ohne Begrüssung und Dank");
});

test("the next-step texts name the new step", () => {
  assert.match(R.NEXT_CREATE, /«Unterlagen erstellen und prüfen»/);
  assert.match(R.nextClarify(1), /^Die Prüfung hat einen Fehler gefunden\. Er steht unter «Unterlagen erstellen und prüfen»\.$/);
  assert.match(R.nextClarify(2), /^Die Prüfung hat 2 Fehler gefunden\. Sie stehen unter «Unterlagen erstellen und prüfen»\.$/);
  const code = lies("bewerbung.js");
  assert.doesNotMatch(code, /"Unterlagen prüfen"|bei den Unterlagen/);
});

test("before creating the form shows as two tiles, the dossier as one line and the attachments as one line", () => {
  const html = lies("bewerbung.html");
  const step = html.slice(html.indexOf('id="s-pruefen"'), html.indexOf('id="s-abschicken"'));
  assert.equal((step.match(/<label class="form-tile">/g) || []).length, 2);
  // #322: «Dossier gestalten» opens a dialog; the step no longer carries the controls
  assert.match(step, /<button type="button" class="btn" id="dossier-gestalten" aria-haspopup="dialog">Dossier gestalten<\/button>/);
  assert.doesNotMatch(step, /dossier-gestalten-teil|dossier-panel/);
  assert.match(step, /<button type="button" class="btn btn--quiet" id="beilagen-aendern" aria-expanded="false" aria-controls="beilagen-liste">Beilagen ändern<\/button>/);
  assert.match(step, /<div class="attach-list" id="beilagen-liste" hidden>/);
  // the announcement is for screen readers; the collapsed summary already shows the count
  assert.match(step, /<p class="status-line visually-hidden" id="befunde-ansage" role="status" aria-live="polite"><\/p>/);
  assert.ok(step.indexOf('id="dossier-kurz"') < step.indexOf('id="erstellen"'), "the dossier line comes before the button");
  assert.ok(step.indexOf('id="erstellen"') < step.indexOf('id="beilagen-aendern"'), "the attachments line comes after it");
  assert.doesNotMatch(step, /<iframe/);
  assert.match(html, /<script src="\/unterlagen-ergebnis.js"><\/script>[\s\S]*<script src="\/bewerbung.js"><\/script>/);
});

/** A stand-in DOM for unterlagen-schritt.js: the elements it looks up by id, the ones it builds, focus and clicks. */
function page() {
  const state = { focused: null, scrolled: [], dialogOpenedFrom: [] };
  function node(tag, attrs = {}) {
    const handlers = {};
    const n = {
      tagName: tag.toUpperCase(), attrs: { ...attrs }, children: [], hidden: false, textContent: "", tabIndex: 0,
      getAttribute: name => n.attrs[name] ?? null,
      setAttribute: (name, value) => { n.attrs[name] = String(value); },
      addEventListener: (type, handler) => { handlers[type] = handler; },
      click: () => handlers.click && handlers.click({ preventDefault() {}, currentTarget: n }),
      replaceChildren: (...items) => { n.children = items; },
      focus: () => { state.focused = n; },
      scrollIntoView: () => state.scrolled.push(n.attrs.id),
      querySelector: () => n.children[0] || null,
      get firstElementChild() { return n.children[0] || null; },
    };
    return n;
  }
  const ids = ["dossier-gestalten", "beilagen-aendern", "beilagen-liste", "pdfs", "befunde",
    "befunde-ok", "befunde-ok-liste", "befunde-ok-titel", "befunde-ansage", "beilagen-zeile", "dossier-kurz",
    "dossier-kurz-design", "s-lebenslauf", "f-variante", "s-anschreiben", "anschreiben-titel", "unterlagen-wahl",
    "form-zeile", "form-zeile-text", "form-dossier", "form-aendern"];
  const byId = Object.fromEntries(ids.map(id => [id, node("div", { id })]));
  byId["beilagen-aendern"].attrs = { id: "beilagen-aendern", "aria-expanded": "false", "aria-controls": "beilagen-liste" };
  byId["beilagen-liste"].hidden = true;
  byId["form-zeile"].hidden = true;
  const checkedTile = node("input", { type: "radio", value: "dossier" });
  byId["unterlagen-wahl"].children = [checkedTile];
  const el = (tag, attrs = {}, ...kids) => {
    const n = node(tag, Object.fromEntries(Object.entries(attrs).filter(([k]) => !k.startsWith("on"))));
    if (attrs.onclick) n.addEventListener("click", attrs.onclick);
    n.children = kids.flat().filter(k => k !== null && k !== undefined);
    return n;
  };
  const window = {
    App: { el, url: (p, q) => `${p}?${new URLSearchParams(q)}` },
    UnterlagenErgebnis: R,
    UnterlagenWahl: require("../seiten/unterlagen-wahl.js"),
    DossierDialog: { open: from => state.dialogOpenedFrom.push(from) },
  };
  vm.runInNewContext(lies("unterlagen-schritt.js"), { window, document: { getElementById: id => byId[id] } });
  return { S: window.UnterlagenSchritt, byId, state, checkedTile };
}

const all = (n, match) => (n && typeof n === "object" ? [...(match(n) ? [n] : []), ...n.children.flatMap(c => all(c, match))] : []);
const textOf = n => (n && typeof n === "object" ? n.children.map(textOf).join("") : String(n ?? ""));
const link = (root, text) => all(root, n => n.tagName === "A" && textOf(n) === text)[0];

test("«Beilagen ändern» opens its part in place and says so with aria-expanded", () => {
  const { byId } = page();
  byId["beilagen-aendern"].click();
  assert.equal(byId["beilagen-aendern"].getAttribute("aria-expanded"), "true");
  assert.equal(byId["beilagen-liste"].hidden, false);
  byId["beilagen-aendern"].click();
  assert.equal(byId["beilagen-aendern"].getAttribute("aria-expanded"), "false");
  assert.equal(byId["beilagen-liste"].hidden, true);
});

test("«Dossier gestalten» in the dossier line and in the closing line opens the dialog from that button", () => {
  const { byId, state } = page();
  byId["dossier-gestalten"].click();
  byId["form-dossier"].click();
  assert.deepEqual(state.dialogOpenedFrom, [byId["dossier-gestalten"], byId["form-dossier"]]);
});

test("each tile has page 1 with its alt text, Als PDF öffnen and the link to where it is adapted", () => {
  const { S, byId, state } = page();
  const daten = { bewerbung: { id: "a", unterlagen: "dossier" }, pdfs: ALL, eigener_lebenslauf: false };
  S.showTiles("a", daten, 1);
  const tiles = byId.pdfs.children;
  assert.equal(tiles.length, 3);
  const images = all(byId.pdfs, n => n.tagName === "IMG");
  assert.deepEqual(images.map(i => i.attrs.alt), ["Dossier, Seite 1", "Anschreiben, Seite 1", "Lebenslauf, Seite 1"]);
  assert.ok(images.every(i => i.attrs.src.startsWith("/api/pdf/miniatur?")));
  assert.equal(all(byId.pdfs, n => textOf(n) === "Als PDF öffnen" && n.tagName === "A").length, 3);
  for (const tile of tiles) {
    const heading = all(tile, n => n.tagName === "H3")[0];
    assert.ok(heading.attrs.id, "the heading has an id");
    assert.equal(tile.attrs["aria-labelledby"], heading.attrs.id, "the tile is named by its heading");
  }
  assert.equal(new Set(tiles.map(t => t.attrs["aria-labelledby"])).size, 3, "each tile has its own heading id");

  link(byId.pdfs, "Für diese Stelle anpassen").click();
  assert.equal(state.focused, byId["f-variante"], "the CV leads to the variant choice");
  assert.deepEqual(state.scrolled, ["s-lebenslauf"]);
  link(byId.pdfs, "Anschreiben ändern").click();
  assert.equal(state.focused, byId["anschreiben-titel"]);
  const design = all(byId.pdfs, n => n.tagName === "BUTTON" && textOf(n) === "Dossier gestalten")[0];
  assert.equal(design.attrs["aria-haspopup"], "dialog", "the dossier tile opens the dialog, so it is a button");
  design.click();
  assert.deepEqual(state.dialogOpenedFrom, [design], "focus comes back to the tile");
});

test("an own CV links to Lebenslauf und Dateien", () => {
  const { S, byId } = page();
  S.showTiles("a", { bewerbung: { id: "a" }, pdfs: { lebenslauf: true }, eigener_lebenslauf: true }, 1);
  assert.equal(link(byId.pdfs, "In Lebenslauf und Dateien ändern").attrs.href, "/dateien");
});

test("after creating the findings are announced and the focus goes to the first one", () => {
  const { S, byId, state } = page();
  const row = f => ({ ...page().byId.befunde, tagName: "LI", text: f.text, focus() { state.focused = this; } });
  S.showFindings([{ stufe: "hinweis", text: "Lebenslauf: 3 Seiten" }, OK("a"), OK("b")], row);
  assert.equal(byId["befunde-ansage"].textContent, "Geprüft: 1 Hinweis, 2 Prüfungen in Ordnung.");
  assert.equal(byId["befunde-ok-titel"].textContent, "2 Prüfungen in Ordnung");
  assert.equal(byId["befunde-ok"].hidden, false);
  S.focusFirstFinding();
  assert.equal(state.focused.text, "Lebenslauf: 3 Seiten");
  assert.equal(state.focused.tabIndex, -1);

  S.showFindings([OK("a")], row);
  S.focusFirstFinding();
  assert.equal(state.focused, byId["befunde-ok-titel"], "with nothing to do, the passed checks get the focus");
});

test("before creating, the dossier line shows only with the dossier chosen and not sent", () => {
  const { S, byId } = page();
  S.showForm({ unterlagen: "dossier", dossier_design: "register" }, false);
  assert.equal(byId["unterlagen-wahl"].hidden, false);
  assert.equal(byId["dossier-kurz"].hidden, false);
  assert.equal(byId["dossier-kurz-design"].textContent, "Design Register");
  assert.equal(byId["form-zeile"].hidden, true);
  S.showForm({ unterlagen: "einzeln" }, false);
  assert.equal(byId["dossier-kurz"].hidden, true);
  S.showForm({ unterlagen: "dossier", versand: { datum: "2026-11-01" } }, true);
  assert.equal(byId["dossier-kurz"].hidden, true);
  assert.equal(byId["unterlagen-wahl"].hidden, true);
  assert.equal(byId["form-zeile"].hidden, true, "once sent the form cannot change");
});

test("the closing line names the form and the design of the dossier", () => {
  assert.equal(R.formLine({ unterlagen: "dossier" }), "Form: Dossier, Siegel");
  assert.equal(R.formLine({ unterlagen: "dossier", dossier_design: "raster" }), "Form: Dossier, Raster");
  assert.equal(R.formLine({ unterlagen: "dossier", dossier_design: "raster", dossier_seiten: { deckblatt: "siegel" } }),
    "Form: Dossier, Design pro Seite");
  assert.equal(R.formLine({}), "Form: Anschreiben und Lebenslauf");
});

test("the documents count as created when the main file of the chosen form is there", () => {
  assert.equal(R.built({ lebenslauf: true }, "einzeln"), true);
  assert.equal(R.built({ anschreiben: true }, "einzeln"), true);
  assert.equal(R.built({}, "einzeln"), false);
  assert.equal(R.built({ lebenslauf: true, anschreiben: true }, "dossier"), false, "the dossier itself is missing");
  assert.equal(R.built(ALL, "dossier"), true);
});

test("after creating, the tiles and the dossier line collapse into one line beside the attachments", () => {
  const { S, byId } = page();
  S.showForm({ unterlagen: "dossier", dossier_design: "siegel" }, true);
  assert.equal(byId["unterlagen-wahl"].hidden, true);
  assert.equal(byId["dossier-kurz"].hidden, true);
  assert.equal(byId["form-zeile"].hidden, false);
  assert.equal(byId["form-zeile-text"].textContent, "Form: Dossier, Siegel");
  assert.equal(byId["form-dossier"].hidden, false, "«Dossier gestalten» stays reachable");
  S.showForm({ unterlagen: "einzeln" }, true);
  assert.equal(byId["form-zeile-text"].textContent, "Form: Anschreiben und Lebenslauf");
  assert.equal(byId["form-dossier"].hidden, true, "without a dossier there is nothing to design");
});

test("«Form ändern» opens the tiles again with the focus on the chosen one, until the next creating", () => {
  const { S, byId, state, checkedTile } = page();
  S.showForm({ unterlagen: "dossier" }, true);
  byId["form-aendern"].click();
  assert.equal(byId["unterlagen-wahl"].hidden, false);
  assert.equal(byId["dossier-kurz"].hidden, false);
  assert.equal(byId["form-zeile"].hidden, true);
  assert.equal(state.focused, checkedTile);
  S.showForm({ unterlagen: "einzeln" }, true);
  assert.equal(byId["unterlagen-wahl"].hidden, false, "a new choice keeps the tiles open");
  S.closeForm();
  S.showForm({ unterlagen: "einzeln" }, true);
  assert.equal(byId["unterlagen-wahl"].hidden, true, "after creating anew they collapse again");
  assert.equal(byId["form-zeile"].hidden, false);
});

test("the closing line sits with the attachments line, after the documents", () => {
  const html = lies("bewerbung.html");
  const step = html.slice(html.indexOf('id="s-pruefen"'), html.indexOf('id="s-abschicken"'));
  assert.match(step, /<div class="attach-line" id="form-zeile" hidden><p class="attach-line__text" id="form-zeile-text"><\/p>/);
  assert.match(step, /<button type="button" class="btn btn--quiet" id="form-dossier" aria-haspopup="dialog" hidden>Dossier gestalten<\/button>/);
  assert.match(step, /<button type="button" class="btn btn--quiet" id="form-aendern">Form ändern<\/button>/);
  assert.ok(step.indexOf('id="pdfs"') < step.indexOf('id="form-zeile"'));
  assert.ok(step.indexOf('id="form-zeile"') < step.indexOf('id="beilagen-zeile"'));
});

test("after creating, the page collapses the form before it loads anew", () => {
  const code = lies("bewerbung.js");
  const create = code.slice(code.indexOf('$("erstellen").addEventListener'), code.indexOf('$("pruefen").addEventListener'));
  assert.match(create, /await senden\("\/api\/unterlagen"[^\n]*\n\s*S\.closeForm\(\);\n\s*await laden\(\);/);
  assert.match(code, /S\.showForm\(b, R\.built\(daten\.pdfs, W\.gewaehlt\(b\)\)\);/);
});

test("after creating, the page waits for the check and moves the focus", () => {
  const code = lies("bewerbung.js");
  const create = code.slice(code.indexOf('$("erstellen").addEventListener'), code.indexOf('$("pruefen").addEventListener'));
  assert.match(create, /await laufendePruefung;[\s\S]*S\.focusFirstFinding\(\);/);
});

test("the hint in «Lebenslauf für diese Stelle» and the dossier sentence in «Aussehen des Lebenslaufs» name «Dossier gestalten»", () => {
  const html = lies("bewerbung.html");
  assert.match(html, /Gilt nur für diese Bewerbung\. Ein Dossier hat Design, Farbe und Zeichen aus «Dossier gestalten»; das Foto nimmt es von hier\./);
  assert.doesNotMatch(html, /Unterlagen prüfen/);
  assert.match(lies("dateien.html"), /Ein Dossier hat sein eigenes Design, gewählt in der Bewerbung unter «Dossier gestalten»\./);
});

// G93, #324: how the app balanced the pages, in a few words on each tile

test("each document names its pages and, only where the app changed the setting, how", () => {
  const note = (art, seiten, ausgleich) => R.pageNote(art, { seiten, ausgleich });
  assert.deepEqual(note("anschreiben", 1, { letter: "slightly-tighter" }), ["1 Seite", "etwas enger gesetzt"]);
  assert.deepEqual(note("lebenslauf", 2, { cv: "tighter" }), ["2 Seiten", "enger gesetzt"]);
  assert.deepEqual(note("lebenslauf", 3, { cv: "tightest" }), ["3 Seiten", "so eng wie möglich"]);
  assert.deepEqual(note("lebenslauf", 2, { cv: "wider" }), ["2 Seiten", "etwas grosszügiger gesetzt"]);
  assert.deepEqual(note("lebenslauf", 2, {}), ["2 Seiten"], "no change, no text");
  assert.deepEqual(note("lebenslauf", 2, { cv: "unknown" }), ["2 Seiten"]);
  assert.deepEqual(R.pageNote("lebenslauf", undefined), [], "nothing before the document is there");
});

test("the dossier names which of its parts the app balanced", () => {
  const line = notes => {
    const tile = R.tiles(ALL, "dossier", { notes }).find(t => t.art === "dossier");
    return [tile.name, ...tile.note].join(" · ");
  };
  assert.equal(line({ dossier: { seiten: 7, ausgleich: { cv: "slightly-tighter" } } }),
    "Dossier · 7 Seiten · Lebenslauf etwas enger gesetzt");
  assert.equal(line({ dossier: { seiten: 8, ausgleich: { cv: "tightest", letter: "tighter" } } }),
    "Dossier · 8 Seiten · Anschreiben enger gesetzt · Lebenslauf so eng wie möglich", "in the order of the dossier");
  assert.equal(line({ dossier: { seiten: 6, ausgleich: {} } }), "Dossier · 6 Seiten");
  const single = R.tiles(ALL, "dossier", { notes: { lebenslauf: { seiten: 2, ausgleich: { cv: "wider" } } } })
    .find(t => t.art === "lebenslauf");
  assert.deepEqual(single.note, ["2 Seiten", "etwas grosszügiger gesetzt"], "a single file names no part");
});

const shown = n => (n && typeof n === "object" ? (n.attrs.class === "visually-hidden" ? "" : n.children.map(shown).join("")) : String(n ?? ""));
const heard = n => (n && typeof n === "object" ? (n.attrs["aria-hidden"] === "true" ? "" : n.children.map(heard).join("")) : String(n ?? ""));
const noteOf = tile => all(tile, n => n.attrs.class === "doc-tile__note")[0];

test("the tile shows the note under its name, the «·» hidden from screen readers, and no colour for the state", () => {
  const { S, byId } = page();
  const seiten = { lebenslauf: { seiten: 3, ausgleich: { cv: "tightest" } }, anschreiben: { seiten: 1, ausgleich: {} } };
  S.showTiles("a", { bewerbung: { id: "a" }, pdfs: { lebenslauf: true, anschreiben: true }, seiten }, 1);
  const [cv, letter] = byId.pdfs.children;
  const note = noteOf(cv);
  assert.ok(note, "the CV tile has a note");
  assert.equal(cv.attrs["aria-describedby"], undefined, "the note follows the name as text, so it is not read twice");
  assert.equal(shown(note), "3 Seiten · so eng wie möglich");
  assert.equal(heard(note), "3 Seiten, so eng wie möglich");
  const dots = all(note, n => textOf(n).trim() === "·");
  assert.ok(dots.length === 1 && dots[0].attrs["aria-hidden"] === "true", "the separator is aria-hidden");
  assert.ok(!Object.keys(note.attrs).some(name => name === "data-level" || name === "style"), "no colour carries meaning");
  assert.equal(shown(noteOf(letter)), "1 Seite");

  S.showTiles("a", { bewerbung: { id: "a" }, pdfs: { lebenslauf: true }, seiten: {} }, 2);
  const tile = byId.pdfs.children[0];
  assert.equal(all(tile, n => n.attrs.class === "doc-tile__note").length, 0, "without a count, no note");
  assert.equal(tile.attrs["aria-describedby"], undefined);
});

// #331: a «·» never stands alone on a line, and a change never breaks inside its words

test("each «·» is glued to the part before it, and a line breaks only after «· »", () => {
  const { S, byId } = page();
  const dossierNote = ausgleich => {
    S.showTiles("a", { bewerbung: { id: "a", unterlagen: "dossier" }, pdfs: { dossier: true }, seiten: { dossier: { seiten: 7, ausgleich } } }, 1);
    return noteOf(byId.pdfs.children[0]);
  };
  for (const [ausgleich, words] of [
    [{ cv: "tightest" }, ["7 Seiten", "Lebenslauf so eng wie möglich"]],
    [{ letter: "slightly-tighter", cv: "tightest" }, ["7 Seiten", "Anschreiben etwas enger gesetzt", "Lebenslauf so eng wie möglich"]],
  ]) {
    const note = dossierNote(ausgleich);
    const parts = note.children.filter(n => typeof n === "object");
    assert.ok(parts.every(n => n.attrs.class === "doc-tile__part"), "the note holds only whole parts");
    assert.deepEqual(note.children.filter(n => typeof n !== "object"), words.slice(1).map(() => " "),
      "a plain space between two parts is the only place a line may break");
    assert.deepEqual(parts.map(shown), words.map((word, i) => (i < words.length - 1 ? `${word} ·` : word)),
      "the «·» sits inside the part before it, after a no-break space");
    assert.equal(shown(note), words.join(" · "));
    assert.equal(heard(note), words.join(", "), "screen readers hear commas, never the «·»");
  }
});

/** The declarations of the first rule in `css` whose selector ends with `selector`. */
const ruleOf = (css, selector) => {
  const line = css.split("\n").find(l => l.trimStart().split("{")[0].trim().endsWith(selector));
  assert.ok(line, `${selector} has its rule`);
  return line.slice(line.indexOf("{") + 1, line.lastIndexOf("}"));
};

test("a part of the note breaks to the next line only as a whole, and a long word cannot be split", () => {
  const css = lies("unterlagen.css");
  assert.match(ruleOf(css, ".doc-tile__part"), /display: inline-block; max-width: 100%;/);
  assert.doesNotMatch(ruleOf(css, ".doc-tile__note"), /overflow-wrap/);
});

test("the note runs under the thumbnail across the whole tile, so the longest change fits on one line", () => {
  const css = lies("unterlagen.css");
  const tile = ruleOf(css, ".doc-tile");
  assert.match(tile, /display: grid;/);
  assert.match(tile, /grid-template-areas: "thumb name" "thumb links" "note note";/);
  assert.match(ruleOf(css, ".doc-tile__body"), /display: contents;/, "name, note and links keep their order for screen readers");
  assert.match(ruleOf(css, ".doc-tile__thumb"), /grid-area: thumb;/);
  assert.match(ruleOf(css, ".doc-tile__name"), /grid-area: name;/);
  assert.match(ruleOf(css, ".doc-tile__links"), /grid-area: links;/);
  assert.match(ruleOf(css, ".doc-tile__note"), /grid-area: note;/);
});
