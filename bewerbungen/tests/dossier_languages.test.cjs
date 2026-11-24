// The letter editor, the dossier dialog, greeting and thanks, and the mark of the dossier in French and English (#429,
// G10, docs/design/sprachen.md): what letter-editor(-logik).js, finding-row.js, dossier-texte.js,
// dossier-dialog(-logik).js and zeichen(-logik).js say at run time comes in the app language with the catalog in
// bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages. The mark names follow into Lebenslauf erstellen.
// Data (the letter, initials, colours as #rrggbb, messages of the server) stays as it is; German stays as it was.
// Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const L = require("../seiten/letter-editor-logik.js");
const D = require("../seiten/dossier-dialog-logik.js");
const Z = require("../seiten/zeichen-logik.js");
const C = require("../seiten/lebenslauf-erstellen-logik.js");
const DotLine = require("../seiten/dot-line.js");

const CATALOG = path.join(__dirname, "..", "sprachen");
const SEITEN = path.join(__dirname, "..", "seiten");
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);

/** What translation_catalog.for_page hands a page of one language: plain texts and text sets. */
function catalogFor(language) {
  const files = fs.readdirSync(CATALOG).filter(name => name.endsWith(".json"));
  const entries = Object.assign({}, ...files.map(name => JSON.parse(fs.readFileSync(path.join(CATALOG, name), "utf8"))));
  const texts = {};
  const sets = {};
  for (const [key, entry] of Object.entries(entries)) {
    if (key.startsWith(SET_PREFIX)) sets[key.slice(SET_PREFIX.length)] = entry[language];
    else texts[key] = entry[language];
  }
  return { sprache: language, texte: texts, saetze: sets };
}

async function inLanguage(language, check) {
  texte.setzeSprache(language, catalogFor(language));
  try {
    return await check();
  } finally {
    texte.setzeSprache();
  }
}

const inAll = async check => ({ de: await check(), fr: await inLanguage("fr", check), en: await inLanguage("en", check) });
const fr = text => text.replaceAll("~", NBSP);  // "~" stands for the no-break space French puts before « : ? ! ; » and inside « »

// ---------- letter-editor-logik.js ----------

test("the hint under a paragraph counts one line in the singular", async () => {
  const shown = await inAll(() => [L.lineHint("x".repeat(10), 80), L.lineHint("x".repeat(170), 80), L.lineHint("  ", 80)]);
  assert.deepEqual(shown.de, ["etwa 1 Zeile", "etwa 3 Zeilen", "Leer: fällt beim Speichern weg."]);
  assert.deepEqual(shown.fr, ["environ 1 ligne", "environ 3 lignes", fr("Vide~: disparaît à l'enregistrement.")]);
  assert.deepEqual(shown.en, ["about 1 line", "about 3 lines", "Empty: dropped when saving."]);
});

test("the goal line says what the check found and what was saved, in the app language", async () => {
  const shown = await inAll(() => [L.goalLine({ lines: 0 }, 12, 12), L.goalLine({ lines: 1 }, 12, 12),
    L.goalLine({ lines: 4 }, 12, 10), L.goalLine({ lines: 4 }, 12, 11), L.goalLine({ lines: 1 }, 12, 11),
    L.goalLine({ lines: 4 }, 12, 7), L.goalLine(null, 12, 7)]);
  assert.deepEqual(shown.de, ["Die Prüfung fand: Das Anschreiben ist länger als eine Seite.",
    "Die Prüfung fand etwa 1 Zeile zu viel.", "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 2 Zeilen weniger.",
    "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 1 Zeile weniger.",
    "Die Prüfung fand etwa 1 Zeile zu viel. Bisher etwa 1 Zeile weniger; ob es reicht, zeigt erst «Unterlagen erstellen».",
    "Die Prüfung fand etwa 4 Zeilen zu viel. Bisher etwa 5 Zeilen weniger; ob es reicht, zeigt erst «Unterlagen erstellen».", ""]);
  assert.deepEqual(shown.fr, [fr("La vérification a trouvé~: la lettre de motivation dépasse une page."),
    "La vérification a trouvé environ 1 ligne de trop.",
    "La vérification a trouvé environ 4 lignes de trop. Jusqu'ici, environ 2 lignes de moins.",
    "La vérification a trouvé environ 4 lignes de trop. Jusqu'ici, environ 1 ligne de moins.",
    fr("La vérification a trouvé environ 1 ligne de trop. Jusqu'ici, environ 1 ligne de moins~; seul «~Créer et vérifier les documents~» montre si cela suffit."),
    fr("La vérification a trouvé environ 4 lignes de trop. Jusqu'ici, environ 5 lignes de moins~; seul «~Créer et vérifier les documents~» montre si cela suffit."),
    ""]);
  assert.deepEqual(shown.en.slice(0, 3), ["The check found: the cover letter is longer than one page.",
    "The check found about 1 line too many.", "The check found about 4 lines too many. So far about 2 lines fewer."]);
  assert.equal(shown.en[5],
    "The check found about 4 lines too many. So far about 5 lines fewer; only “Create and check documents” shows whether that is enough.");
});

