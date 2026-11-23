// Suche einstellen, part A, in French and English (#424, G10, docs/design/sprachen.md): what the scripts of the page
// say at run time comes in the app language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to
// the pages: the ordered list of terms, the region card, the time window, the place notices, the portals, the
// suggestions of the AI and the messages. Terms, places, portals and the grammar of the search profile are data and stay
// as they are; German stays as it was. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const SuchlisteLogik = require("../seiten/suchliste-logik.js");
const SucheRahmenLogik = require("../seiten/suche-rahmen-logik.js");
const DotLine = require("../seiten/dot-line.js");

const CATALOG = path.join(__dirname, "..", "sprachen");
const SEITEN = path.join(__dirname, "..", "seiten");
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);
const DIGEST = "a".repeat(64);

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
const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };
const fr = text => text.replaceAll("~", NBSP);  // "~" stands for the no-break space French puts before « : ? ! ; » and inside « »

// A small stand-in for the DOM: elements by id, and what App.el builds.
function element(tag = "div", attrs = {}, kinder = []) {
  const handlers = {};
  return {
    tag, attrs, kinder, textContent: "", value: "", hidden: false, disabled: false, checked: false, open: false,
    maxLength: 0, className: "", dataset: {},
    addEventListener(type, handler) { handlers[type] = handler; },
    removeEventListener() {},
    fire(type, event = {}) { return handlers[type]({ preventDefault() {}, ...event }); },
    replaceChildren(...neu) { this.kinder = neu; },
    setAttribute(name, value) { this.attrs = { ...this.attrs, [name]: String(value) }; },
    removeAttribute() {},
    focus() {}, showModal() {}, close() {},
    querySelector: () => null, querySelectorAll: () => [], closest: () => null,
    getBoundingClientRect: () => ({ top: 0, height: 10 }),
  };
}
const el = (tag, attrs = {}, ...kinder) => element(tag, attrs || {},
  kinder.flat().filter(k => k !== null && k !== undefined && k !== false));
const text = node => (node && typeof node === "object" ? (node.kinder && node.kinder.length ? node.kinder.map(text).join("")
  : node.textContent || "") : String(node ?? ""));
const nodes = node => (node && typeof node === "object" && node.kinder ? [node, ...node.kinder.flatMap(nodes)] : []);

/** Runs the page scripts `names` with `window` and records every message App.status shows. */
function run(names, window, satz = "stelle-sie") {
  const elements = new Map();
  const $ = id => elements.get(id) || elements.set(id, element("div", { id })).get(id);
  const said = [];
  const document = { getElementById: $, addEventListener() {}, removeEventListener() {}, dispatchEvent() {},
                     activeElement: null, documentElement: { lang: "de", dataset: {} } };
  const app = { el, holen: async () => ({}), senden: async () => ({}), textsatz: async () => satz,
                status: (ziel, inhalt, stufe, optionen = {}) => said.push({ ziel: ziel && ziel.attrs ? ziel.attrs.id : null,
                  text: text({ kinder: [inhalt].flat() }), stufe, optionen }),
                fragenLink: (anker, inhalt) => el("a", { href: `#${anker}` }, inhalt), ...window.App };
  const full = { Texte: texte, DotLine, SuchlisteLogik, SucheRahmenLogik,
                 Meldungen: { isInputRejection: () => false }, SidebarLogic: { HITS_CHANGED: "treffer-geaendert" },
                 ...window, App: app };
  const context = { window: full, document, console, location: { hash: "" }, CustomEvent: class {},
                    setTimeout: () => 0, clearTimeout: () => {} };
  vm.createContext(context);
  for (const name of names) vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  return { $, said, window: full };
}

// The logic without DOM

test("the announcement and the names of the move buttons come in the app language", async () => {
  const shown = await inAll(() => [SuchlisteLogik.ansage("Datenanalyst", 2, 3), SuchlisteLogik.knopfNamen("Datenanalyst")]);
  assert.deepEqual(shown.de, ["„Datenanalyst“ steht jetzt an Stelle 2 von 3.",
    { hoch: "Datenanalyst nach oben", runter: "Datenanalyst nach unten", entfernen: "Datenanalyst entfernen" }]);
  assert.deepEqual(shown.fr, [fr("«~Datenanalyst~» est maintenant en position 2 sur 3."),
    { hoch: "Monter Datenanalyst", runter: "Descendre Datenanalyst", entfernen: "Retirer Datenanalyst" }]);
  assert.deepEqual(shown.en, ["“Datenanalyst” is now in position 2 of 3.",
    { hoch: "Move Datenanalyst up", runter: "Move Datenanalyst down", entfernen: "Remove Datenanalyst" }]);
});

