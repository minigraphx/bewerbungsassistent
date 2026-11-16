// The letter editor in the step Anschreiben (G94, #332, binding brief of the UI/UX review): opened from three places,
// one field per paragraph, the goal line while the letter is over one page, save and cancel. A small stand-in DOM;
// invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const L = require("../seiten/letter-editor-logik.js");
const Texte = require("../seiten/texte.js");
const logik = require("../seiten/bewerbung-logik.js");

const SEITEN = path.join(__dirname, "..", "seiten");
const lies = name => fs.readFileSync(path.join(SEITEN, name), "utf8");
const html = lies("bewerbung.html");

class FakeNode {
  constructor(doc, tag, attrs = {}) {
    Object.assign(this, { doc, tagName: tag.toUpperCase(), attrs: new Map(), children: [], listeners: {},
                          hidden: false, disabled: false, value: "", style: {}, scrollHeight: 96, offsetHeight: 50,
                          clientHeight: 48, parentNode: null });
    for (const [name, value] of Object.entries(attrs)) this.setAttribute(name, value);
    const node = this;
    this.classList = {
      contains: c => node.className.split(/\s+/).includes(c),
      toggle: (c, on) => { const set = new Set(node.className.split(/\s+/).filter(Boolean)); if (on) set.add(c); else set.delete(c); node.className = [...set].join(" "); },
      add: c => node.classList.toggle(c, true), remove: c => node.classList.toggle(c, false),
    };
  }
  get id() { return this.getAttribute("id"); }
  get className() { return this.getAttribute("class") || ""; }
  set className(value) { this.attrs.set("class", value); }
  setAttribute(name, value) {
    if (name === "hidden") this.hidden = true;
    else if (name === "disabled") this.disabled = true;
    else this.attrs.set(name, String(value));
  }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  removeAttribute(name) { this.attrs.delete(name); }
  append(...nodes) {
    for (const n of nodes.flat()) {
      if (n === null || n === undefined || n === false) continue;
      if (n instanceof FakeNode) n.parentNode = this;
      this.children.push(n);
    }
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  get elements() { return this.children.filter(c => c instanceof FakeNode); }
  get textContent() { return this.children.map(c => (c instanceof FakeNode ? c.textContent : String(c))).join(""); }
  set textContent(value) { this.children = [String(value)]; }
  all() { return this.elements.flatMap(c => [c, ...c.all()]); }
  matches(selector) { return selector.startsWith(".") ? this.classList.contains(selector.slice(1)) : this.tagName === selector.toUpperCase(); }
  querySelectorAll(selector) { return this.all().filter(n => n.matches(selector)); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatch(type, extra = {}) {
    const event = { type, target: this, currentTarget: this, defaultPrevented: false, stopped: false,
                    preventDefault() { event.defaultPrevented = true; }, stopPropagation() { event.stopped = true; },
                    stopImmediatePropagation() { event.stopped = true; }, ...extra };
    // the capture phase on the document runs first, as in a browser
    for (const h of [...(this.doc.capture[type] || [])]) if (!event.stopped) h(event);
    for (const h of this.listeners[type] || []) if (!event.stopped) h(event);
    return event;
  }
  click() { if (!this.disabled) this.dispatch("click"); }
  focus() { this.doc.activeElement = this; }
  scrollIntoView(options) { this.doc.scrolled.push([this, options]); }
  setSelectionRange(start, end) { this.selection = [start, end]; }
}

const IDS = ["brief-editor", "brief-editor-titel", "brief-editor-intro", "brief-betreff", "brief-anrede", "brief-gruss",
  "brief-ziel", "brief-absaetze", "brief-absatz-neu", "brief-als-text", "brief-aktionen", "brief-speichern",
  "brief-abbrechen", "brief-verwerfen", "brief-weiter", "brief-verwerfen-ja", "brief-editor-status", "brief-gespeichert",
  "anschreiben-aendern", "anschreiben-text", "ki-pruefung-teil", "freigabe-zeile", "freigabe-status", "ki-entwerfen",
  "ki-pruefen", "erstellen", "pruefen", "brief-offen-hinweis", "s-pruefen", "anschreiben-titel", "laengster-absatz"];

const LETTER = {
  betreff: "Bewerbung als Testerin", anrede: "Guten Tag Frau Muster",
  absaetze: ["Kurzer erster Absatz.", "x".repeat(250), "Mittlerer Absatz mit etwas mehr Text als der erste."],
  gruss: "Freundliche Grüsse", fingerabdruck: "f1", zeichen_pro_zeile: 99,
};
const OVER = { stufe: "fehler", schluessel: "k", bestaetigt: false, text: "zu lang", letter_cut: { lines: 4, paragraph: 1 } };

function page({ satz = "stelle-sie", answer = { geaendert: true }, failWith = null } = {}) {
  const doc = { activeElement: null, scrolled: [], capture: {} };
  const byId = Object.fromEntries(IDS.map(id => [id, new FakeNode(doc, "div", { id })]));
  byId["brief-editor"].hidden = true;
  byId["brief-verwerfen"].hidden = true;
  byId["brief-offen-hinweis"].hidden = true;
  const state = { sent: [], reloads: 0, reloaded: false, built: 0, windowHandlers: {}, levels: new Map() };
  byId.erstellen.addEventListener("click", () => { state.built += 1; });
  const window = {
    Texte,
    LetterEditorLogik: L,
    FindingRow: { LONGEST_ID: "laengster-absatz" },
    App: {
      el(tag, attrs = {}, ...kids) {
        const node = new FakeNode(doc, tag);
        for (const [name, value] of Object.entries(attrs || {})) {
          if (value === false || value === null || value === undefined) continue;
          if (name.startsWith("on")) node.addEventListener(name.slice(2), value);
          else node.setAttribute(name, value === true ? "" : value);
        }
        node.append(...kids);
        return node;
      },
      senden: async (pfad, body, parameter) => {
        state.sent.push({ pfad, body, parameter });
        if (failWith) throw failWith;
        return answer;
      },
      textsatz: async () => satz,
    },
    Meldungen: {
      zeige(element, inhalt, stufe = "", { aktion = null } = {}) {
        element.replaceChildren();
        state.levels.set(element.id, stufe);
        if (!inhalt) return;
        element.append(new FakeNode(doc, "span", { class: "status__text" }));
        element.elements[0].append(inhalt);
        if (aktion) {
          const button = new FakeNode(doc, "button", { class: "btn btn--sm status__action" });
          button.append(aktion.text);
          button.addEventListener("click", () => { element.replaceChildren(); aktion.ausfuehren(); });
          element.append(button);
        }
      },
    },
    addEventListener: (type, handler) => { (state.windowHandlers[type] ||= []).push(handler); },
  };
  const document = {
    getElementById: id => byId[id] || null, get activeElement() { return doc.activeElement; },
    addEventListener: (type, handler, capture) => { if (capture === true) (doc.capture[type] ||= []).push(handler); },
    removeEventListener: (type, handler, capture) => {
      if (capture === true) doc.capture[type] = (doc.capture[type] || []).filter(h => h !== handler);
    },
  };
  const context = { window, document,
    location: { search: "?id=muster-ag", reload: () => { state.reloaded = true; } }, CSS: { supports: () => false },
    URLSearchParams };
  vm.runInNewContext(lies("letter-editor.js"), context);
  const E = window.LetterEditor;
  const update = (letter = LETTER, findings = null, approval = { noetig: true, freigegeben: false }) => {
    // the page draws the read view first, as zeigeBrief does
    for (const id of ["anschreiben-text", "freigabe-zeile", "freigabe-status"]) byId[id].hidden = false;
    byId["ki-pruefung-teil"].hidden = true;
    E.update({ letter, findings, approval, shown: Boolean(letter) });
  };
  E.connect(async () => { state.reloads += 1; update({ ...LETTER, absaetze: ["Neu."], fingerabdruck: "f2" }); });
  const fields = () => byId["brief-absaetze"].querySelectorAll("textarea");
  const type = (field, text) => { field.value = text; field.dispatch("input"); };
  const settle = () => new Promise(resolve => setImmediate(resolve));
  const unload = () => { const e = { defaultPrevented: false, preventDefault() { e.defaultPrevented = true; } }; (state.windowHandlers.beforeunload || []).forEach(h => h(e)); return e; };
  return { E, byId, doc, document, window, state, update, fields, type, settle, unload };
}

const labelText = field => field.parentNode.querySelector("label").textContent;

/** unterlagen-schritt.js on the same page, so a tile link reaches the real editor (#332). */
function tileStep(p) {
  const extra = Object.fromEntries(["beilagen-liste", "dossier-gestalten", "form-dossier", "form-aendern", "pdfs",
    "unterlagen-wahl", "s-lebenslauf", "s-anschreiben", "f-variante"].map(id => [id, new FakeNode(p.doc, "div", { id })]));
  extra["beilagen-aendern"] = new FakeNode(p.doc, "button", { id: "beilagen-aendern", "aria-controls": "beilagen-liste" });
  const window = Object.assign(p.window, {
    App: { ...p.window.App, url: (pfad, query) => `${pfad}?${new URLSearchParams(query)}` },
    UnterlagenErgebnis: require("../seiten/unterlagen-ergebnis.js"),
    UnterlagenWahl: require("../seiten/unterlagen-wahl.js"),
  });
  const document = { ...p.document, getElementById: id => extra[id] || p.document.getElementById(id) };
  vm.runInNewContext(lies("unterlagen-schritt.js"), { window, document });
  return { S: window.UnterlagenSchritt, pdfs: extra.pdfs };
}
const hintOf = (p, field) => p.byId["brief-absaetze"].all().find(n => n.id === field.getAttribute("aria-describedby"));

// Markup of the page

test("«Anschreiben ändern» is a button that opens the editor, not a link to /inhalte", () => {
  assert.match(html, /<button type="button" class="btn btn--quiet" id="anschreiben-aendern" aria-expanded="false" aria-controls="brief-editor">Anschreiben ändern<\/button>/);
  assert.doesNotMatch(html, /id="anschreiben-aendern" href=/);
});

test("the editor is a form inside the step, in the order of the brief", () => {
  const step = html.slice(html.indexOf('id="s-anschreiben"'), html.indexOf('id="s-pruefen"'));
  assert.match(step, /<form class="letter-editor" id="brief-editor" aria-labelledby="brief-editor-titel" novalidate hidden>/);
  const order = ['id="brief-editor-titel" tabindex="-1">Anschreiben ändern</h3>', 'id="brief-editor-intro"', 'for="brief-betreff">Betreff',
    'for="brief-anrede">Anrede', '<legend class="field__label">Text</legend>', 'id="brief-ziel"', 'id="brief-absaetze"',
    'id="brief-absatz-neu">Absatz hinzufügen', 'for="brief-gruss">Gruss', 'Als Text bearbeiten (für Geübte)</a>',
    'id="brief-speichern">Speichern', 'id="brief-abbrechen">Abbrechen', '<p class="letter-editor__question" id="brief-verwerfen-frage">Änderungen verwerfen?</p><button type="button" class="btn" id="brief-weiter">Weiter bearbeiten</button><button type="button" class="btn btn--danger" id="brief-verwerfen-ja">Verwerfen</button>',
    'id="brief-editor-status" role="alert"', 'id="brief-gespeichert" role="status"'];
  let at = 0;
  for (const part of order) {
    const found = step.indexOf(part, at);
    assert.ok(found > at, `${part} after the one before`);
    at = found;
  }
  assert.match(step, /id="brief-verwerfen" role="group" aria-labelledby="brief-verwerfen-frage" hidden/);
  assert.doesNotMatch(step, /placeholder=/, "no placeholders");
});

test("the step «Unterlagen erstellen und prüfen» has the hint while the letter is open", () => {
  assert.match(html, /id="pruefen" hidden>Erneut prüfen<\/button><\/div>\s*<p class="status-line" id="dossier-meldung"[^>]*><\/p>\s*<p class="status-line" id="brief-offen-hinweis" hidden>Das Anschreiben ist noch offen: zuerst speichern oder abbrechen\.<\/p>/);
});

test("the page loads the editor after the finding row and before bewerbung.js; the server hands the files out", () => {
  const at = name => html.indexOf(`src="/${name}"`);
  assert.ok(at("finding-row.js") < at("letter-editor-logik.js") && at("letter-editor-logik.js") < at("letter-editor.js")
    && at("letter-editor.js") < at("bewerbung.js"));
  assert.match(html, /<link rel="stylesheet" href="\/letter-editor.css">/);
  const app = fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8");
  for (const name of ["letter-editor.js", "letter-editor-logik.js", "letter-editor.css"]) assert.match(app, new RegExp(`"/${name}": "${name}"`));
});

test("bewerbung.js hands over data and reload, cuts through the editor and does not grow", () => {
  const page = lies("bewerbung.js");
  assert.match(page, /E\.update\(\{ letter: brief, findings: befunde, approval: freigabe, shown: zeigen \}\);/);
  assert.match(page, /onCut: E\.cut/);
  assert.match(page, /FindingRow\.longest\(absatz\(text\), E\.openAtLongest\)/);
  assert.match(page, /E\.connect\(laden\)/);
  assert.doesNotMatch(page, /anschreiben-aendern"\)\.href/);
  assert.ok(page.split("\n").length <= 779, "bewerbung.js stays at or below its size before the editor");
});

test("the styles follow the brief: column, longest rule, 44 px targets and a stacked row at 375 px", () => {
  const css = lies("letter-editor.css");
  assert.match(css, /\.letter-editor \{[^}]*display: flex; flex-direction: column; gap: var\(--space-4\);/);
  assert.match(css, /\.letter-editor__paragraphs \{[^}]*gap: var\(--space-3\);/);
  assert.match(css, /\.letter-editor__paragraph--longest \{[^}]*padding-left: var\(--space-3\); border-left: 3px solid var\(--accent\);/);
  assert.match(css, /\.letter-editor__field \{[^}]*field-sizing: content;[^}]*resize: vertical;[^}]*font-size: 16px; line-height: 1\.5;/);
  assert.match(css, /\.letter-editor__remove, \.letter-editor__add \{[^}]*min-height: 44px;/);
  const phone = css.slice(css.indexOf("@media (max-width: 600px)"));
  assert.match(phone, /\.letter-editor__actions \{ flex-direction: column; align-items: stretch; \}/);
  assert.doesNotMatch(css, /[:\s]#[0-9a-f]{3,8};|rgb\(|hsl\(/i, "only existing tokens");
});

test("at 375 px the saved and error lines keep their text full width, the button wraps below", () => {
  const phone = lies("letter-editor.css").split("@media (max-width: 600px)")[1] || "";
  assert.match(phone, /#brief-editor-status\.status--closable, #brief-gespeichert\.status--closable \{ flex-wrap: wrap; \}/);
  assert.match(phone, /#brief-editor-status \.status__text, #brief-gespeichert \.status__text \{ flex-basis: 100%; \}/);
});

test("the group «Längster Absatz» has a button «Anschreiben ändern» that calls the editor", () => {
  const source = lies("finding-row.js");
  assert.match(source, /el\("button", \{ type: "button", class: "btn btn--sm btn--quiet letter-longest__edit", onclick: onEdit \}, EDIT_LETTER\)/);
});

// Texts in the form of the set

test("the editor texts follow Sie, du and the apprenticeship", () => {
  assert.equal(Texte.text("anschreiben.editor-intro", "stelle-sie"), "Passen Sie den Text an die Stelle und die Firma an. Jeder Absatz hat ein eigenes Feld.");
  assert.equal(Texte.text("anschreiben.editor-intro", "stelle-du"), "Pass den Text an die Stelle und die Firma an. Jeder Absatz hat ein eigenes Feld.");
  assert.equal(Texte.text("anschreiben.editor-intro", "lehrstelle-du"), "Pass den Text an die Lehrstelle und den Lehrbetrieb an. Jeder Absatz hat ein eigenes Feld.");
  assert.equal(Texte.text("anschreiben.editor-freigabe", "lehrstelle-du"), "Mit dem Speichern ist die Freigabe aufgehoben; gib das Anschreiben danach neu frei.");
  assert.equal(Texte.text("anschreiben.editor-als-text", "stelle-du"), "Empfänger, Ort und Datum änderst du als Text.");
  assert.equal(Texte.text("anschreiben.gespeichert", "stelle-sie"), "Gespeichert. Erstellen Sie die Unterlagen neu, damit PDF und Prüfung den neuen Text zeigen.");
  assert.equal(Texte.text("anschreiben.nicht-erreichbar", "lehrstelle-du"), "Nicht gespeichert: Die App antwortet nicht. Der Text bleibt hier; versuch es nochmals.");
  assert.equal(Texte.text("anschreiben.geaendert", "stelle-du"), "Nicht gespeichert: Das Anschreiben hat sich inzwischen geändert, etwa durch einen neuen Entwurf. Kopier, was du behalten möchtest, und lade die Seite neu.");
  assert.match(html, /<span data-text="anschreiben.editor-als-text">Empfänger, Ort und Datum ändern Sie als Text.<\/span>/);
});

// Behaviour

test("«Anschreiben ändern» opens the editor with one field per paragraph and the focus on its title", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.byId["anschreiben-aendern"].click();
  assert.equal(p.byId["brief-editor"].hidden, false);
  assert.equal(p.byId["anschreiben-aendern"].getAttribute("aria-expanded"), "true");
  assert.deepEqual([...p.fields().map(f => f.value)], LETTER.absaetze);
  assert.deepEqual(p.fields().map(labelText), ["Absatz 1", "Absatz 2", "Absatz 3"]);
  assert.equal(p.fields()[0].getAttribute("rows"), "3");
  assert.equal(p.byId["brief-betreff"].value, LETTER.betreff);
  assert.equal(p.byId["brief-gruss"].value, LETTER.gruss);
  assert.equal(p.doc.activeElement, p.byId["brief-editor-titel"]);
  assert.equal(p.doc.scrolled.at(-1)[0], p.byId["brief-editor-titel"]);
  assert.equal(JSON.stringify(p.doc.scrolled.at(-1)[1]), JSON.stringify({ block: "start" }));
  assert.equal(p.byId["brief-als-text"].getAttribute("href"), "/inhalte?datei=bewerbungen%2Fmuster-ag%2Fanschreiben.yaml&ansicht=text");
  assert.equal(p.byId["brief-editor-intro"].textContent, Texte.text("anschreiben.editor-intro", "stelle-sie"));
});

const LOCKED = ["ki-entwerfen", "ki-pruefen", "erstellen", "pruefen"];

test("while open the read view hides and the buttons that would use the letter are locked, not disabled", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.byId.pruefen.disabled = true;  // the page disabled it; the editor leaves `disabled` alone
  p.E.open();
  assert.equal(p.E.isOpen(), true);
  for (const id of ["anschreiben-text", "ki-pruefung-teil", "freigabe-zeile", "freigabe-status"]) assert.equal(p.byId[id].hidden, true, id);
  for (const id of LOCKED) {
    assert.equal(p.byId[id].getAttribute("aria-disabled"), "true", id);
    assert.equal(p.byId[id].getAttribute("aria-describedby"), "brief-offen-hinweis", id);
  }
  assert.equal(p.byId.erstellen.disabled, false, "the editor never sets disabled");
  p.byId.erstellen.click();
  assert.equal(p.state.built, 0, "a click on a locked button does not reach its handler");
  assert.equal(p.byId["brief-offen-hinweis"].hidden, false);
  p.update();  // a reload while open draws the read view again; the editor hides it again
  assert.equal(p.byId["anschreiben-text"].hidden, true);
  p.byId["brief-abbrechen"].click();
  assert.equal(p.E.isOpen(), false);
  assert.equal(p.byId["anschreiben-text"].hidden, false);
  assert.equal(p.byId["ki-pruefung-teil"].hidden, true, "back as the page drew it");
  for (const id of LOCKED) {
    assert.equal(p.byId[id].getAttribute("aria-disabled"), null, id);
    assert.equal(p.byId[id].getAttribute("aria-describedby"), null, id);
  }
  assert.equal(p.byId.pruefen.disabled, true, "still as the page set it");
  assert.equal(p.byId["brief-offen-hinweis"].hidden, true);
  p.byId.erstellen.click();
  assert.equal(p.state.built, 1, "closed, the click goes through again");
});

test("ki.js turning its buttons on while the editor is open does not let «Anschreiben entwerfen» through", async () => {
  // ki.js sets `disabled` itself whenever its status loads; this is its line
  assert.match(lies("ki.js"), /const frei = an => KNOEPFE\.forEach\(k => \{ \$\(k\)\.disabled = !an; \}\);/);
  const p = page();
  await p.settle();
  p.update();
  let drafted = 0;
  p.byId["ki-entwerfen"].addEventListener("click", () => { drafted += 1; });
  p.E.open();
  for (const id of ["ki-bewerten", "ki-entwerfen", "ki-pruefen"]) if (p.byId[id]) p.byId[id].disabled = false;  // frei(true)
  p.byId["ki-entwerfen"].click();
  assert.equal(drafted, 0);
  const programmatic = p.byId.erstellen.dispatch("click");  // the «Nächster Schritt» card clicks it from code
  assert.equal(programmatic.defaultPrevented, true);
  assert.equal(p.state.built, 0);
});

test("a build that ends while the editor is open leaves «Unterlagen erstellen» usable after closing", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.byId.erstellen.disabled = true;  // a build is running
  p.E.open();
  p.byId.erstellen.disabled = false;  // the build ends (bewerbung.js, finally)
  p.byId["brief-abbrechen"].click();
  assert.equal(p.byId.erstellen.disabled, false);
  assert.equal(p.byId.erstellen.getAttribute("aria-disabled"), null);
});

test("the tile link «Anschreiben ändern» opens the editor with the focus on its title", async () => {
  const p = page();
  await p.settle();
  p.update();
  const tiles = tileStep(p);
  tiles.S.showTiles("muster-ag", { bewerbung: { id: "muster-ag" }, pdfs: { lebenslauf: true, anschreiben: true } }, 1);
  const link = tiles.pdfs.all().find(n => n.tagName === "A" && n.textContent === "Anschreiben ändern");
  const event = link.dispatch("click");
  assert.equal(event.defaultPrevented, true);
  assert.equal(p.byId["brief-editor"].hidden, false);
  assert.equal(p.doc.activeElement, p.byId["brief-editor-titel"]);
  assert.equal(p.doc.scrolled.at(-1)[0], p.byId["brief-editor-titel"]);
});

test("without a letter to edit, the tile link still leads to the step", async () => {
  const p = page();
  await p.settle();
  p.update(null);
  const tiles = tileStep(p);
  tiles.S.showTiles("muster-ag", { bewerbung: { id: "muster-ag" }, pdfs: { lebenslauf: true, anschreiben: true } }, 1);
  tiles.pdfs.all().find(n => n.tagName === "A" && n.textContent === "Anschreiben ändern").dispatch("click");
  assert.equal(p.byId["brief-editor"].hidden, true);
  assert.equal(p.doc.activeElement, p.byId["anschreiben-titel"]);
});

test("each field has its line hint, referenced by aria-describedby; an empty one falls away", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.E.open();
  assert.deepEqual(p.fields().map(f => hintOf(p, f).textContent), ["etwa 1 Zeile", "etwa 3 Zeilen", "etwa 1 Zeile"]);
  p.type(p.fields()[0], "  ");
  assert.equal(hintOf(p, p.fields()[0]).textContent, "Leer: fällt beim Speichern weg.");
  assert.equal(p.fields()[0].style.height, "98px", "it grows to its content where field-sizing is missing");
});