test("a refusal keeps the server's reason and says the text stays", async () => {
  const shown = await inAll(() => L.refusedText("Vom Server."));
  assert.deepEqual(shown, { de: "Nicht gespeichert: Vom Server. Der Text bleibt hier.",
    fr: fr("Non enregistré~: Vom Server. Le texte reste ici."), en: "Not saved: Vom Server. The text stays here." });
});

// ---------- dossier-dialog-logik.js ----------

test("after «Übernehmen» the page names the pages that fall away in the app language", async () => {
  const shown = await inAll(() => [D.savedMessage(true, null), D.savedMessage(false, { gruss: "", dank: "Danke" }),
    D.savedMessage(false, { gruss: "Hallo", dank: " " }), D.savedMessage(false, { gruss: "", dank: "" }),
    D.savedMessage(false, null)]);
  const saved = "Dossier übernommen. Mit «Unterlagen erstellen» entsteht es neu.";
  assert.deepEqual(shown.de, [saved, `${saved} Ohne Begrüssung entfällt die Seite dazu.`,
    `${saved} Ohne Dank entfällt die Seite dazu.`, `${saved} Ohne Begrüssung und Dank entfällt die Seite dazu.`, ""]);
  const appliedFr = fr("Dossier appliqué. «~Créer et vérifier les documents~» le recrée.");
  assert.deepEqual(shown.fr, [appliedFr, `${appliedFr} Sans accueil, la page correspondante disparaît.`,
    `${appliedFr} Sans remerciements, la page correspondante disparaît.`,
    `${appliedFr} Sans accueil ni remerciements, les pages correspondantes disparaissent.`, ""]);
  const appliedEn = "Dossier applied. “Create and check documents” creates it anew.";
  assert.deepEqual(shown.en, [appliedEn, `${appliedEn} Without a welcome, its page is left out.`,
    `${appliedEn} Without thanks, its page is left out.`, `${appliedEn} Without welcome and thanks, their pages are left out.`, ""]);
});

// ---------- zeichen-logik.js ----------

const ALLE = design => ({ deckblatt: design, anschreiben: design, lebenslauf: design, weitere: design });
const zustand = (felder = {}) => ({ zeichen: "passend", akzent: "passend", initialen: "", initialen_wirksam: "LB", logo: null, ...felder });

test("the marks, their sentences and the reason one is blocked come in the app language", async () => {
  const shown = await inAll(() => [Z.VARIANTEN.map(v => [v.wert, v.name, v.satz]), Z.gesperrt("verschraenkt", "L"), Z.NUR_ZWEI]);
  assert.deepEqual(shown.de[0], [["passend", "Passend zum Design", undefined], ["ring", "Ring", "Initialen im Ring"],
    ["block", "Block", "Initialen in einer Fläche"], ["verschraenkt", "Verschränkt", "Zwei Buchstaben ineinander"],
    ["linie", "Linie", "Initialen auf einer Linie"], ["punkt", "Punkt", "Punkt vor den Initialen"]]);
  assert.deepEqual(shown.fr[0], [["passend", "Assortie au design", undefined], ["ring", "Anneau", "Initiales dans un anneau"],
    ["block", "Bloc", "Initiales sur un aplat de couleur"], ["verschraenkt", "Entrelacé", "Deux lettres entrelacées"],
    ["linie", "Ligne", "Initiales sur une ligne"], ["punkt", "Point", "Point devant les initiales"]]);
  assert.deepEqual(shown.en[0], [["passend", "Matching the design", undefined], ["ring", "Ring", "Initials in a ring"],
    ["block", "Block", "Initials on a solid area"], ["verschraenkt", "Intertwined", "Two letters intertwined"],
    ["linie", "Line", "Initials on a line"], ["punkt", "Dot", "Dot before the initials"]]);
  assert.deepEqual([shown.de.slice(1), shown.fr.slice(1), shown.en.slice(1)], [
    ["Nur mit zwei Buchstaben", "Nur mit zwei Buchstaben"], ["Seulement avec deux lettres", "Seulement avec deux lettres"],
    ["Only with two letters", "Only with two letters"]]);
});

