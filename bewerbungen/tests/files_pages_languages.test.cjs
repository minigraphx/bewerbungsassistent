// Lebenslauf und Dateien, Foto, Entwürfe, Inhalte and Fragen in French and English (#430, G10,
// docs/design/sprachen.md): what dateien(-logik).js, foto.js, entwuerfe(-logik).js, inhalte.js and fragen.js say at run
// time comes in the app language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages.
// Data stays as it is: file names, stored kinds and their values, titles and messages from the server, the answer of
// the AI. German stays as it was. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const D = require("../seiten/dateien-logik.js");
const E = require("../seiten/entwuerfe-logik.js");
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

// ---------- dateien-logik.js ----------

test("the kinds of files, the notes on variants and photos come in the app language", async () => {
  const one = [{ datei: "foto.jpg", aktiv: true }];
  const two = [...one, { datei: "fotos/b.jpg", aktiv: false }];
  const shown = await inAll(() => [D.KINDS.map(kind => D.KIND_LABELS[kind]), D.variantNote(1), D.variantNote(3),
    D.photoSummary([]), D.photoSummary(one), D.photoSummary(two), D.photoSummary(one, false), D.photoSummary(two, false)]);
  assert.deepEqual(shown.de, [["Zeugnis", "Diplom", "Zertifikat"], "1 Bewerbung hat eine eigene Variante, dort gilt sie.",
    "3 Bewerbungen haben eine eigene Variante, dort gilt sie.", "Noch kein Foto. Ein Foto ist freiwillig.",
    "1 Foto, es wird verwendet.", "2 Fotos, das umrandete wird verwendet.", "1 Foto. Neue Unterlagen entstehen ohne Foto.",
    "2 Fotos. Neue Unterlagen entstehen ohne Foto."]);
  assert.deepEqual(shown.fr, [["Certificat de travail ou bulletin", "Diplôme", "Certificat"],
    "1 candidature a sa propre variante, c'est elle qui s'y applique.",
    "3 candidatures ont leur propre variante, c'est elle qui s'y applique.", "Pas encore de photo. Une photo est facultative.",
    "1 photo, elle est utilisée.", "2 photos, celle qui est encadrée est utilisée.",
    "1 photo. Les nouveaux documents sont créés sans photo.", "2 photos. Les nouveaux documents sont créés sans photo."]);
  assert.deepEqual(shown.en, [["Reference or report", "Diploma", "Certificate"], "1 application has its own variant, which applies there.",
    "3 applications have their own variant, which applies there.", "No photo yet. A photo is optional.",
    "1 photo, it is used.", "2 photos, the one with the frame is used.", "1 photo. New documents are created without a photo.",
    "2 photos. New documents are created without a photo."]);
});

test("the designs of the CV, their refusal and the line after a choice come in the app language", async () => {
  const shown = await inAll(() => {
    let refusal = "";
    try { D.designToSave("zweispaltig", "dossier-siegel"); } catch (error) { refusal = error.message; }
    return [D.DESIGNS.map(design => [design.id, design.name, design.text]), refusal, D.designSaved("einspaltig"),
      D.designName("unbekannt"), [D.sizeText(12000), D.sizeText(2500000)]];
  });
  assert.deepEqual(shown.de, [[["zweispaltig", "Zweispaltig", "Foto und Kontakt im Kopf, zwei Spalten. Viel auf wenig Platz."],
    ["einspaltig", "Einspaltig", "Schlicht, alles untereinander. Liest sich auch in Bewerbungsportalen gut."]],
    "Bitte Zweispaltig oder Einspaltig wählen.",
    "Neue Unterlagen entstehen jetzt im Design Einspaltig. Was schon erstellt oder versendet ist, bleibt, wie es ist.",
    "Zweispaltig", ["12 KB", "2.5 MB"]]);
  assert.deepEqual(shown.fr, [[["zweispaltig", "Deux colonnes", "Photo et coordonnées en en-tête, deux colonnes. Beaucoup de contenu sur peu de place."],
    ["einspaltig", "Une colonne", "Sobre, tout à la suite. Se lit bien aussi dans les portails de candidature."]],
    "Merci de choisir Deux colonnes ou Une colonne.",
    "Les nouveaux documents sont désormais créés avec le design Une colonne. Ce qui est déjà créé ou envoyé reste tel quel.",
    "Deux colonnes", ["12 Ko", "2.5 Mo"]]);
  assert.deepEqual(shown.en, [[["zweispaltig", "Two columns", "Photo and contact details in the header, two columns. A lot in little space."],
    ["einspaltig", "One column", "Plain, everything one below the other. Reads well in application portals too."]],
    "Please choose Two columns or One column.",
    "New documents are now created with the design One column. What is already created or sent stays as it is.",
    "Two columns", ["12 KB", "2.5 MB"]]);
});