test("from «Im Anschreiben kürzen» the longest paragraph has the focus, the caret at its start", async () => {
  const p = page();
  await p.settle();
  p.update(LETTER, [OVER]);
  p.E.cut();
  const longest = p.fields()[1];
  assert.equal(p.doc.activeElement, longest);
  assert.equal(JSON.stringify(longest.selection), "[0,0]");
  assert.equal(p.doc.scrolled.at(-1)[0], longest);
  assert.equal(JSON.stringify(p.doc.scrolled.at(-1)[1]), JSON.stringify({ block: "center" }));
  assert.equal(labelText(longest), "Absatz 2 Längster Absatz");
  assert.ok(longest.parentNode.classList.contains("letter-editor__paragraph--longest"));
  p.fields()[2].focus();
  p.E.cut();  // already open: only the focus moves
  assert.equal(p.doc.activeElement, p.fields()[1]);
});

test("the group button opens the editor at the longest paragraph too", async () => {
  const p = page();
  await p.settle();
  p.update(LETTER, [OVER]);
  p.E.openAtLongest();
  assert.equal(p.doc.activeElement, p.fields()[1]);
});

test("without a letter, «Im Anschreiben kürzen» falls back to the step with the marked paragraph", async () => {
  const p = page();
  await p.settle();
  p.update(null, [OVER]);
  p.E.cut();
  assert.equal(p.byId["brief-editor"].hidden, true);
  assert.equal(p.doc.activeElement, p.byId["laengster-absatz"]);
});