test("designs and colours are named in the app language, the colour values stay", async () => {
  const shown = await inAll(() => [["siegel", "raster", "register", "unbekannt"].map(Z.designName),
    Z.FARBEN.map(f => [f.name, f.farbe]), Z.hauptfarbe("raster").name]);
  assert.deepEqual(shown.de[0], ["Siegel", "Raster", "Register", "Siegel"]);
  assert.deepEqual(shown.fr[0], ["Sceau", "Trame", "Registre", "Sceau"]);
  assert.deepEqual(shown.en[0], ["Seal", "Grid", "Register", "Seal"]);
  assert.deepEqual(shown.de[1].map(([name]) => name), ["Schieferblau", "Weinrot", "Tannengrün", "Petrol", "Aubergine", "Bronze", "Graphit"]);
  assert.deepEqual(shown.fr[1], [["Bleu ardoise", "#38495d"], ["Bordeaux", "#7a2e3a"], ["Vert sapin", "#2f5d50"],
    ["Pétrole", "#1d5c6b"], ["Aubergine", "#5b3f6b"], ["Bronze", "#7a5418"], ["Graphite", "#3a3d42"]]);
  assert.deepEqual(shown.en[1].map(([name]) => name), ["Slate blue", "Wine red", "Fir green", "Petrol", "Aubergine", "Bronze", "Graphite"]);
  assert.deepEqual([shown.de[2], shown.fr[2], shown.en[2]], ["Weinrot", "Bordeaux", "Wine red"]);
});

test("the check of an own colour says why in the app language", async () => {
  const shown = await inAll(() => ["rot", "#e0b84a", "#7f7f7f", "#38495d", "#e8e4dc"].map(farbe => Z.pruefeFarbe(farbe).meldung));
  assert.deepEqual(shown.de, ["Bitte eine Farbe wie #38495d eingeben.",
    "Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht.",
    "Weder weisse noch dunkle Schrift ist auf dieser Farbe gut lesbar. Gespeichert wird sie nicht.",
    "Gut lesbar: weisse Schrift auf der Farbe, Linien gut sichtbar auf dem Papier.",
    "Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht."]);
  assert.deepEqual(shown.fr, ["Merci de saisir une couleur comme #38495d.",
    fr("Trop clair~: l'anneau, les lignes et les points seraient à peine visibles sur le papier. Cette couleur n'est pas enregistrée."),
    "Ni un texte blanc ni un texte foncé ne se lit bien sur cette couleur. Elle n'est pas enregistrée.",
    fr("Bien lisible~: texte blanc sur la couleur, lignes bien visibles sur le papier."),
    fr("Trop clair~: l'anneau, les lignes et les points seraient à peine visibles sur le papier. Cette couleur n'est pas enregistrée.")]);
  assert.deepEqual(shown.en.slice(0, 4), ["Please enter a colour such as #38495d.",
    "Too light: ring, lines and dots would hardly show on the paper. This colour is not saved.",
    "Neither white nor dark text reads well on this colour. It is not saved.",
    "Easy to read: white text on the colour, lines clearly visible on the paper."]);
});

test("the sentence under the design, the preview label and the colour names follow the app language", async () => {
  const gemischt = { ...ALLE("siegel"), deckblatt: "raster" };
  const logo = { farbe: "#a35a2b" };
  const shown = await inAll(() => [Z.satzUnterDesign(zustand(), ALLE("siegel")), Z.satzUnterDesign(zustand(), gemischt),
    Z.satzUnterDesign(zustand({ akzent: "#1d5c6b" }), ALLE("register")),
    Z.satzUnterDesign(zustand({ zeichen: "ring" }), ALLE("raster")),
    Z.satzUnterDesign(zustand({ zeichen: "logo", akzent: "#a35a2b", logo }), ALLE("raster"), true),
    Z.satzUnterDesign(zustand({ zeichen: "logo", akzent: "#123456", logo }), ALLE("raster")),
    [Z.zeichenWorte(zustand({ zeichen: "block" }), "siegel"), Z.zeichenWorte(zustand({ zeichen: "verschraenkt" }), "siegel"),
      Z.zeichenWorte(zustand({ zeichen: "linie" }), "siegel")],
    Z.vorschauLabel(zustand(), "raster"), Z.passendSatz("register")]);
  assert.deepEqual(shown.de, [["Zeichen: Ring mit LB", "Akzentfarbe: Schieferblau", "beides passend zu Siegel"],
    ["Zeichen: passend zum Design jeder Seite", "Akzentfarbe: Weinrot, passend zum Deckblatt in Raster"],
    ["Zeichen: Punkt mit LB im Anhänger, passend zu Register", "Akzentfarbe: Petrol"],
    ["Zeichen: Ring mit LB", "Akzentfarbe: Weinrot, passend zu Raster"],
    ["Zeichen: Dein Logo", "Akzentfarbe: Aus dem Logo (#a35a2b)"], ["Zeichen: Ihr Logo", "Akzentfarbe: Eigene Farbe (#123456)"],
    ["Block mit LB", "LB verschränkt", "LB auf einer Linie"], "Vorschau Deckblatt: Raster, Initialen im Band, Weinrot",
    "Punkt bei Register, wie das Design es vorsieht"]);
  assert.deepEqual(shown.fr, [[fr("Emblème~: Anneau avec LB"), fr("Couleur d'accent~: Bleu ardoise"), "les deux assortis à Sceau"],
    [fr("Emblème~: assorti au design de chaque page"), fr("Couleur d'accent~: Bordeaux, assortie à la page de garde en Trame")],
    [fr("Emblème~: Point avec LB sur l'étiquette, assorti à Registre"), fr("Couleur d'accent~: Pétrole")],
    [fr("Emblème~: Anneau avec LB"), fr("Couleur d'accent~: Bordeaux, assortie à Trame")],
    [fr("Emblème~: Ton logo"), fr("Couleur d'accent~: Du logo (#a35a2b)")],
    [fr("Emblème~: Votre logo"), fr("Couleur d'accent~: Couleur personnalisée (#123456)")],
    ["Bloc avec LB", "LB entrelacées", "LB sur une ligne"], fr("Aperçu de la page de garde~: Trame, Initiales dans le bandeau, Bordeaux"),
    "Point pour Registre, comme le prévoit le design"]);
  assert.deepEqual(shown.en, [["Mark: Ring with LB", "Accent colour: Slate blue", "both matching Seal"],
    ["Mark: matching the design of each page", "Accent colour: Wine red, matching the cover page in Grid"],
    ["Mark: Dot with LB on the tag, matching Register", "Accent colour: Petrol"],
    ["Mark: Ring with LB", "Accent colour: Wine red, matching Grid"],
    ["Mark: Your logo", "Accent colour: From the logo (#a35a2b)"], ["Mark: Your logo", "Accent colour: Custom colour (#123456)"],
    ["Block with LB", "LB intertwined", "LB on a line"], "Cover page preview: Grid, Initials in the band, Wine red",
    "Dot for Register, as the design intends"]);
});