test("the caption of a limited term names its portals in the app language, with one portal in the singular", async () => {
  const shown = await inAll(() => [
    SuchlisteLogik.zusatzTeile({ portale: ["jobs.ch", "job-room"], ausgeschaltet: ["jobs.ch"], aus: false }, ["Informatik"]),
    SuchlisteLogik.zusatzTeile({ portale: ["jobs.ch", "job-room", "ictjobs"], ausgeschaltet: ["jobs.ch", "ictjobs"], aus: false },
      ["Informatik", "ICT"]),
    SuchlisteLogik.zusatzTeile({ portale: ["jobs.ch"], ausgeschaltet: ["jobs.ch"], aus: true }, []),
  ]);
  assert.deepEqual(shown.de, [["nur jobs.ch, job-room", "jobs.ch ausgeschaltet", "Pflichtbezug: Informatik"],
    ["nur jobs.ch, job-room, ictjobs", "jobs.ch, ictjobs ausgeschaltet", "Pflichtbezug: Informatik, ICT"],
    ["nur jobs.ch", "ausgeschaltet"]]);
  assert.deepEqual(shown.fr, [["seulement jobs.ch, job-room", "jobs.ch désactivé", fr("Mot requis~: Informatik")],
    ["seulement jobs.ch, job-room, ictjobs", "jobs.ch, ictjobs désactivés", fr("Mots requis~: Informatik, ICT")],
    ["seulement jobs.ch", "désactivé"]]);
  assert.deepEqual(shown.en, [["only jobs.ch, job-room", "jobs.ch switched off", "Required word: Informatik"],
    ["only jobs.ch, job-room, ictjobs", "jobs.ch, ictjobs switched off", "Required words: Informatik, ICT"],
    ["only jobs.ch", "switched off"]]);
});

test("the hints of the region card come in the app language", async () => {
  const shown = await inAll(() => [SucheRahmenLogik.regionenJobscout24Hinweis(true), SucheRahmenLogik.regionenJobscout24Hinweis(false),
    SucheRahmenLogik.kantoneHinweis(true), SucheRahmenLogik.kantoneHinweis(false, 0), SucheRahmenLogik.kantoneHinweis(false, 2),
    SucheRahmenLogik.proPortalText([{ portal: "jobs.ch", orte: ["Thun", "Biel"] }, { portal: "jobscout24", vorsatz: "Regionen", orte: ["Bern"] }])]);
  assert.deepEqual(shown.de, [
    "jobscout24 sucht dann pro Begriff einmal in allen gewählten Regionen. Keine gewählt: jobscout24 sucht an den PLZ darunter.",
    "jobscout24 sucht dann pro Begriff einmal in allen gewählten Regionen. Keine gewählt: jobscout24 sucht an der PLZ aus Meine Angaben.",
    "Gesucht wird im Umkreis des Wohnorts. Die Kantone helfen beim Einordnen.",
    "Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst.",
    "Ohne Auswahl sucht die App in der ganzen Schweiz, Stellen nahe dem Wohnort zuerst. Nischen sucht die App ohne Ort; Stellen "
      + "ausserhalb dieser Kantone behält sie nur, wenn das Inserat Remote nennt.",
    ["jobs.ch: Thun, Biel", "jobscout24: Regionen Bern"]]);
  assert.deepEqual(shown.fr, [
    fr("jobscout24 cherche alors une fois par terme dans toutes les régions choisies. Aucune choisie~: jobscout24 cherche aux NPA ci-dessous."),
    fr("jobscout24 cherche alors une fois par terme dans toutes les régions choisies. Aucune choisie~: jobscout24 cherche au NPA de Mes informations."),
    "La recherche se fait dans un rayon autour du domicile. Les cantons aident à classer les offres.",
    "Sans choix, l'app cherche dans toute la Suisse, les offres proches du domicile en premier.",
    fr("Sans choix, l'app cherche dans toute la Suisse, les offres proches du domicile en premier. L'app cherche les niches sans "
      + "lieu~; elle ne garde les offres hors de ces cantons que si l'annonce mentionne le travail à distance."),
    [fr("jobs.ch~: Thun, Biel"), fr("jobscout24~: Regionen Bern")]]);
  assert.deepEqual(shown.en[0],
    "jobscout24 then searches once per term in all chosen regions. None chosen: jobscout24 searches at the postcodes below.");
  assert.equal(shown.en[3], "Without a choice the app searches all of Switzerland, jobs near the place of residence first.");
  assert.deepEqual(shown.en[5], ["jobs.ch: Thun, Biel", "jobscout24: Regionen Bern"]);
});