test("the mark and the goal line follow the edits, only while the letter is over one page", async () => {
  const p = page();
  await p.settle();
  p.update(LETTER, [OVER]);
  p.E.open();
  assert.equal(p.byId["brief-ziel"].textContent, "Die Prüfung fand etwa 4 Zeilen zu viel.");
  p.type(p.fields()[1], "x".repeat(50));
  assert.equal(p.byId["brief-ziel"].textContent, "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 2 Zeilen weniger.");
  assert.equal(labelText(p.fields()[2]), "Absatz 3 Längster Absatz", "the mark moves live");
  assert.equal(labelText(p.fields()[1]), "Absatz 2");
  const q = page();
  await q.settle();
  q.update(LETTER, [{ ...OVER, bestaetigt: true }]);
  q.E.open();
  assert.equal(q.byId["brief-ziel"].hidden, true);
  assert.ok(q.fields().every(f => !labelText(f).includes("Längster")));
});

test("removing and adding paragraphs: numbers follow, focus moves, the last one cannot be removed", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.E.open();
  const removeOf = field => field.parentNode.querySelector("button");
  assert.equal(removeOf(p.fields()[1]).getAttribute("aria-label"), "Absatz 2 entfernen");
  removeOf(p.fields()[1]).click();
  assert.deepEqual(p.fields().map(f => f.value), [LETTER.absaetze[0], LETTER.absaetze[2]]);
  assert.deepEqual(p.fields().map(labelText), ["Absatz 1", "Absatz 2"]);
  assert.equal(p.doc.activeElement, p.fields()[1], "the next field");
  removeOf(p.fields()[1]).click();
  assert.equal(p.doc.activeElement, p.fields()[0], "the one before, as it was the last");
  assert.equal(removeOf(p.fields()[0]), null, "one paragraph left: no «Entfernen»");
  p.byId["brief-absatz-neu"].click();
  assert.equal(p.fields().length, 2);
  assert.equal(p.doc.activeElement, p.fields()[1]);
  assert.equal(p.fields()[1].value, "");
});