// ---------- the mark names in Lebenslauf erstellen (lebenslauf-erstellen-logik.js) ----------

const CV_ANSWER = {
  stand: "abc", abschnitte: [], berufsbezeichnung: "Planerin", kurzprofil: "", design: "zweispaltig", bezeichnung: "",
  aussehen: { foto: true, zeichen: "verschraenkt", akzent: "#5b3f6b" },
  aussehen_angebot: { foto_vorhanden: true, initialen: "EKB", logo: false },
};

test("Lebenslauf erstellen names the marks of the dossier in the app language, also in its line", async () => {
  // As the page's `word`: keys of texte.js become words, the mark names come translated (lebenslauf-erstellen.js)
  const say = key => (key.startsWith("lebenslauf.") ? texte.text(key, "stelle-sie") : key);
  const shown = await inAll(() => {
    const state = C.setLook(C.start(CV_ANSWER), { zeichen: "ring" });
    const choices = C.markChoices(state).map(choice => [choice.id, say(choice.name), choice.note, choice.locked && say(choice.locked)]);
    return [choices.slice(1, 4), C.lookParts(state, say)];
  });
  assert.deepEqual(shown.de, [[["ring", "Ring", "Initialen im Ring", null], ["block", "Block", "Initialen in einer Fläche", null],
    ["verschraenkt", "Verschränkt", "Zwei Buchstaben ineinander", "Nur mit zwei Buchstaben"]], ["Zeichen: Ring", "Farbe: Aubergine"]]);
  assert.deepEqual(shown.fr, [[["ring", "Anneau", "Initiales dans un anneau", null], ["block", "Bloc", "Initiales sur un aplat de couleur", null],
    ["verschraenkt", "Entrelacé", "Deux lettres entrelacées", "Seulement avec deux lettres"]],
    [fr("Emblème~: Anneau"), fr("Couleur~: Aubergine")]]);
  assert.deepEqual(shown.en[0][2], ["verschraenkt", "Intertwined", "Two letters intertwined", "Only with two letters"]);
  assert.deepEqual(shown.en[1], ["Mark: Ring", "Colour: Aubergine"]);
});

// ---------- the scripts on a stand-in page ----------

class Node {
  constructor(tag = "div", attrs = {}) {
    Object.assign(this, { tag, attrs: { ...attrs }, children: [], listeners: {}, hidden: false, disabled: false, value: "",
                          placeholder: "", src: "", dataset: {}, style: {}, parentNode: null, open: false });
    this.classList = { toggle() {}, add() {}, remove() {}, contains: () => false };
  }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  removeAttribute(name) { delete this.attrs[name]; }
  append(...items) {
    for (const item of items.flat(Infinity)) {
      if (item === null || item === undefined || item === false) continue;
      if (item instanceof Node) item.parentNode = this;
      this.children.push(item);
    }
  }
  replaceChildren(...items) { this.children = []; this.append(...items); }
  get textContent() { return this.children.map(child => (child instanceof Node ? child.textContent : String(child))).join(""); }
  set textContent(value) { this.children = [String(value)]; }
  all() { return this.children.filter(child => child instanceof Node).flatMap(child => [child, ...child.all()]); }
  querySelectorAll(selector) {
    const matches = selector.startsWith(".")
      ? node => (node.attrs.class || "").split(" ").includes(selector.slice(1)) : node => node.tag === selector;
    return this.all().filter(matches);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  async fire(type, extra = {}) {
    const event = { type, target: this, currentTarget: this, preventDefault() {}, stopImmediatePropagation() {}, ...extra };
    for (const handler of this.listeners[type] || []) await handler(event);
  }
  focus() {}
  scrollIntoView() {}
  setSelectionRange() {}
  showModal() { this.open = true; }
  close() { this.open = false; }
  click() { return this.fire("click"); }
}

const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };

/** Runs page scripts against a stand-in page with `app` merged into window.App and `extra` into window. */
function run(names, { app = {}, extra = {}, satz = "stelle-sie" } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, new Node("div", { id })); return elements.get(id); };
  const handlers = {};
  const document = {
    getElementById: $, createElementNS: (ns, tag) => new Node(tag), createTextNode: text => String(text),
    addEventListener: (type, handler) => { (handlers[type] ||= []).push(handler); },
    dispatchEvent: event => (handlers[event.type] || []).forEach(handler => handler(event)), documentElement: { dataset: {} },
  };
  const status = (target, text = "") => { target.textContent = text; };
  const window = {
    App: { el: (tag, attrs, ...children) => { const node = new Node(tag, attrs || {}); node.append(...children); return node; },
           status, textsatz: async () => satz, url: (pfad, werte) => `${pfad}?${new URLSearchParams(werte)}`,
           holen: async () => ({}), senden: async () => ({}), bestaetigen: () => {}, ...app },
    Texte: texte, DotLine, ZeichenLogik: Z, LetterEditorLogik: L, DossierDialogLogik: D,
    Meldungen: { zeige: status, isInputRejection: () => false, clearOnInput() {} },
    addEventListener() {}, ...extra,
  };
  const context = { window, document, URLSearchParams, location: { search: "?id=muster-ag", reload() {} }, console, setTimeout,
    CSS: { supports: () => true }, CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } } };
  vm.createContext(context);
  for (const name of names) vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  const load = bewerbung => document.dispatchEvent({ type: "bewerbung-geladen", detail: { bewerbung } });
  return { $, window, load };
}

const LETTER = { betreff: "Bewerbung als Planerin", anrede: "Guten Tag", gruss: "Freundliche Grüsse", fingerabdruck: "f1",
                 absaetze: ["Erster Absatz, frei erfunden.", "Zweiter Absatz, ebenfalls erfunden."], zeichen_pro_zeile: 80 };

test("the letter editor names its paragraphs and buttons in the app language, the letter stays as written", async () => {
  const shown = await inAll(async () => {
    const page = run(["letter-editor.js"]);
    page.window.LetterEditor.update({ letter: LETTER, findings: [], approval: null, shown: true });
    page.window.LetterEditor.open();
    const blocks = page.$("brief-absaetze").children;
    const label = blocks[1].querySelector("label").textContent;
    const remove = blocks[1].querySelector("button");
    const hint = blocks[0].querySelector("p").textContent;
    return [label, remove.getAttribute("aria-label"), remove.textContent, hint, blocks[0].querySelector("textarea").value,
      page.$("brief-editor-intro").textContent];
  });
  assert.deepEqual(shown.de, ["Absatz 2", "Absatz 2 entfernen", "Entfernen", "etwa 1 Zeile", "Erster Absatz, frei erfunden.",
    "Passen Sie den Text an die Stelle und die Firma an. Jeder Absatz hat ein eigenes Feld."]);
  assert.deepEqual(shown.fr, ["Paragraphe 2", "Retirer le paragraphe 2", "Retirer", "environ 1 ligne", "Erster Absatz, frei erfunden.",
    "Adaptez le texte au poste et à l'entreprise. Chaque paragraphe a son propre champ."]);
  assert.deepEqual(shown.en, ["Paragraph 2", "Remove paragraph 2", "Remove", "about 1 line", "Erster Absatz, frei erfunden.",
    "Adapt the text to the job and the company. Each paragraph has a field of its own."]);
});