// The pages

test("the rows of the term list name their buttons in the app language, and a failed order says so", async () => {
  const shown = await inAll(async () => {
    const page = run(["suchliste.js"], { SucheErtragLogik: { OHNE_ERTRAG: "ohne Ertrag", teile: () => [] },
      App: { senden: async () => { throw new Error("x"); } } });
    const liste = element("ol");
    const status = element("div", { id: "suchliste-status" });
    page.window.Suchliste.zeige(liste, ["Datenanalyst", "Data Engineer"], { status, entfernen() {}, geaendert() {} });
    const knoepfe = nodes(liste).filter(n => n.tag === "button");
    const griff = nodes(liste).find(n => n.attrs.class === "suchliste__griff");
    knoepfe[1].fire("click");
    await settle();
    return { knoepfe: knoepfe.slice(0, 3).map(n => [n.attrs["aria-label"], n.attrs.title || text(n)]), griff: griff.attrs.title,
             said: page.said.map(m => m.text) };
  });
  assert.deepEqual(shown.de.knoepfe, [["Datenanalyst nach oben", "Nach oben"], ["Datenanalyst nach unten", "Nach unten"],
    ["Datenanalyst entfernen", "Entfernen"]]);
  assert.deepEqual(shown.fr.knoepfe, [["Monter Datenanalyst", "Monter"], ["Descendre Datenanalyst", "Descendre"],
    ["Retirer Datenanalyst", "Retirer"]]);
  assert.deepEqual(shown.en.knoepfe, [["Move Datenanalyst up", "Move up"], ["Move Datenanalyst down", "Move down"],
    ["Remove Datenanalyst", "Remove"]]);
  assert.deepEqual([shown.de.griff, shown.fr.griff, shown.en.griff], ["Ziehen, um zu verschieben", "Faire glisser pour déplacer", "Drag to move"]);
  assert.deepEqual(shown.de.said, ["„Datenanalyst“ steht jetzt an Stelle 2 von 2.", "Reihenfolge nicht gespeichert: x"]);
  assert.deepEqual(shown.fr.said, [fr("«~Datenanalyst~» est maintenant en position 2 sur 2."), fr("Ordre non enregistré~: x")]);
  assert.deepEqual(shown.en.said, ["“Datenanalyst” is now in position 2 of 2.", "Order not saved: x"]);
});

/** beruf-vorschlag.js with a consent already given and `antworten` per route; Suchliste only records what it got. */
function suggestions(antworten = {}, satz = "stelle-sie") {
  const liste = { zeige(ziel, begriffe, optionen) { Object.assign(this, { ziel, begriffe, optionen }); } };
  const page = run(["beruf-vorschlag.js"], {
    Suchliste: liste, Einwilligung: { zeile() {} },
    App: { holen: async () => ({ einwilligung: { erteilt: true } }),
           senden: async pfad => { if (antworten[pfad] instanceof Error) throw antworten[pfad]; return antworten[pfad] || {}; } },
  }, satz);
  return { ...page, liste };
}

const VORSCHLAG = { beruf: "Datenanalyst", warum: "Passt zu SQL.", alltag: "Berichte bauen", pruefen: "SQL verlangt", schon_gesucht: false,
                    schluessel: "datenanalyst" };