test("«Speichern» without changes closes and writes nothing", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.E.open();
  p.type(p.fields()[0], ` ${LETTER.absaetze[0]} `);
  p.byId["brief-editor"].dispatch("submit");
  await p.settle();
  assert.deepEqual(p.state.sent, []);
  assert.equal(p.byId["brief-editor"].hidden, true);
  assert.equal(p.doc.activeElement, p.byId["anschreiben-aendern"]);
});

test("a letter with every paragraph empty is refused on the page", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.E.open();
  p.fields().forEach(f => p.type(f, ""));
  p.byId["brief-editor"].dispatch("submit");
  await p.settle();
  assert.deepEqual(p.state.sent, []);
  assert.equal(p.byId["brief-editor-status"].textContent, "Das Anschreiben braucht mindestens einen Absatz mit Text.");
  assert.equal(p.fields()[0].getAttribute("aria-invalid"), "true");
  assert.equal(p.doc.activeElement, p.fields()[0]);
});

test("saving sends the edit, reloads, closes and offers to build anew with the focus there", async () => {
  const p = page({ satz: "stelle-du" });
  await p.settle();
  p.update(LETTER, null, { noetig: true, freigegeben: true });
  p.E.open();
  assert.equal(p.byId["brief-editor-intro"].textContent,
    `${Texte.text("anschreiben.editor-intro", "stelle-du")} ${Texte.text("anschreiben.editor-freigabe", "stelle-du")}`);
  p.type(p.fields()[1], "Kürzer.");
  const pending = p.byId["brief-editor"].dispatch("submit");
  assert.equal(pending.defaultPrevented, true);
  assert.equal(p.byId["brief-speichern"].disabled, true);
  assert.equal(p.byId["brief-speichern"].textContent, "Wird gespeichert …");
  await p.settle();
  assert.deepEqual(JSON.parse(JSON.stringify(p.state.sent)), [{ pfad: "/api/bewerbung/anschreiben", parameter: { id: "muster-ag" },
    body: { betreff: LETTER.betreff, anrede: LETTER.anrede, absaetze: [LETTER.absaetze[0], "Kürzer.", LETTER.absaetze[2]], gruss: LETTER.gruss, fingerabdruck: "f1" } }]);
  assert.equal(p.state.reloads, 1);
  assert.equal(p.byId["brief-editor"].hidden, true);
  assert.equal(p.byId["anschreiben-text"].hidden, false);
  assert.equal(p.byId["brief-speichern"].textContent, "Speichern");
  const line = p.byId["brief-gespeichert"];
  assert.equal(line.querySelector(".status__text").textContent, Texte.text("anschreiben.gespeichert", "stelle-du"));
  const rebuild = line.querySelector(".status__action");
  assert.equal(rebuild.textContent, "Unterlagen neu erstellen");
  assert.equal(p.doc.activeElement, rebuild);
  assert.equal(p.unload().defaultPrevented, false, "nothing left unsaved");
  rebuild.click();
  assert.equal(p.state.built, 1, "the same handler as «Unterlagen erstellen»");
  assert.equal(p.doc.scrolled.at(-1)[0], p.byId["s-pruefen"]);
});