test("the letter editor refuses a letter without text and says it is saving in the app language", async () => {
  const shown = await inAll(async () => {
    let busy = "";
    const page = run(["letter-editor.js"], { app: { senden: async () => { busy = page.$("brief-speichern").textContent; return { geaendert: true }; } } });
    page.window.LetterEditor.update({ letter: LETTER, findings: [], approval: null, shown: true });
    page.window.LetterEditor.open();
    const fields = page.$("brief-absaetze").querySelectorAll("textarea");
    fields.forEach(field => { field.value = " "; field.fire("input"); });
    await page.$("brief-editor").fire("submit");
    const refused = page.$("brief-editor-status").textContent;
    fields[0].value = "Neu.";
    await fields[0].fire("input");
    await page.$("brief-editor").fire("submit");
    await settle();
    return [refused, busy, page.$("brief-speichern").textContent];
  });
  assert.deepEqual(shown.de, ["Das Anschreiben braucht mindestens einen Absatz mit Text.", "Wird gespeichert …", "Speichern"]);
  assert.deepEqual(shown.fr, ["La lettre de motivation doit contenir au moins un paragraphe avec du texte.", "Enregistrement…", "Enregistrer"]);
  assert.deepEqual(shown.en, ["The cover letter needs at least one paragraph with text.", "Saving…", "Save"]);
});

test("the editor's text sets speak tu in French where the set says du", async () => {
  const keys = ["anschreiben.editor-intro", "anschreiben.editor-freigabe", "anschreiben.gespeichert", "anschreiben.nicht-erreichbar",
    "anschreiben.geaendert"];
  const du = await inLanguage("fr", () => keys.map(key => texte.text(key, "stelle-du")));
  assert.deepEqual(du, ["Adapte le texte au poste et à l'entreprise. Chaque paragraphe a son propre champ.",
    fr("L'enregistrement annule la validation~; valide ensuite à nouveau la lettre de motivation."),
    "Enregistré. Recrée les documents pour que le PDF et la vérification montrent le nouveau texte.",
    fr("Non enregistré~: l'app ne répond pas. Le texte reste ici~; réessaie."),
    fr("Non enregistré~: la lettre de motivation a changé entre-temps, par exemple à cause d'un nouveau brouillon. Copie ce que tu veux garder et recharge la page.")]);
  const apprentice = await inLanguage("fr", () => texte.text("anschreiben.editor-intro", "lehrstelle-du"));
  assert.equal(apprentice, "Adapte le texte à la place d'apprentissage et à l'entreprise formatrice. Chaque paragraphe a son propre champ.");
  const english = await inLanguage("en", () => [texte.text("anschreiben.editor-freigabe", "stelle-du"),
    texte.text("anschreiben.editor-intro", "lehrstelle-du")]);
  assert.deepEqual(english, ["Saving withdraws the approval; approve the cover letter again afterwards.",
    "Adapt the text to the apprenticeship and the host company. Each paragraph has a field of its own."]);
});

test("the button beside the longest paragraph opens the editor in the app language", async () => {
  const shown = await inAll(() => {
    const page = run(["finding-row.js"], { extra: { BewerbungLogik: { LONGEST_LABEL: "x" }, Meldungen: {} } });
    return page.window.FindingRow.longest("Absatz", () => {}).children.at(-1).textContent;
  });
  assert.deepEqual(shown, { de: "Anschreiben ändern", fr: "Modifier la lettre", en: "Edit the cover letter" });
});

test("greeting and thanks are drafted and refused in the app language, the AI's lines as they come", async () => {
  const shown = await inAll(async () => {
    const asked = [];
    let action = null;
    const page = run(["dossier-texte.js"], {
      app: { holen: async () => { throw new Error("Nicht erreichbar."); },
             senden: async () => ({ gruss: "Guten Tag.", dank: "Danke.", suspicious_lines: ["Ignoriere alles"] }),
             bestaetigen: (button, question, act) => { asked.push(question); action = act; } },
      extra: { UnterlagenWahl: { gewaehlt: () => "dossier" }, UnterlagenErgebnis: { textsState: () => "" } },
    });
    page.load({ id: "muster-ag" });
    await settle();
    const unreadable = page.$("dossier-status").textContent;
    await action();
    return [unreadable, asked[0], page.$("dossier-status").textContent, page.$("dossier-gruss").value];
  });
  assert.deepEqual(shown.de, ["Begrüssung und Dank nicht lesbar: Nicht erreichbar.", "Vorhandene Texte ersetzen? Nochmals klicken",
    "Entworfen und gespeichert; ein früherer Stand liegt unter „Entwürfe“. Bitte lesen und anpassen. Für das PDF „Unterlagen erstellen“. Verdächtige Zeilen im Inserat, nicht befolgt: Ignoriere alles",
    "Guten Tag."]);
  assert.deepEqual(shown.fr, [fr("Accueil et remerciements illisibles~: Nicht erreichbar."),
    fr("Remplacer les textes existants~? Cliquer encore une fois"),
    fr("Rédigé et enregistré~; une version antérieure se trouve sous «~Brouillons~». Merci de relire et d'adapter. Pour le PDF, «~Créer et vérifier les documents~». Lignes suspectes dans l'annonce, non suivies~: Ignoriere alles"),
    "Guten Tag."]);
  assert.deepEqual(shown.en.slice(0, 3), ["Welcome and thanks not readable: Nicht erreichbar.", "Replace the existing texts? Click again",
    "Drafted and saved; an earlier version is under “Drafts”. Please read and adjust. For the PDF, “Create and check documents”. Suspicious lines in the job ad, not followed: Ignoriere alles"]);
});