async function suggestionTexts(art, satz) {
  const page = suggestions({ "/api/beruf/vorschlag": { vorschlaege: [VORSCHLAG] },
    "/api/beruf/entfernen": { rueckgaengig: DIGEST }, "/api/beruf/rueckgaengig": { am_ende: true } }, satz);
  await page.window.Suchbegriffe.zeige(art, ["Datenanalyst"], ["datenanalyst"], 80);
  const felder = ["vorschlag-titel", "vorschlag-label-interessen", "vorschlag-label-staerken", "vorschlag-label-vermeiden",
    "vorschlag-holen", "suchliste-titel", "suchliste-neu-label"].map(id => page.$(id).textContent);
  await page.$("vorschlag-holen").fire("click");
  await settle();
  const karte = page.$("vorschlag-liste").kinder[0];
  await page.liste.optionen.entfernen("Datenanalyst", element("button"));
  const entfernt = page.said[page.said.length - 1];
  await entfernt.optionen.aktion.ausfuehren();
  page.$("suchliste-neu").value = "Berufsbildner (nur mit Informatik, ICT)";
  await page.$("suchliste-aufnehmen").fire("click");
  page.$("suchliste-neu").value = "Datenanalyst (nur mit SQL)";
  await page.$("suchliste-aufnehmen").fire("click");
  page.$("suchliste-neu").value = "Data Engineer";
  await page.$("suchliste-aufnehmen").fire("click");
  return { felder, hilfe: page.$("vorschlag-hilfe").textContent, ordnen: page.$("suchliste-hinweis").textContent,
           karte: nodes(karte).filter(n => n.tag === "p" && n.attrs.class === "leise").map(text),
           knopf: nodes(karte).filter(n => n.tag === "button").map(n => [n.attrs["aria-label"], text(n)])[0],
           said: page.said.map(m => m.text), aktion: entfernt.optionen.aktion.text };
}

test("the suggestions of the AI for a job, formally, come in the app language with a singular for one", async () => {
  const shown = await inAll(() => suggestionTexts("stelle", "stelle-sie"));
  assert.deepEqual(shown.de.felder, ["Stellen von der KI vorschlagen lassen", "Was machen Sie gern? (Interessen)",
    "Was können Sie gut? (Fähigkeiten)", "Was möchten Sie lieber nicht? (freiwillig)", "Stellen vorschlagen", "Danach suchen Sie:",
    "Eigenen Suchbegriff aufnehmen"]);
  assert.deepEqual(shown.fr.felder, ["Se faire proposer des postes par l'IA", fr("Qu'aimez-vous faire~? (intérêts)"),
    fr("Qu'est-ce que vous faites bien~? (compétences)"), fr("Qu'est-ce que vous préférez éviter~? (facultatif)"), "Proposer des postes",
    fr("Vous cherchez~:"), "Ajouter un mot-clé personnel"]);
  assert.deepEqual(shown.en.felder, ["Have the AI suggest jobs", "What do you like doing? (interests)", "What are you good at? (abilities)",
    "What would you rather not do? (optional)", "Suggest jobs", "You are searching for:", "Add your own search term"]);
  assert.ok(shown.fr.hilfe.startsWith("Vous ne savez pas encore exactement quoi chercher"));
  assert.ok(shown.fr.hilfe.includes("L'ORP ou l'orientation professionnelle"));
  assert.ok(shown.en.hilfe.includes("The RAV or career guidance"));
  assert.ok(shown.fr.ordnen.startsWith(fr("La recherche va de haut en bas~; les nouveaux termes vont à la fin. Faites glisser")));
  assert.deepEqual(shown.de.karte, ["Im Alltag: Berichte bauen", "Im Inserat: SQL verlangt"]);
  assert.deepEqual(shown.fr.karte, [fr("Au quotidien~: Berichte bauen"), fr("Dans l'annonce~: SQL verlangt")]);
  assert.deepEqual(shown.en.karte, ["Day to day: Berichte bauen", "In the ad: SQL verlangt"]);
  assert.deepEqual(shown.de.knopf, ["Datenanalyst in die Suche aufnehmen", "In die Suche aufnehmen"]);
  assert.deepEqual(shown.fr.knopf, ["Ajouter Datenanalyst à la recherche", "Ajouter à la recherche"]);
  assert.deepEqual(shown.en.knopf, ["Add Datenanalyst to the search", "Add to the search"]);
  assert.deepEqual(shown.de.said, ["Die KI überlegt, das dauert einen Moment …", "1 Vorschlag. Nehmen Sie auf, was Sie interessiert.",
    "„Datenanalyst“ ist nicht mehr in Ihrer Suche.", "„Datenanalyst“ ist wieder in Ihrer Suche, am Ende der Liste.",
    "„Berufsbildner“ ist jetzt in Ihrer Suche, mit Pflichtbezug: Informatik, ICT.",
    "„Datenanalyst“ ist jetzt in Ihrer Suche, mit Pflichtbezug: SQL.", "„Data Engineer“ ist jetzt in Ihrer Suche."]);
  assert.deepEqual(shown.fr.said, ["L'IA réfléchit, cela prend un moment…", "1 proposition. Ajoutez ce qui vous intéresse.",
    fr("«~Datenanalyst~» n'est plus dans votre recherche."), fr("«~Datenanalyst~» est de nouveau dans votre recherche, à la fin de la liste."),
    fr("«~Berufsbildner~» est maintenant dans votre recherche, avec les mots requis~: Informatik, ICT."),
    fr("«~Datenanalyst~» est maintenant dans votre recherche, avec le mot requis~: SQL."),
    fr("«~Data Engineer~» est maintenant dans votre recherche.")]);
  assert.deepEqual(shown.en.said, ["The AI is thinking, this takes a moment…", "1 suggestion. Add what interests you.",
    "“Datenanalyst” is no longer in your search.", "“Datenanalyst” is back in your search, at the end of the list.",
    "“Berufsbildner” is now in your search, with the required words: Informatik, ICT.",
    "“Datenanalyst” is now in your search, with the required word: SQL.", "“Data Engineer” is now in your search."]);
  assert.deepEqual([shown.de.aktion, shown.fr.aktion, shown.en.aktion], ["Rückgängig", "Annuler", "Undo"]);
});