test("the saved line goes on the next build and when the editor opens again", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.E.open();
  p.type(p.fields()[0], "Anders.");
  p.byId["brief-editor"].dispatch("submit");
  await p.settle();
  p.byId.erstellen.click();
  assert.equal(p.byId["brief-gespeichert"].textContent, "");
  p.E.open();
  p.type(p.fields()[0], "Nochmals anders.");
  p.byId["brief-editor"].dispatch("submit");
  await p.settle();
  assert.notEqual(p.byId["brief-gespeichert"].textContent, "");
  p.E.open();
  assert.equal(p.byId["brief-gespeichert"].textContent, "");
});

test("a letter changed meanwhile (409) keeps the text and offers «Neu laden»", async () => {
  const p = page({ failWith: Object.assign(new Error("Das Anschreiben hat sich inzwischen geändert."), { status: 409 }) });
  await p.settle();
  p.update();
  p.E.open();
  p.type(p.fields()[0], "Mein neuer Text.");
  p.byId["brief-editor"].dispatch("submit");
  await p.settle();
  const status = p.byId["brief-editor-status"];
  assert.equal(status.querySelector(".status__text").textContent, Texte.text("anschreiben.geaendert", "stelle-sie"));
  assert.equal(p.state.levels.get("brief-editor-status"), "fehler");
  assert.equal(p.fields()[0].value, "Mein neuer Text.");
  assert.equal(p.byId["brief-editor"].hidden, false);
  assert.equal(p.doc.activeElement, p.byId["brief-speichern"]);
  assert.equal(p.byId["brief-speichern"].disabled, false);
  assert.equal(p.unload().defaultPrevented, true, "leaving now would lose the text");
  status.querySelector(".status__action").click();
  assert.equal(p.state.reloaded, true);
  assert.equal(p.unload().defaultPrevented, false, "«Neu laden» was asked for");
});