// ---------- entwuerfe-logik.js ----------

const version = (id, tag, felder = {}) => ({ id, zeit: `${tag}T10:00:00`, beschreibung: "", versendet: [], ...felder });
const sent = [{ firma: "Beispiel AG", datum: "2026-10-24" }, { firma: "Muster AG", datum: "2026-10-30" }];

test("the filter, the folded versions and where a version went come in the app language", async () => {
  const groups = [{ art: "lebenslauf", titel: "Lebenslauf", dokumente: [{ datei: "cv.yaml", titel: "Lebenslauf", verwendet: true,
    fassungen: [version("c", "2026-11-03", { versendet: sent }), version("b", "2026-11-02"), version("a", "2026-11-01")] }] }];
  const shown = await inAll(() => [E.filter(groups).map(f => f.titel), E.ansicht(groups[0].dokumente[0]).faltTitel,
    E.ansicht(groups[0].dokumente[0], { nurVerwendet: true }).faltTitel, E.versandText(groups[0].dokumente[0].fassungen[0]),
    E.versandText(version("x", "2026-01-01", { versendet: [{ firma: null, datum: null, zweck: "Versand: Alt AG" }] }))]);
  assert.deepEqual(shown.de, [["Alle", "Lebenslauf"], "Ältere Fassungen (2)", "Nicht versendete Fassungen (2)",
    "versendet an Beispiel AG am 24.10.2026 und an Muster AG am 30.10.2026", "versendet (Versand: Alt AG)"]);
  // the title of a group comes from the server, which says it in the app language itself
  assert.deepEqual(shown.fr, [["Tous", "Lebenslauf"], "Versions plus anciennes (2)", "Versions non envoyées (2)",
    "envoyée à Beispiel AG le 24.10.2026 et à Muster AG le 30.10.2026", "envoyée (Versand: Alt AG)"]);
  assert.deepEqual(shown.en, [["All", "Lebenslauf"], "Older versions (2)", "Versions not sent (2)",
    "sent to Beispiel AG on 24.10.2026 and to Muster AG on 30.10.2026", "sent (Versand: Alt AG)"]);
});

// ---------- the scripts on a stand-in page ----------