test("the suggestions for an apprenticeship say du and tu, and several suggestions take the plural", async () => {
  const shown = await inAll(async () => {
    const page = suggestions({ "/api/beruf/vorschlag": { vorschlaege: [VORSCHLAG, { ...VORSCHLAG, beruf: "Koch/Köchin EFZ" }] } },
      "lehrstelle-du");
    await page.window.Suchbegriffe.zeige("lehrstelle", [], [], 80);
    await page.$("vorschlag-holen").fire("click");
    await settle();
    const karte = page.$("vorschlag-liste").kinder[0];
    return { titel: page.$("vorschlag-titel").textContent, neu: page.$("suchliste-neu-label").textContent,
             pruefen: nodes(karte).filter(n => n.tag === "p" && n.attrs.class === "leise").map(text)[1],
             fertig: page.said[page.said.length - 1].text };
  });
  assert.deepEqual(shown.de, { titel: "Berufe von der KI vorschlagen lassen",
    neu: "Eigenen Beruf aufnehmen (mit EFZ oder EBA, zum Beispiel Koch/Köchin EFZ)", pruefen: "In der Schnupperlehre: SQL verlangt",
    fertig: "2 Vorschläge. Nimm auf, was dich interessiert." });
  assert.deepEqual(shown.fr, { titel: "Se faire proposer des métiers par l'IA",
    neu: "Ajouter ton propre métier (avec EFZ ou EBA, par exemple Koch/Köchin EFZ)", pruefen: fr("Pendant le stage d'orientation~: SQL verlangt"),
    fertig: "2 propositions. Ajoute ce qui t'intéresse." });
  assert.deepEqual(shown.en, { titel: "Have the AI suggest occupations",
    neu: "Add your own occupation (with EFZ or EBA, for example Koch/Köchin EFZ)", pruefen: "In the trial apprenticeship: SQL verlangt",
    fertig: "2 suggestions. Add what interests you." });
});

test("a job search with du keeps du in German and takes tu in French", async () => {
  const shown = await inAll(async () => {
    const page = suggestions({}, "stelle-du");
    await page.window.Suchbegriffe.zeige("stelle", ["Datenanalyst"], ["datenanalyst"], 80);
    return [page.$("vorschlag-label-interessen").textContent, page.$("suchliste-titel").textContent];
  });
  assert.deepEqual(shown.de, ["Was machst du gern? (Interessen)", "Danach suchst du:"]);
  assert.deepEqual(shown.fr, [fr("Qu'aimes-tu faire~? (intérêts)"), fr("Tu cherches~:")]);
  assert.deepEqual(shown.en, ["What do you like doing? (interests)", "You are searching for:"]);
});