test("an app that does not answer and a refusal say so and keep the text", async () => {
  const p = page({ failWith: new TypeError("Failed to fetch") });
  await p.settle();
  p.update();
  p.E.open();
  p.type(p.fields()[0], "Text.");
  p.byId["brief-editor"].dispatch("submit");
  await p.settle();
  assert.equal(p.byId["brief-editor-status"].textContent, Texte.text("anschreiben.nicht-erreichbar", "stelle-sie"));
  const q = page({ failWith: Object.assign(new Error("Diese Bewerbung ist schon versendet."), { status: 400 }) });
  await q.settle();
  q.update();
  q.E.open();
  q.type(q.fields()[0], "Text.");
  q.byId["brief-editor"].dispatch("submit");
  await q.settle();
  assert.equal(q.byId["brief-editor-status"].textContent, "Nicht gespeichert: Diese Bewerbung ist schon versendet. Der Text bleibt hier.");
});

test("«Abbrechen» without changes closes and returns to «Anschreiben ändern», also when opened at the longest", async () => {
  const p = page();
  await p.settle();
  p.update(LETTER, [OVER]);
  p.E.cut();
  p.byId["brief-abbrechen"].click();
  assert.equal(p.byId["brief-editor"].hidden, true);
  assert.equal(p.doc.activeElement, p.byId["anschreiben-aendern"]);
  assert.equal(p.byId["anschreiben-aendern"].getAttribute("aria-expanded"), "false");
});