class Node {
  constructor(tag = "div", attrs = {}) {
    Object.assign(this, { tag, attrs: { ...attrs }, children: [], listeners: {}, hidden: false, disabled: false, value: "",
                          checked: false, src: "", dataset: {}, style: {}, parentNode: null, open: false, files: [] });
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
  get firstChild() { return this.children[0] ?? null; }
  get lastElementChild() { return this.children.filter(child => child instanceof Node).at(-1) ?? null; }
  get textContent() { return this.children.map(child => (child instanceof Node ? child.textContent : String(child))).join(""); }
  set textContent(value) { this.children = [String(value)]; }
  all() { return this.children.filter(child => child instanceof Node).flatMap(child => [child, ...child.all()]); }
  querySelectorAll(selector) {
    const matches = selector.startsWith(".")
      ? node => (node.attrs.class || "").split(" ").includes(selector.slice(1)) : node => node.tag === selector;
    return this.all().filter(matches);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  closest() { return this.parentNode || new Node("label"); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  async fire(type, extra = {}) {
    const event = { type, target: this, currentTarget: this, preventDefault() {}, ...extra };
    for (const handler of this.listeners[type] || []) await handler(event);
  }
  focus() {}
  scrollIntoView() {}
  setPointerCapture() {}
  showModal() { this.open = true; }
  close() { this.open = false; }
}

const settle = async () => { for (let i = 0; i < 20; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const buttons = node => node.querySelectorAll("button").map(button => button.textContent);

/** Runs page scripts against a stand-in page; `routes` answers App.holen by path, `prepare` sets up elements. */
function run(names, { routes = {}, app = {}, extra = {}, search = "", prepare = () => {} } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, new Node("div", { id })); return elements.get(id); };
  prepare($);
  const asked = [];
  const status = (target, text = "") => { target.textContent = text; };
  const holen = async pfad => {
    if (!(pfad in routes)) throw new Error(`no route ${pfad}`);
    const found = routes[pfad];
    return typeof found === "function" ? found() : found;
  };
  const window = {
    App: { el: (tag, attrs, ...children) => { const node = new Node(tag, attrs || {}); node.append(...children); return node; },
           status, holen, senden: async () => ({}), url: (pfad, werte) => `${pfad}?${new URLSearchParams(werte)}`,
           bestaetigen: (button, question) => asked.push(question), datum: value => value, zeitpunkt: value => value,
           pdfAdresse: async () => "blob:pdf", letzteEntwuerfe: () => {}, textsatz: async () => "stelle-sie", alsBase64: async () => "", ...app },
    Texte: texte, DotLine, DateienLogik: D, EntwuerfeLogik: E,
    Meldungen: { zeige: (target, text, level = "") => { target.textContent = text; target.dataset.level = level; } },
    addEventListener() {}, ...extra,
  };
  const document = {
    getElementById: $, querySelectorAll: () => [], querySelector: () => ({ content: "token" }),
    documentElement: { dataset: {} },
  };
  const context = { window, document, URLSearchParams, location: { search }, history: { replaceState() {} }, console,
    setTimeout, performance: { now: () => 0 }, URL: { createObjectURL: () => "blob:1", revokeObjectURL() {} },
    Image: class { decode() { this.naturalHeight = 100; this.naturalWidth = 80; return Promise.resolve(); } },
    fetch: extra.fetch || (async () => ({ ok: true, json: async () => ({}), blob: async () => ({}) })),
    Texte: texte, App: window.App };
  vm.createContext(context);
  for (const name of names) vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  return { $, window, asked };
}

// ---------- dateien.js ----------

const LISTING = { max_groesse: 2000000, lebenslauf: [], diplom: [],
  zeugnis: [{ datei: "dokumente/zeugnisse/Arbeitszeugnis Muster.pdf", name: "Arbeitszeugnis Muster.pdf", groesse: 120000 }],
  zertifikat: [{ datei: "dokumente/zertifikate/Kurs Daten.pdf", name: "Kurs Daten.pdf", groesse: 2500000 }] };
const FILES_ROUTES = {
  "/api/bewerbungen": { bewerbungen: [{ variante: "daten", versand: null }] }, "/api/dateien": LISTING,
  "/api/dateien/aussehen": { design: "einspaltig" },
  "/api/foto/liste": { max_groesse: 10000000, zeigen: true, fotos: [{ datei: "foto.png", aktiv: true }, { datei: "fotos/b.png", aktiv: false }] },
};
const withLabel = $ => $("cv-waehlen").append(new Node("text"));

async function filesPage(app = {}) {
  const page = run(["dateien.js"], { routes: FILES_ROUTES, app, prepare: withLabel });
  await settle();
  return page;
}

test("Lebenslauf und Dateien names the CV, the files and the photos in the app language, names and values stay", async () => {
  const shown = await inAll(async () => {
    const page = await filesPage();
    const selects = page.$("nachweise").querySelectorAll("select");
    return [page.$("cv-varianten").textContent, page.$("cv-waehlen").firstChild.textContent, page.$("cv-datei").textContent,
      page.$("cv-design").textContent, selects.map(select => select.getAttribute("aria-label")),
      selects[0].children.map(option => [option.attrs.value, option.textContent]),
      page.$("nachweise").querySelectorAll(".leise").map(size => size.textContent),
      page.$("fotos").querySelectorAll("button").map(button => button.getAttribute("aria-label")), page.$("fotos-text").textContent,
      buttons(page.$("nachweise"))];
  });
  assert.deepEqual(shown.de, ["1 Bewerbung hat eine eigene Variante, dort gilt sie.", "PDF wählen",
    "Noch kein PDF. Bis eines da ist, erstellt die App den Lebenslauf.", "Design: Einspaltig",
    ["Art von Arbeitszeugnis Muster.pdf", "Art von Kurs Daten.pdf"],
    [["zeugnis", "Zeugnis"], ["diplom", "Diplom"], ["zertifikat", "Zertifikat"]], ["120 KB", "2.5 MB"],
    ["Aktives Foto", "Dieses Foto verwenden"], "2 Fotos, das umrandete wird verwendet.", ["Entfernen", "Entfernen"]]);
  assert.deepEqual(shown.fr, ["1 candidature a sa propre variante, c'est elle qui s'y applique.", "Choisir un PDF",
    "Pas encore de PDF. En attendant, l'app crée le CV.", fr("Design~: Une colonne"),
    ["Type de Arbeitszeugnis Muster.pdf", "Type de Kurs Daten.pdf"],
    [["zeugnis", "Certificat de travail ou bulletin"], ["diplom", "Diplôme"], ["zertifikat", "Certificat"]], ["120 Ko", "2.5 Mo"],
    ["Photo active", "Utiliser cette photo"], "2 photos, celle qui est encadrée est utilisée.", ["Retirer", "Retirer"]]);
  assert.deepEqual(shown.en, ["1 application has its own variant, which applies there.", "Choose PDF",
    "No PDF yet. Until there is one, the app creates the CV.", "Design: One column",
    ["Kind of Arbeitszeugnis Muster.pdf", "Kind of Kurs Daten.pdf"],
    [["zeugnis", "Reference or report"], ["diplom", "Diploma"], ["zertifikat", "Certificate"]], ["120 KB", "2.5 MB"],
    ["Active photo", "Use this photo"], "2 photos, the one with the frame is used.", ["Remove", "Remove"]]);
});

test("Lebenslauf und Dateien says what happened to files and photos in the app language, the server's reason as it comes", async () => {
  const shown = await inAll(async () => {
    const page = await filesPage({ senden: async pfad => {
      if (pfad === "/api/foto/aktiv") throw new Error("Vom Server.");
      return pfad === "/api/dateien/art" ? LISTING : {};
    } });
    const [select] = page.$("nachweise").querySelectorAll("select");
    select.value = "diplom";
    await select.fire("change");
    const kind = page.$("nachweise-status").textContent;
    page.$("nachweise-input").files = [{ name: "Gross.pdf", size: 3000000 }];
    await page.$("nachweise-input").fire("change");
    const tooLarge = page.$("nachweise-status").textContent;
    page.$("foto-input").files = [{ name: "gross.jpg", size: 20000000 }];
    await page.$("foto-input").fire("change");
    const photoTooLarge = page.$("fotos-status").textContent;
    page.$("foto-zeigen").checked = false;
    await page.$("foto-zeigen").fire("change");
    const hidden = page.$("fotos-status").textContent;
    await page.$("fotos").querySelectorAll("button")[1].fire("click");
    return [kind, tooLarge, photoTooLarge, hidden, page.$("fotos-status").textContent, page.asked[0]];
  });
  assert.deepEqual(shown.de, ["Arbeitszeugnis Muster.pdf ist jetzt als Diplom eingeordnet.",
    "Gross.pdf: Gross.pdf ist zu gross, höchstens 2 MB.", "Das Foto ist zu gross, höchstens 10 MB.",
    "Neue Unterlagen entstehen ohne Foto. Was schon erstellt ist, bleibt, wie es ist.", "Vom Server.", "Wirklich entfernen?"]);
  assert.deepEqual(shown.fr, [fr("Arbeitszeugnis Muster.pdf est maintenant classé comme «~Diplôme~»."),
    fr("Gross.pdf~: Gross.pdf est trop volumineux, 2 Mo au maximum."), "La photo est trop volumineuse, 10 Mo au maximum.",
    "Les nouveaux documents sont créés sans photo. Ce qui est déjà créé reste tel quel.", "Vom Server.", fr("Vraiment retirer~?")]);
  assert.deepEqual(shown.en, ["Arbeitszeugnis Muster.pdf is now filed as “Diploma”.",
    "Gross.pdf: Gross.pdf is too large, at most 2 MB.", "The photo is too large, at most 10 MB.",
    "New documents are created without a photo. What is already created stays as it is.", "Vom Server.", "Really remove?"]);
});

// ---------- entwuerfe.js ----------

const DRAFT_GROUPS = [{ art: "lebenslauf", titel: "Lebenslauf", dokumente: [{ datei: "cv.yaml", titel: "Lebenslauf", verwendet: true,
  fassungen: [version("c", "2026-11-03", { datei: "cv.yaml", pdf: true, beschreibung: "Angaben erfasst", versendet: sent.slice(0, 1) }),
    version("b", "2026-11-02", { datei: "cv.yaml", pdf: true, genutzt: true, genutzt_fuer: ["Versand Beispiel AG"] })] }] },
  { art: "suchprofil", titel: "Suchprofil", dokumente: [{ datei: "suchprofil.md", titel: "Suchprofil", verwendet: false,
    fassungen: [version("s", "2026-10-02", { datei: "suchprofil.md", pdf: true })] }] }];

test("Entwürfe und Versionen names its buttons, folds and empty parts in the app language, notes and titles stay", async () => {
  const shown = await inAll(async () => {
    const page = run(["entwuerfe.js"], { routes: { "/api/entwuerfe": { gruppen: DRAFT_GROUPS },
      "/api/versionen": { hinweis: "Vom Server.", versionen: [] } } });
    await settle();
    const doc = page.$("gruppen").querySelectorAll("article")[0];
    const [, older] = doc.querySelectorAll("li");
    return [buttons(page.$("filter")), doc.querySelector("summary").textContent, buttons(doc.querySelectorAll("ul")[0]),
      buttons(older), older.querySelectorAll("button").at(-1).getAttribute("title"), doc.querySelector(".drafts__sent").textContent,
      page.$("gruppen").querySelectorAll("h3").map(heading => heading.textContent),
      page.$("versionen").textContent, page.$("versionen-hinweis").textContent, page.$("leer").textContent,
      doc.querySelector("li").textContent.includes("Angaben erfasst")];
  });
  // the titles of groups and documents and the hint on versions come from the server, which says them itself
  assert.deepEqual(shown.de, [["Alle 2", "Lebenslauf 1", "Suchprofil 1"], "Ältere Fassungen (1)",
    ["Ansehen", "Als Text", "Vergleich mit vorher", "Löschen"], ["Ansehen", "Als Text", "Mit neuester vergleichen", "Zurückholen", "Löschen"],
    "Genutzt: Versand Beispiel AG", "versendet an Beispiel AG am 24.10.2026", ["Lebenslauf", "Suchprofil"],
    "Noch nichts versendet.", "Vom Server.", "Noch keine Entwürfe.", true]);
  assert.deepEqual(shown.fr, [["Tous 2", "Lebenslauf 1", "Suchprofil 1"], "Versions plus anciennes (1)",
    ["Voir", "En texte", "Comparer avec la précédente", "Supprimer"], ["Voir", "En texte", "Comparer avec la plus récente", "Récupérer", "Supprimer"],
    fr("Utilisé~: Versand Beispiel AG"), "envoyée à Beispiel AG le 24.10.2026", ["Lebenslauf", "Suchprofil"],
    "Rien n'a encore été envoyé.", "Vom Server.", "Pas encore de brouillons.", true]);
  assert.deepEqual(shown.en, [["All 2", "Lebenslauf 1", "Suchprofil 1"], "Older versions (1)",
    ["View", "As text", "Compare with previous", "Delete"], ["View", "As text", "Compare with newest", "Restore", "Delete"],
    "Used: Versand Beispiel AG", "sent to Beispiel AG on 24.10.2026", ["Lebenslauf", "Suchprofil"],
    "Nothing sent yet.", "Vom Server.", "No drafts yet.", true]);
});

test("a version without a note and a draft that cannot be shown are said in the app language", async () => {
  const shown = await inAll(async () => {
    const page = run(["entwuerfe.js"], { routes: { "/api/entwuerfe": { gruppen: DRAFT_GROUPS.slice(1) },
      "/api/versionen": () => { throw new Error("Kaputt."); }, "/api/entwurf": { text: null } },
      app: { pdfAdresse: async () => { throw new Error("kein Typst"); } } });
    await settle();
    const versionLine = page.$("gruppen").querySelector("li").querySelector("div").textContent;
    const view = page.$("gruppen").querySelector("li").querySelectorAll("button")[0];
    await view.attrs.onclick();
    await settle();
    return [versionLine.includes(texte.t("ohne Beschreibung")), texte.t("ohne Beschreibung"), page.$("status").textContent,
      page.$("ansicht").textContent];
  });
  assert.deepEqual(shown.de, [true, "ohne Beschreibung", "Als PDF nicht möglich (kein Typst), daher als Text.",
    "Inhalt ist binär und lässt sich nicht als Text anzeigen."]);
  assert.deepEqual(shown.fr, [true, "sans description", "Impossible en PDF (kein Typst), donc en texte.",
    "Le contenu est binaire et ne peut pas s'afficher comme texte."]);
  assert.deepEqual(shown.en, [true, "no description", "Not possible as PDF (kein Typst), so as text.",
    "The content is binary and cannot be shown as text."]);
});

// ---------- inhalte.js ----------

test("Inhalte als Text says what it checks and shows in the app language, the file and its title stay", async () => {
  const shown = await inAll(async () => {
    let check = {};
    const page = run(["inhalte.js"], {
      routes: { "/api/inhalte": { dateien: [{ datei: "cv.yaml", titel: "Lebenslauf", pdf: true }] }, "/api/inhalt": { text: "basics: {}\n" } },
      app: { pdfAdresse: async () => { throw new Error("Kaputt."); }, senden: async () => check },
      prepare: $ => { $("datei").value = "cv.yaml"; },
    });
    await settle();
    const pdf = page.$("status").textContent;
    const toggle = page.$("umschalten").textContent;
    await page.$("umschalten").fire("click");
    const back = page.$("umschalten").textContent;
    await page.$("pruefen").fire("click");
    const valid = page.$("status").textContent;
    check = { vorschau: false };
    page.$("text").value = "basics: {name: Muster}\n";
    await page.$("text").fire("input");
    const unsaved = page.$("status").textContent;
    await page.$("datei").fire("change");
    return [pdf, toggle, back, valid, unsaved, page.$("status").textContent, page.$("datei").children[0].textContent];
  });
  assert.deepEqual(shown.de, ["PDF nicht möglich: Kaputt. – mit „Als Text“ prüfen und korrigieren.", "Als Text", "Als PDF",
    "Gültig", "Nicht gespeichert", "Erst speichern oder „Änderungen verwerfen“, dann die Datei wechseln.", "Lebenslauf"]);
  assert.deepEqual(shown.fr, [fr("PDF impossible~: Kaputt. – vérifier et corriger avec «~En texte~»."), "En texte", "En PDF",
    "Valable", "Non enregistré", fr("Enregistrer d'abord ou «~Abandonner les modifications~», puis changer de fichier."), "Lebenslauf"]);
  assert.deepEqual(shown.en, ["PDF not possible: Kaputt. – check and correct with “As text”.", "As text", "As PDF",
    "Valid", "Not saved", "Save first or “Discard changes”, then switch the file.", "Lebenslauf"]);
});

// ---------- fragen.js ----------

const QUESTIONS = { eingerichtet: true, erlaubt: true, hinweis: "", uebrig: 1 };

test("the questions page speaks in the set and the app language, the AI's answer stays as it comes", async () => {
  const shown = await inAll(async () => {
    const page = run(["fragen.js"], { routes: { "/api/fragen/stand": QUESTIONS },
      app: { textsatz: async () => "stelle-du", senden: async () => ({ antwort: "Antwort der KI.", uebrig: 5 }) } });
    await settle();
    const examples = buttons(page.$("fragen-beispiele"));
    const start = [page.$("fragen-hilfe").textContent.slice(0, 20), page.$("fragen-label").textContent, page.$("fragen-uebrig").textContent];
    await page.$("fragen-beispiele").children[0].attrs.onclick();
    const turns = page.$("fragen-verlauf").children.map(turn => [turn.children[0].textContent, turn.children[1].textContent]);
    await page.$("fragen-senden").fire("click");
    return [examples, start, turns, page.$("fragen-uebrig").textContent, page.$("fragen-meldung").textContent];
  });
  assert.deepEqual(shown.de, [["Was fehlt noch in meinen Angaben?", "Wie bereite ich mich auf ein Vorstellungsgespräch vor?",
    "Wie gehe ich im Anschreiben mit einer Lücke um?"], ["Frag hier zur Stelle", "Deine Frage", "Heute noch 1 Frage."],
    [["Du", "Was fehlt noch in meinen Angaben?"], ["KI", "Antwort der KI."]], "Heute noch 5 Fragen.", "Bitte zuerst die Frage schreiben."]);
  assert.deepEqual(shown.fr, [[fr("Que manque-t-il encore dans mes informations~?"), fr("Comment me préparer à un entretien d'embauche~?"),
    fr("Comment aborder une interruption de parcours dans la lettre de motivation~?")],
    ["Pose ici tes questio", "Ta question", "Il reste 1 question aujourd'hui."],
    [["Toi", fr("Que manque-t-il encore dans mes informations~?")], ["IA", "Antwort der KI."]], "Il reste 5 questions aujourd'hui.",
    "Merci d'écrire d'abord la question."]);
  assert.deepEqual(shown.en, [["What is still missing in my details?", "How do I prepare for a job interview?",
    "How do I handle a gap in my CV in the cover letter?"], ["Ask here about the j", "Your question", "1 question left today."],
    [["You", "What is still missing in my details?"], ["AI", "Antwort der KI."]], "5 questions left today.",
    "Please write the question first."]);
});

test("without the AI the questions page says where to set it up, a refusal of the server as it comes", async () => {
  const shown = await inAll(async () => {
    const off = run(["fragen.js"], { routes: { "/api/fragen/stand": { ...QUESTIONS, eingerichtet: false } } });
    const minor = run(["fragen.js"], { routes: { "/api/fragen/stand": { ...QUESTIONS, erlaubt: false, hinweis: "Vom Server." } } });
    await settle();
    return [off.$("fragen-aus").textContent, minor.$("fragen-aus").textContent];
  });
  assert.equal(shown.de[0], "Für Fragen braucht es die KI der App: unter „Einstellungen“, „Zugang zur KI“ der Einladungscode oder ein eigener Schlüssel. Wer Claude mit dem eigenen Abo nutzt, fragt direkt dort.");
  assert.equal(shown.fr[0], fr("Pour poser des questions, il faut l'IA de l'app~: sous «~Paramètres~», «~Accès à l'IA~», le code d'invitation ou une clé personnelle. Qui utilise Claude avec son propre abonnement pose ses questions directement là-bas."));
  assert.equal(shown.en[0], "Questions need the app's AI: under “Settings”, “Access to the AI”, the invitation code or your own key. Anyone using Claude with their own subscription asks there directly.");
  assert.deepEqual([shown.de[1], shown.fr[1], shown.en[1]], ["Vom Server.", "Vom Server.", "Vom Server."]);
});

// ---------- foto.js ----------

function photoFetch(saved = { mirror: false, zoom: 1, x: 0.5, y: 0.5 }) {
  const answers = { "/api/foto/vorhanden": { vorhanden: true, max_groesse: 10000000 }, "/api/foto/optionen": saved,
                    "/api/foto/speichern": saved };
  return async adresse => {
    const [route] = adresse.split("?");
    return { ok: true, json: async () => answers[route] || {}, blob: async () => ({}) };
  };
}

async function photoPage() {
  const page = run(["foto.js"], { extra: { fetch: photoFetch() }, routes: {
    "/api/foto/liste": { max_groesse: 10000000, fotos: [{ datei: "foto.png", aktiv: true }, { datei: "fotos/b.png", aktiv: false }] } } });
  await settle();
  return page;
}

test("the photo page names its list and says what it saved in the app language, file names stay", async () => {
  const shown = await inAll(async () => {
    const page = await photoPage();
    const [active, other] = page.$("fotos").children;
    const list = [active.children[1].textContent, other.children[0].attrs.alt, buttons(other)];
    page.$("zoom").value = "2";
    await page.$("zoom").fire("input", { target: { value: "2" } });
    const unsaved = page.$("status").textContent;
    await buttons(other).length && other.querySelectorAll("button")[0].fire("click");
    const first = page.$("fotos-status").textContent;
    await page.$("speichern").fire("click");
    await settle();
    page.$("foto-datei").files = [];
    await page.$("foto-datei").fire("change", { target: { files: [{ name: "gross.jpg", size: 20000000 }], value: "" } });
    return [list, unsaved, first, page.$("status").textContent, page.$("hochladen-status").textContent, page.asked[0]];
  });
  assert.deepEqual(shown.de, [["Aktiv", "Foto b.png", ["Verwenden", "Löschen"]], "Nicht gespeichert",
    "Zuerst den Ausschnitt speichern oder zurücksetzen.", "Gespeichert. Der Stand davor liegt unter Entwürfe.",
    "gross.jpg ist zu gross, höchstens 10 MB.", "Wirklich löschen?"]);
  assert.deepEqual(shown.fr, [["Active", "Photo b.png", ["Utiliser", "Supprimer"]], "Non enregistré",
    "Enregistrer ou réinitialiser d'abord le cadrage.", "Enregistré. La version antérieure se trouve sous Brouillons.",
    "gross.jpg est trop volumineux, 10 Mo au maximum.", fr("Vraiment supprimer~?")]);
  assert.deepEqual(shown.en, [["Active", "Photo b.png", ["Use", "Delete"]], "Not saved",
    "Save or reset the crop first.", "Saved. The earlier version is under Drafts.",
    "gross.jpg is too large, at most 10 MB.", "Really delete?"]);
});

test("the photo page says in the app language that a deleted photo stays under the drafts, the file name stays", async () => {
  const shown = await inAll(async () => {
    const confirmed = [];
    const page = run(["foto.js"], { extra: { fetch: photoFetch() },
      app: { bestaetigen: (button, question, action) => confirmed.push(action),
             senden: async () => ({ fotos: [{ datei: "foto.png", aktiv: true }] }) },
      routes: { "/api/foto/liste": { max_groesse: 10000000,
                                     fotos: [{ datei: "foto.png", aktiv: true }, { datei: "fotos/b.png", aktiv: false }] } } });
    await settle();
    await confirmed[0]();
    return page.$("status").textContent;
  });
  assert.deepEqual([shown.de, shown.fr, shown.en], ["b.png gelöscht. Es bleibt unter Entwürfe.",
    "b.png supprimé. Le fichier reste sous Brouillons.", "b.png deleted. It stays under Drafts."]);
});