test("a draft without suspicious lines and the drafting itself are said in the app language", async () => {
  const shown = await inAll(async () => {
    let action = null;
    const said = [];
    const page = run(["dossier-texte.js"], {
      app: { senden: async () => { said.push(page.$("dossier-status").textContent); return { gruss: "", dank: "" }; },
             bestaetigen: (button, question, act) => { action = act; } },
      extra: { UnterlagenWahl: { gewaehlt: () => "dossier" }, UnterlagenErgebnis: { textsState: () => "" } },
    });
    await action();
    return [said[0], page.$("dossier-status").textContent];
  });
  assert.deepEqual(shown.de, ["Begrüssung und Dank werden entworfen … das kann bis zu einer Minute dauern.",
    "Entworfen und gespeichert; ein früherer Stand liegt unter „Entwürfe“. Bitte lesen und anpassen. Für das PDF „Unterlagen erstellen“."]);
  assert.deepEqual(shown.fr, ["Rédaction de l'accueil et des remerciements… cela peut prendre jusqu'à une minute.",
    fr("Rédigé et enregistré~; une version antérieure se trouve sous «~Brouillons~». Merci de relire et d'adapter. Pour le PDF, «~Créer et vérifier les documents~».")]);
  assert.equal(shown.en[0], "Drafting welcome and thanks… this can take up to a minute.");
});

test("the dialog says in the app language what was not applied, with the server's reason", async () => {
  const shown = await inAll(async () => {
    const page = run(["dossier-dialog.js"], {
      app: { senden: async () => { throw new Error("Die App antwortet nicht"); } },
      extra: { UnterlagenWahl: { entwurf: () => ({ design: "siegel", seiten: {} }), gemischt: () => false,
                                 entwurfSpeichern: () => ({ id: "muster-ag" }) },
               DossierTexte: { oeffnen() {}, geaendert: () => false, speichern: async () => null, verwerfen() {} } },
    });
    page.$("dossier-dialog").querySelectorAll = () => [];
    page.load({ id: "muster-ag", unterlagen: "dossier" });
    page.window.DossierDialog.open(null);
    await page.$("dossier-uebernehmen").fire("click");
    return page.$("dossier-dialog-status").textContent;
  });
  assert.deepEqual(shown, { de: "Nicht übernommen: Die App antwortet nicht", fr: fr("Non appliqué~: Die App antwortet nicht"),
    en: "Not applied: Die App antwortet nicht" });
});

const MARK_STATE = { zeichen: "passend", akzent: "passend", initialen: "", initialen_wirksam: "EKB", lebenslauf: true,
  logo: { version: "v1", vektor: false, breite: 640, hoehe: 200, durchsichtig: true, farbe: "#a35a2b",
          hinweise: ["Vom Server."] } };

async function markPage(satz, state = MARK_STATE, app = {}) {
  const page = run(["zeichen.js"], {
    satz, app: { holen: async () => state, ...app },
    extra: { UnterlagenWahl: { gewaehlt: () => "dossier", seitenDesigns: () => ALLE("raster") } },
  });
  await settle();
  page.load({ id: "muster-ag", unterlagen: "dossier" });
  await settle();
  return page;
}

const tileTexts = page => page.$("d-zeichen-liste").children.map(tile => tile.children.at(-1).textContent);
const swatchTexts = page => page.$("d-akzent-liste").children.map(swatch => swatch.children.at(-1).textContent);