test("«Abbrechen» with changes asks first; «Weiter bearbeiten» goes back, «Verwerfen» closes", async () => {
  const p = page();
  await p.settle();
  p.update();
  p.E.open();
  p.type(p.byId["brief-betreff"], "Anderer Betreff");
  p.byId["brief-betreff"].dispatch("input");
  assert.equal(p.unload().defaultPrevented, true, "leaving with changes asks");
  p.byId["brief-abbrechen"].click();
  assert.equal(p.byId["brief-aktionen"].hidden, true);
  assert.equal(p.byId["brief-verwerfen"].hidden, false);
  assert.equal(p.doc.activeElement, p.byId["brief-weiter"]);
  p.byId["brief-weiter"].click();
  assert.equal(p.byId["brief-verwerfen"].hidden, true);
  assert.equal(p.byId["brief-aktionen"].hidden, false);
  assert.equal(p.doc.activeElement, p.byId["brief-abbrechen"]);
  p.byId["brief-abbrechen"].click();
  p.byId["brief-verwerfen-ja"].click();
  assert.equal(p.byId["brief-editor"].hidden, true);
  assert.equal(p.doc.activeElement, p.byId["anschreiben-aendern"]);
  assert.deepEqual(p.state.sent, []);
  assert.equal(p.unload().defaultPrevented, false);
  p.E.open();
  assert.equal(p.byId["brief-betreff"].value, LETTER.betreff, "the next open starts from the saved letter");
  assert.equal(p.byId["brief-verwerfen"].hidden, true);
});

test("the longest paragraph of the bewerbung-logik finding and of the editor agree", () => {
  assert.equal(logik.longestParagraph([OVER]), L.longestIndex(LETTER.absaetze));
});
