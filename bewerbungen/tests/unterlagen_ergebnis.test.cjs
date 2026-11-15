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
  assert.equal(R.attachmentsLine(available, [], []), "Beilagen: keine.");
  assert.equal(R.attachmentsLine(available, [available[0]], []), "Beilagen: Diplom-Muster.pdf");
  assert.equal(R.attachmentsLine(available, null, [available[1]]), "Beilagen: Zertifikat-Beispiel.pdf (Vorschlag, noch nicht gespeichert)");
  assert.equal(R.attachmentsLine(available, null, []), "Beilagen: keine.");
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
  assert.match(step, /<button type="button" class="btn" id="dossier-gestalten" aria-expanded="false" aria-controls="dossier-gestalten-teil">Dossier gestalten<\/button>/);
  assert.match(step, /<div class="dossier-panel" id="dossier-gestalten-teil" hidden>/);
  assert.match(step, /<button type="button" class="btn btn--quiet" id="beilagen-aendern" aria-expanded="false" aria-controls="beilagen-liste">Beilagen ändern<\/button>/);
  assert.match(step, /<div class="attach-list" id="beilagen-liste" hidden>/);
  assert.match(step, /<p class="status-line" id="befunde-ansage" role="status" aria-live="polite"><\/p>/);
  assert.ok(step.indexOf('id="dossier-kurz"') < step.indexOf('id="erstellen"'), "the dossier line comes before the button");
  assert.ok(step.indexOf('id="erstellen"') < step.indexOf('id="beilagen-aendern"'), "the attachments line comes after it");
  assert.doesNotMatch(step, /<iframe/);
  assert.match(html, /<script src="\/unterlagen-ergebnis.js"><\/script>[\s\S]*<script src="\/bewerbung.js"><\/script>/);
});

/** A stand-in DOM for unterlagen-schritt.js: the elements it looks up by id, the ones it builds, focus and clicks. */
function page() {
  const state = { focused: null, scrolled: [] };
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
      get firstElementChild() { return n.children[0] || null; },
    };
    return n;
  }
  const ids = ["dossier-gestalten", "dossier-gestalten-teil", "beilagen-aendern", "beilagen-liste", "pdfs", "befunde",
    "befunde-ok", "befunde-ok-liste", "befunde-ok-titel", "befunde-ansage", "beilagen-zeile", "dossier-kurz",
    "dossier-kurz-design", "s-lebenslauf", "f-variante", "s-anschreiben", "anschreiben-titel", "d-design"];
  const byId = Object.fromEntries(ids.map(id => [id, node("div", { id })]));
  byId["dossier-gestalten"].attrs = { id: "dossier-gestalten", "aria-expanded": "false", "aria-controls": "dossier-gestalten-teil" };
  byId["beilagen-aendern"].attrs = { id: "beilagen-aendern", "aria-expanded": "false", "aria-controls": "beilagen-liste" };
  byId["dossier-gestalten-teil"].hidden = true;
  byId["beilagen-liste"].hidden = true;
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
  };
  vm.runInNewContext(lies("unterlagen-schritt.js"), { window, document: { getElementById: id => byId[id] } });
  return { S: window.UnterlagenSchritt, byId, state };
}

const all = (n, match) => (n && typeof n === "object" ? [...(match(n) ? [n] : []), ...n.children.flatMap(c => all(c, match))] : []);
const textOf = n => (n && typeof n === "object" ? n.children.map(textOf).join("") : String(n ?? ""));
const link = (root, text) => all(root, n => n.tagName === "A" && textOf(n) === text)[0];

test("«Dossier gestalten» and «Beilagen ändern» open their part in place and say so with aria-expanded", () => {
  const { byId } = page();
  for (const [button, panel] of [["dossier-gestalten", "dossier-gestalten-teil"], ["beilagen-aendern", "beilagen-liste"]]) {
    byId[button].click();
    assert.equal(byId[button].getAttribute("aria-expanded"), "true", button);
    assert.equal(byId[panel].hidden, false, panel);
    byId[button].click();
    assert.equal(byId[button].getAttribute("aria-expanded"), "false", button);
    assert.equal(byId[panel].hidden, true, panel);
  }
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

  link(byId.pdfs, "Für diese Stelle anpassen").click();
  assert.equal(state.focused, byId["f-variante"], "the CV leads to the variant choice");
  assert.deepEqual(state.scrolled, ["s-lebenslauf"]);
  link(byId.pdfs, "Anschreiben ändern").click();
  assert.equal(state.focused, byId["anschreiben-titel"]);
  link(byId.pdfs, "Dossier gestalten").click();
  assert.equal(byId["dossier-gestalten-teil"].hidden, false);
  assert.equal(byId["dossier-gestalten"].getAttribute("aria-expanded"), "true");
  assert.equal(state.focused, byId["d-design"]);
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

test("the dossier line shows only with the dossier chosen and not sent, and closes its part otherwise", () => {
  const { S, byId } = page();
  S.showDossierLine({ unterlagen: "dossier", dossier_design: "register" });
  assert.equal(byId["dossier-kurz"].hidden, false);
  assert.equal(byId["dossier-kurz-design"].textContent, "Design Register");
  byId["dossier-gestalten"].click();
  S.showDossierLine({ unterlagen: "einzeln" });
  assert.equal(byId["dossier-kurz"].hidden, true);
  assert.equal(byId["dossier-gestalten-teil"].hidden, true);
  S.showDossierLine({ unterlagen: "dossier", versand: { datum: "2026-11-01" } });
  assert.equal(byId["dossier-kurz"].hidden, true);
});

test("after creating, the page waits for the check and moves the focus", () => {
  const code = lies("bewerbung.js");
  const create = code.slice(code.indexOf('$("erstellen").addEventListener'), code.indexOf('$("pruefen").addEventListener'));
  assert.match(create, /await laufendePruefung;[\s\S]*S\.focusFirstFinding\(\);/);
});

test("the hint in «Lebenslauf für diese Stelle» and the dossier sentence in «Aussehen des Lebenslaufs» name «Dossier gestalten»", () => {
  const html = lies("bewerbung.html");
  assert.match(html, /Gilt nur für diese Bewerbung\. Ein Dossier hat sein eigenes Design, unter «Dossier gestalten»\./);
  assert.doesNotMatch(html, /Unterlagen prüfen/);
  assert.match(lies("dateien.html"), /Ein Dossier hat sein eigenes Design, gewählt in der Bewerbung unter «Dossier gestalten»\./);
});