test("the marks of the dialog, its colours and its logo are named in the app language", async () => {
  const shown = await inAll(async () => {
    const page = await markPage("stelle-du");
    return [tileTexts(page), swatchTexts(page), page.$("d-logo-waehlen").textContent, page.$("d-logo-info").textContent,
      page.$("d-vorschau-text").textContent, page.$("d-vorschau").getAttribute("aria-label"), page.$("d-logo-hinweise").textContent];
  });
  assert.deepEqual(shown.de[0], ["Passend zum DesignBlock bei Raster, wie das Design es vorsieht", "RingInitialen im Ring",
    "BlockInitialen in einer Fläche", "VerschränktZwei Buchstaben ineinanderNur mit zwei Buchstaben", "LinieInitialen auf einer Linie",
    "PunktPunkt vor den Initialen", "Eigenes LogoDein Logo statt der Initialen"]);
  assert.deepEqual(shown.fr[0], ["Assortie au designBloc pour Trame, comme le prévoit le design", "AnneauInitiales dans un anneau",
    "BlocInitiales sur un aplat de couleur", "EntrelacéDeux lettres entrelacéesSeulement avec deux lettres",
    "LigneInitiales sur une ligne", "PointPoint devant les initiales", "Logo personnelTon logo à la place des initiales"]);
  assert.deepEqual(shown.en[0].at(-1), "Own logoYour logo instead of the initials");
  assert.deepEqual(shown.de[1].slice(0, 2), ["Passend zum DesignWeinrot, Farbe von Raster", "Schieferblau"]);
  assert.deepEqual(shown.fr[1].slice(0, 2).concat(shown.fr[1].slice(-2)), ["Assortie au designBordeaux, couleur de Trame", "Bleu ardoise",
    "Du logo#a35a2b", "Couleur personnalisée"]);
  assert.deepEqual(shown.en[1].slice(-2), ["From the logo#a35a2b", "Custom colour"]);
  assert.deepEqual(shown.de.slice(2), ["Anderes Logo wählen", `Dein Logo${NBSP}·, 640 × 200 Pixel, durchsichtig`,
    "Deckblatt und Folgeseite in Raster. Vereinfacht; das PDF entsteht mit «Unterlagen erstellen».",
    "Vorschau Deckblatt: Raster, Initialen im Band, Weinrot", "Vom Server."]);
  assert.deepEqual(shown.fr.slice(2), ["Choisir un autre logo", `Ton logo${NBSP}·, 640 × 200 pixels, transparent`,
    fr("Page de garde et page suivante en Trame. Simplifié~; le PDF est créé avec «~Créer et vérifier les documents~»."),
    fr("Aperçu de la page de garde~: Trame, Initiales dans le bandeau, Bordeaux"), "Vom Server."]);
  assert.deepEqual(shown.en.slice(2, 5), ["Choose another logo", `Your logo${NBSP}·, 640 × 200 pixels, transparent`,
    "Cover page and following page in Grid. Simplified; the PDF is created with “Create and check documents”."]);
});

test("without a logo the dialog asks for one first, a vector logo is named as such", async () => {
  const shown = await inAll(async () => {
    const without = await markPage("stelle-sie", { ...MARK_STATE, logo: null });
    const vector = await markPage("stelle-sie", { ...MARK_STATE, logo: { ...MARK_STATE.logo, vektor: true, durchsichtig: false } });
    return [tileTexts(without).at(-1), without.$("d-logo-waehlen").textContent, vector.$("d-logo-info").textContent];
  });
  assert.deepEqual(shown.de, ["Eigenes LogoIhr Logo statt der InitialenZuerst ein Logo wählen.", "Logo wählen", `Ihr Logo${NBSP}·, Vektorgrafik`]);
  assert.deepEqual(shown.fr, ["Logo personnelVotre logo à la place des initialesChoisir d'abord un logo.", "Choisir un logo",
    `Votre logo${NBSP}·, Graphique vectoriel`]);
  assert.deepEqual(shown.en, ["Own logoYour logo instead of the initialsChoose a logo first.", "Choose logo", `Your logo${NBSP}·, Vector graphic`]);
});

test("the dialog's own colour check and its refusals come in the app language, the server's reason as it comes", async () => {
  const shown = await inAll(async () => {
    const page = await markPage("stelle-sie", { ...MARK_STATE, akzent: "#e0b84a" }, {
      senden: async () => { throw new Error("Vom Server."); },
    });
    const check = page.$("d-eigene-farbe-pruefung").textContent;
    await page.$("d-zeichen-liste").fire("change", { target: { value: "ring" } });
    const refused = page.$("d-zeichen-status").textContent;
    const broken = run(["zeichen.js"], { app: { holen: async () => { throw new Error("Kaputt."); } },
      extra: { UnterlagenWahl: { gewaehlt: () => "dossier", seitenDesigns: () => ALLE("siegel") } } });
    broken.load({ id: "muster-ag", unterlagen: "dossier" });
    await settle();
    return [check.replace(/#[0-9a-f]{6}$/, "#…"), refused, broken.$("d-zeichen-status").textContent];
  });
  assert.deepEqual(shown.de, ["Zu hell: Ring, Linien und Punkte wären auf dem Papier kaum zu sehen. Gespeichert wird diese Farbe nicht. Vorschlag #…",
    "Nicht gespeichert. Vom Server.", "Zeichen und Farbe nicht lesbar: Kaputt."]);
  assert.deepEqual(shown.fr, [fr("Trop clair~: l'anneau, les lignes et les points seraient à peine visibles sur le papier. Cette couleur n'est pas enregistrée. Proposition~: #…"),
    "Non enregistré. Vom Server.", fr("Emblème et couleur illisibles~: Kaputt.")]);
  assert.deepEqual(shown.en, ["Too light: ring, lines and dots would hardly show on the paper. This colour is not saved. Suggestion: #…",
    "Not saved. Vom Server.", "Mark and colour not readable: Kaputt."]);
});