test("the time window says saved or not saved in the app language", async () => {
  const shown = await inAll(async () => {
    let fail = false;
    const page = run(["zeitfenster.js"], {
      SucheAnzeige: { zeitfensterWahl: () => [], portalStand: () => [] },
      App: { holen: async () => ({ art: "stelle", zeitfenster: 21, portale: [] }),
             senden: async () => { if (fail) throw new Error("x"); return { art: "stelle", zeitfenster: 21, portale: [] }; } },
    });
    await settle();
    await page.$("zeitfenster-tage").fire("change");
    fail = true;
    await page.$("zeitfenster-tage").fire("change");
    return page.said.map(m => m.text);
  });
  assert.deepEqual(shown.de, ["Gespeichert. Gilt ab der nächsten Suche.", "Nicht gespeichert. x"]);
  assert.deepEqual(shown.fr, ["Enregistré. S'applique dès la prochaine recherche.", "Non enregistré. x"]);
  assert.deepEqual(shown.en, ["Saved. Applies from the next search.", "Not saved. x"]);
});

test("the region card says its hints and messages in the app language, with places and regions as they are", async () => {
  const shown = await inAll(async () => {
    let fail = false;
    const page = run(["suche-rahmen.js"], { App: { senden: async () => { if (fail) throw new Error("x"); return {}; } } });
    page.window.SucheRahmen.zeige({ werte: { plz: ["3000"] }, orte_pro_portal: [{ portal: "jobscout24", vorsatz: "Regionen", orte: ["Bern"] }] },
      false, [], 1);
    page.$("region-aendern").fire("click");
    await page.$("region-form").fire("submit");
    fail = true;
    await page.$("titelfilter-form").fire("submit");
    return { kantone: page.$("kantone-hinweis").textContent, jobscout24: page.$("region-regionen_jobscout24-hinweis").textContent,
             orte: text(page.$("portale-orte-text")), said: page.said.map(m => m.text) };
  });
  assert.equal(shown.de.jobscout24,
    "jobscout24 sucht dann pro Begriff einmal in allen gewählten Regionen. Keine gewählt: jobscout24 sucht an den PLZ darunter.");
  assert.ok(shown.fr.kantone.endsWith("que si l'annonce mentionne le travail à distance."));
  assert.ok(shown.en.kantone.endsWith("only if the ad mentions remote work."));
  assert.ok(shown.fr.orte.startsWith(fr("jobscout24~: Regionen Bern")));
  assert.deepEqual(shown.de.said, ["Gespeichert. Gilt ab der nächsten Suche.", "Nicht gespeichert. x"]);
  assert.deepEqual(shown.fr.said, ["Enregistré. S'applique dès la prochaine recherche.", "Non enregistré. x"]);
  assert.deepEqual(shown.en.said, ["Saved. Applies from the next search.", "Not saved. x"]);
});

test("the place notices offer Rückgängig and say a failed load in the app language", async () => {
  const shown = await inAll(async () => {
    let fail = false;
    const notice = { ort: "Thun", text: "Thun und Bern …", knopf: "Thun entfernen", behalten: "Behalten" };
    const page = run(["orte-hinweise.js"], { SucheRahmen: { oeffneRegionen() {} }, App: {
      holen: async () => { if (fail) throw new Error("x"); return { orte: [notice], plz: null }; },
      senden: async () => ({ text: "Thun entfernt.", ort: "Thun", rueckgaengig: DIGEST }) } });
    await page.window.OrteHinweise.lade();
    const knopf = nodes(page.$("orte-doppelt-liste")).filter(n => n.tag === "button")[0];
    await knopf.fire("click");
    const aktion = page.said[0].optionen.aktion.text;
    fail = true;
    await page.window.OrteHinweise.lade();
    return [aktion, page.said[page.said.length - 1].text];
  });
  assert.deepEqual(shown.de, ["Rückgängig", "Hinweise zu den Orten liessen sich nicht laden: x"]);
  assert.deepEqual(shown.fr, ["Annuler", fr("Impossible de charger les remarques sur les lieux~: x")]);
  assert.deepEqual(shown.en, ["Undo", "The notes on the places could not be loaded: x"]);
});

test("the portals link why ictjobs is on or off and give the reason in the app language", async () => {
  const shown = await inAll(async () => {
    const page = run(["portal-wahl.js"], {});
    page.window.PortalWahl.zeige([{ name: "ictjobs", hinweis: "nur Informatik", an: true, grund: "keine" }], () => {});
    await settle();
    const zeile = page.$("portale-liste").kinder[0];
    return { link: text(nodes(zeile).find(n => n.tag === "a")),
             grund: nodes(zeile).filter(n => n.tag === "p").map(n => n.textContent || text(n))[0] };
  });
  assert.deepEqual(shown.de, { link: "Warum ictjobs an oder aus ist", grund: "An, bis Suchbegriffe da sind. Mit dem Häkchen ausschalten." });
  assert.deepEqual(shown.fr, { link: "Pourquoi ictjobs est activé ou non",
    grund: "Activé tant qu'il n'y a pas de mots-clés. Décocher pour le désactiver." });
  assert.deepEqual(shown.en, { link: "Why ictjobs is on or off", grund: "On until there are search terms. Untick to switch off." });
});

/** suche-einstellen.js with the data of an invented job search; `ertrag` an Error makes the yield fail. */
async function settingsPage(ertrag) {
  const routes = {
    "/api/suche/liste": { art: "stelle", einstellungen: { auto_bewerten: true, zuschauen: false }, grenze: 1, portale: [] },
    "/api/suche/rahmen": { pensum: "", ausschluss: [], titel_ausschluss: [], titel_positiv: [] },
    "/api/firmen/ausgeschlossen": { firmen: [] },
    "/api/suchbegriffe/schaetzung": { verfuegbar: false },
    "/api/suche/ertrag": ertrag,
  };
  const page = run(["suche-einstellen.js"], {
    Texte: { ...texte, anwenden: () => {} },
    SucheAnzeige: { regionText: () => "", nischenText: () => "", zusammenfassung: () => [] },
    TrefferLogik: { wahlAus: () => "lehrstelle" }, SuchbegriffeLogik: {},
    SucheRahmen: { zeige() {} }, TitelfilterBeispiele: { begriffe() {}, beispiele() {} }, Suchbegriffe: { zeige() {} },
    Suchliste: { portale() {}, pflicht() {} }, PortalWahl: { zeige() {} }, SucheErtrag: { zeige() {} },
    DoppeltGesucht: { lade() {} }, OrteHinweise: { lade() {} },
    App: { holen: async route => { if (routes[route] instanceof Error) throw routes[route]; return routes[route]; } },
  });
  await settle();
  return { region: page.$("region-text").textContent, pensum: page.$("pensum-text").textContent,
           auto: page.$("auto-text").textContent, said: page.said.map(m => m.text) };
}

test("Suche einstellen says nothing given, the automatic rating and a failed yield in the app language", async () => {
  const shown = await inAll(() => settingsPage(new Error("x")));
  assert.deepEqual(shown.de, { region: "Nichts angegeben", pensum: "Nichts angegeben",
    auto: "Neue Treffer nach der Suche automatisch bewerten (höchstens 1 pro Suche)",
    said: ["Was die Suche bringt, liess sich nicht laden: x"] });
  assert.deepEqual(shown.fr, { region: "Rien d'indiqué", pensum: "Rien d'indiqué",
    auto: "Évaluer automatiquement les nouveaux résultats après la recherche (1 au plus par recherche)",
    said: [fr("Impossible de charger ce que rapporte la recherche~: x")] });
  assert.deepEqual(shown.en, { region: "Nothing given", pensum: "Nothing given",
    auto: "Rate new results automatically after the search (at most 1 per search)",
    said: ["What the search brings could not be loaded: x"] });
});

// The wording fixed by the UI/UX rulings on #416 to #423 that this page reuses
const REVIEWED = {
  "Jetzt suchen": ["Rechercher maintenant", "Search now"],
  "Zeitfenster": ["Période", "Time window"],
  "Rückgängig": ["Annuler", "Undo"],
  "Aufnehmen": ["Ajouter", "Add"],
  "Titelfilter": ["Filtre de titre", "Title filter"],
  "Was der Titelfilter aussortiert hat": ["Ce qu'a retiré le filtre de titre", "What the title filter filtered out"],
  "Stellen": ["Offres", "Jobs"],
};

test("the reviewed names are the ones the catalog gives", async () => {
  const shown = await inAll(() => Object.keys(REVIEWED).map(german => texte.t(german)));
  assert.deepEqual(shown.de, Object.keys(REVIEWED));
  assert.deepEqual(shown.fr, Object.values(REVIEWED).map(([fr]) => fr));
  assert.deepEqual(shown.en, Object.values(REVIEWED).map(([, en]) => en));
});
