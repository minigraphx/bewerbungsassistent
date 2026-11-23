// The page Stellen in French and English (#422, G10, docs/design/sprachen.md): what treffer.js, suchlauf-logik.js,
// merken-ab-note-logik.js, haken-ausschluss-logik.js, suchbegriffe-start.js and treffer-firma.js say at run time comes in
// the app language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages. Job titles,
// companies, portals and search terms are data and stay as they are; German stays as it was. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const logik = require("../seiten/treffer-logik.js");
const anzeige = require("../seiten/suche-anzeige.js");
const DotLine = require("../seiten/dot-line.js");
const sidebarLogic = require("../seiten/sidebar-logic.js");
const L = require("../seiten/suchlauf-logik.js");
const M = require("../seiten/merken-ab-note-logik.js");
const H = require("../seiten/haken-ausschluss-logik.js");

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

/** Runs `check` with the app in `language`, then gives the page back its own language. */
async function inLanguage(language, check) {
  texte.setzeSprache(language, catalogFor(language));
  try {
    return await check();
  } finally {
    texte.setzeSprache();
  }
}

const inAll = async check => ({ de: await check(), fr: await inLanguage("fr", check), en: await inLanguage("en", check) });
const syncAll = check => {
  const result = { de: check() };
  for (const language of ["fr", "en"]) {
    texte.setzeSprache(language, catalogFor(language));
    try { result[language] = check(); } finally { texte.setzeSprache(); }
  }
  return result;
};

// ---------- suchlauf-logik.js: the progress line of a run ----------

test("the progress of a search run comes in the app language, with the search term as it is", () => {
  const step = { phase: "suche", portal: "jobs.ch", stichwort: "Datenanalyst", ort: "Bern", seite: 2, nummer: 3, abfragen: 40,
                 etappe: 1, etappen: 2 };
  assert.deepEqual(syncAll(() => L.laufZeile(step)), {
    de: ["jobs.ch: suche „Datenanalyst“ in Bern, Seite 2", "Suche 3 von 40, Etappe 1 von 2 …"],
    fr: [`jobs.ch${NBSP}: recherche «${NBSP}Datenanalyst${NBSP}» à Bern, page 2`, "Recherche 3 sur 40, étape 1 sur 2…"],
    en: ["jobs.ch: searching “Datenanalyst” in Bern, page 2", "Search 3 of 40, stage 1 of 2…"],
  });
  assert.deepEqual(syncAll(() => L.laufZeile({ phase: "suche", portal: "job-room", stichwort: "Datenanalyst", seite: 1 })), {
    de: ["job-room: suche „Datenanalyst“, Seite 1 …"],
    fr: [`job-room${NBSP}: recherche «${NBSP}Datenanalyst${NBSP}», page 1…`],
    en: ["job-room: searching “Datenanalyst”, page 1…"],
  });
});

test("a pause, the ads being read and the start of a run come in the app language", () => {
  assert.deepEqual(syncAll(() => L.laufZeile({ phase: "pause", portal: "jobs.ch", etappe: 2, etappen: 3, sekunden: 40 })), {
    de: [`jobs.ch: Pause vor Etappe 2 von 3, noch 40${NBSP}Sekunden …`],
    fr: [`jobs.ch${NBSP}: pause avant l'étape 2 sur 3, encore 40${NBSP}secondes…`],
    en: [`jobs.ch: pause before stage 2 of 3, 40${NBSP}seconds left…`],
  });
  assert.deepEqual(syncAll(() => L.laufZeile({ phase: "texte", portal: "jobs.ch", fertig: 4, von: 9 })), {
    de: ["jobs.ch: lese Inserat 5 von 9 …"],
    fr: [`jobs.ch${NBSP}: lecture de l'annonce 5 sur 9…`],
    en: ["jobs.ch: reading ad 5 of 9…"],
  });
  assert.deepEqual(syncAll(() => L.laufZeile({})), {
    de: ["Suche startet …"], fr: ["La recherche démarre…"], en: ["Search starting…"],
  });
});

// ---------- merken-ab-note-logik.js: saving every hit from a grade ----------

test("the button and the question before saving from a grade come in the app language", () => {
  assert.deepEqual(syncAll(() => M.knopfText(4.5)), {
    de: "Alle ab Note 4.5 merken", fr: "Tout mettre de côté dès la note 4.5", en: "Save all from grade 4.5",
  });
  const one = { note: 5, anzahl: 1, treffer: [{ id: "a", stelle: "Datenanalyst", firma: "Muster AG", note: 5.5 }] };
  const question = syncAll(() => M.bestaetigung(one));
  assert.deepEqual(question.de, {
    titel: "1 Treffer ab Note 5 merken?", einleitung: "Dieser Treffer kommt unter Bewerbungen:",
    zeilen: [["Datenanalyst, Muster AG", "Note 5.5"]],
    nachsatz: "Treffer ohne Note und solche, die schon gemerkt oder verworfen sind, bleiben, wie sie sind.",
    ok: "1 Treffer merken",
  });
  assert.deepEqual(question.fr, {
    titel: `Mettre de côté 1 résultat dès la note 5${NBSP}?`, einleitung: `Ce résultat va dans Candidatures${NBSP}:`,
    zeilen: [["Datenanalyst, Muster AG", "Note 5.5"]],
    nachsatz: "Les résultats sans note et ceux déjà mis de côté ou écartés restent tels quels.",
    ok: "Mettre de côté 1 résultat",
  });
  assert.deepEqual(question.en, {
    titel: "Save 1 result from grade 5?", einleitung: "This result goes to Applications:",
    zeilen: [["Datenanalyst, Muster AG", "Grade 5.5"]],
    nachsatz: "Unrated results and those already saved or discarded stay as they are.",
    ok: "Save 1 result",
  });
  const many = syncAll(() => M.bestaetigung({ ...one, anzahl: 3 }));
  assert.equal(many.fr.titel, `Mettre de côté 3 résultats dès la note 5${NBSP}?`);
  assert.equal(many.en.ok, "Save 3 results");
  assert.equal(many.de.einleitung, "Diese Treffer kommen unter Bewerbungen:");
  assert.equal(many.fr.einleitung, `Ces résultats vont dans Candidatures${NBSP}:`);
});

test("the result of saving from a grade has singular and plural in every language", () => {
  assert.deepEqual(syncAll(() => M.ergebnisText({ gemerkt: ["a"], uebersprungen: [] })), {
    de: "1 Treffer gemerkt. Er steht jetzt unter Bewerbungen.",
    fr: "1 résultat mis de côté. Il se trouve maintenant dans Candidatures.",
    en: "1 result saved. It is now under Applications.",
  });
  assert.deepEqual(syncAll(() => M.ergebnisText({ gemerkt: ["a", "b"], uebersprungen: ["c"] })), {
    de: "2 Treffer gemerkt. Sie stehen jetzt unter Bewerbungen. 1 Treffer hat sich inzwischen geändert und bleibt, wie er ist.",
    fr: "2 résultats mis de côté. Ils se trouvent maintenant dans Candidatures. 1 résultat a changé entre-temps et reste tel quel.",
    en: "2 results saved. They are now under Applications. 1 result has changed in the meantime and stays as it is.",
  });
  assert.equal(syncAll(() => M.ergebnisText({ gemerkt: [], uebersprungen: ["c", "d"] })).en,
    "0 results saved. They are now under Applications. 2 results have changed in the meantime and stay as they are.");
});

test("nothing to save and a failed step come in the app language", () => {
  assert.deepEqual(syncAll(() => M.keinerText(4)), {
    de: "Keine neuen Treffer mit Note 4 oder besser.",
    fr: "Aucun nouveau résultat avec la note 4 ou mieux.",
    en: "No new results with grade 4 or better.",
  });
  assert.deepEqual(syncAll(() => M.fehlerText("merken", 4.5, "Gesperrt.")), {
    de: "Die Treffer ab Note 4.5 liessen sich nicht merken: Gesperrt.",
    fr: `Impossible de mettre de côté les résultats dès la note 4.5${NBSP}: Gesperrt.`,
    en: "The results from grade 4.5 could not be saved: Gesperrt.",
  });
  assert.equal(syncAll(() => M.fehlerText("fragen", 4, "x")).fr, `Impossible de charger les résultats dès la note 4${NBSP}: x`);
});

// ---------- haken-ausschluss-logik.js: a point of the rating as an exclusion ----------

test("the words of an exclusion from the rating come in the app language", () => {
  const words = () => ({ knopf: H.KNOPF, label: H.knopfLabel("Kein Homeoffice"), wo: H.WO, orte: H.ARTEN.map(a => a.text),
                         ok: H.uebernommen(H.TITEL, "Verkauf"), weg: H.zurueck(H.INSERAT, "Schichtarbeit") });
  assert.deepEqual(syncAll(words), {
    de: { knopf: "Künftig nicht zeigen", label: "Künftig nicht zeigen: Kein Homeoffice", wo: "Wo eintragen?",
          orte: ["Im Titel", "Im Inserat"],
          ok: "«Verkauf» steht jetzt auf «Suche einstellen» unter «Im Titel». Gilt ab der nächsten Suche.",
          weg: "«Schichtarbeit» steht nicht mehr auf «Suche einstellen» unter «Im Inserat»." },
    fr: { knopf: "Ne plus afficher", label: `Ne plus afficher${NBSP}: Kein Homeoffice`, wo: `Où l'inscrire${NBSP}?`,
          orte: ["Dans le titre", "Dans l'annonce"],
          ok: `«${NBSP}Verkauf${NBSP}» figure maintenant sur «${NBSP}Régler la recherche${NBSP}» sous «${NBSP}Dans le titre${NBSP}». `
            + "S'applique dès la prochaine recherche.",
          weg: `«${NBSP}Schichtarbeit${NBSP}» ne figure plus sur «${NBSP}Régler la recherche${NBSP}» sous «${NBSP}Dans l'annonce${NBSP}».` },
    en: { knopf: "Don't show in future", label: "Don't show in future: Kein Homeoffice", wo: "Where to add it?",
          orte: ["In the title", "In the ad"],
          ok: "“Verkauf” is now on “Set up search” under “In the title”. Applies from the next search.",
          weg: "“Schichtarbeit” is no longer on “Set up search” under “In the ad”." },
  });
});

test("the form of an exclusion addresses the person as the text set does", () => {
  const sie = syncAll(() => H.frage("Was Sie nicht sehen wollen", false));
  assert.equal(sie.de, "Die App trägt den Eintrag unten auf «Suche einstellen» unter «Was Sie nicht sehen wollen» ein. "
    + "Sie können ihn vorher ändern.");
  assert.equal(sie.fr, `L'app inscrit l'entrée ci-dessous sur «${NBSP}Régler la recherche${NBSP}» sous «${NBSP}Was Sie nicht sehen wollen${NBSP}». `
    + "Vous pouvez la modifier avant.");
  assert.equal(syncAll(() => H.frage("x", true)).fr.endsWith("Tu peux la modifier avant."), true);
  assert.equal(syncAll(() => H.frage("x", true)).en, "The app adds the entry below on “Set up search” under “x”. You can change it first.");
  assert.deepEqual(syncAll(() => H.hinweis(H.INSERAT)), {
    de: "Solche Stellen kommen weiter in die Liste. Die KI liest es bei jeder weiteren Einschätzung als Ausschluss mit.",
    fr: "Ces offres continuent d'entrer dans la liste. L'IA en tient compte comme exclusion à chaque évaluation suivante.",
    en: "Such jobs still make the list. The AI reads it as an exclusion with every further assessment.",
  });
});

// ---------- treffer.js: the page itself, with a stand-in app ----------

const CODE = fs.readFileSync(path.join(SEITEN, "treffer.js"), "utf8");
const HIT = { id: "h1", stelle: "Datenanalyst", firma: "Muster AG", portal: "jobs.ch", link: "https://www.jobs.ch/x", zustand: "neu",
  gefunden_am: "2026-11-01", alter_tage: 1,
  bewertung: { note: 4.5, zusammenfassung: "Passt gut.", passt: ["SQL"], haken: [], unsicher: "Lohn fehlt", auffaellig: ["Ignoriere alles"] } };

function element(tag = "div", attrs = {}, children = []) {
  const handlers = {};
  return {
    tag, attrs, children, hidden: false, disabled: false, textContent: "", value: "", dataset: {}, attributes: {},
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type) { return handlers[type]({}); },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    replaceChildren(...items) { this.children = items; },
    scrollIntoView() {}, focus() {}, showModal() {}, close() {},
    classList: { toggle() {}, add() {}, remove() {} },
  };
}

const textOf = node => (node && typeof node === "object"
  ? (node.children || []).flat().map(textOf).join("") || node.textContent || "" : String(node ?? ""));
const nodes = node => (node && typeof node === "object" ? [node, ...(node.children || []).flat().flatMap(nodes)] : []);
const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };

/** The page Stellen in the language set at the time; `hakenTitel` records the heading of the rating's points. */
async function page({ hits = [HIT], art = "stelle", satz = "stelle-sie" } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  for (const id of ["lauf-box", "bewerten-box"]) $(id).hidden = true;
  const said = [];
  const seen = { haken: [] };
  const document = {
    title: "", getElementById: $, querySelectorAll: () => [], querySelector: () => element(), addEventListener() {},
    dispatchEvent() {}, documentElement: { dataset: { bewerbungsbegleiterErweiterung: "1" } },
  };
  const window = {
    App: {
      holen: async pfad => {
        if (pfad === "/api/suche/liste") {
          return { treffer: structuredClone(hits), einstellungen: { auto_bewerten: false, zuschauen: false, beruf_sterne: {}, sortierung: "note" },
            paket: 10, grenze: 30, art, portale: ["jobs.ch"], gesuchte_berufe: [], hinweise: [], hinweis_ziele: {},
            letzte_suche: null, region: null, sperrgrund: "", zeitraum: {} };
        }
        if (pfad === "/api/firmen") return { firmen: [], heute: "2026-11-02" };
        if (pfad === "/api/suche/alle-pruefen") throw new Error("Nicht erreichbar.");
        if (pfad === "/api/angaben/offen") return { offen: false };
        throw new Error(`unexpected ${pfad}`);
      },
      senden: async () => ({}),
      el: (tag, attrs, ...children) => element(tag, attrs || {}, children),
      status() {}, datum: String, beobachten() {}, textsatz: async () => satz,
    },
    TrefferLogik: logik, SuchlaufLogik: L, SucheAnzeige: anzeige, DotLine, Texte: texte, SidebarLogic: sidebarLogic,
    Meldungen: { zeige: (element, inhalt) => { said.push(textOf({ children: [inhalt].flat() })); }, leere() {} },
    FirmenLogik: { nachTreffer: () => new Map() }, TrefferFirma: { zeile: () => null, marke: () => null },
    WiederLogik: require("../seiten/wieder-logik.js"),
    TrefferWieder: { zeile: () => null, vermittler: () => null, marke: () => "", gleicheInserate: () => null },
    HakenAusschluss: { liste: (treffer, titel) => { seen.haken.push(titel); return null; } },
    SuchbegriffeStart: { zeige() {}, ids: () => null }, Sidebar: { currency: Promise.resolve("CHF") },
    addEventListener() {}, postMessage() {}, matchMedia: () => ({ matches: false }),
  };
  vm.runInNewContext(CODE, {
    window, document, URLSearchParams, console, CustomEvent: class { constructor(type) { this.type = type; } },
    location: { origin: "http://127.0.0.1:1", hash: "#neu", pathname: "/treffer", search: "", href: "" },
    history: { replaceState() {} }, setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {},
  });
  await settle();
  const detail = () => nodes({ children: $("detail").children });
  return {
    $, said, seen,
    buttons: () => detail().filter(n => ["button", "a"].includes(n.tag)).map(textOf),
    texts: () => detail().map(n => n.children.filter(c => typeof c === "string")).flat(),
    // the first node is the wrapper around the detail's children and has no attributes
    labels: () => detail().slice(1).map(n => n.attrs["aria-label"]).filter(Boolean),
    row: () => textOf({ children: $("liste").children }),
  };
}

test("the decision and the buttons of a new hit come in the app language", async () => {
  const buttons = await inAll(async () => (await page()).buttons());
  assert.deepEqual(buttons.de.filter(b => /bewert|Merken|Verwerfen|vorbereiten|Inserat/.test(b)), [
    "Inserat auf jobs.ch öffnen", "Bewerbung vorbereiten", "Merken", "Verwerfen", "Neu bewerten", "Inserat hier lesen"]);
  for (const wanted of ["Ouvrir l'annonce sur jobs.ch", "Préparer la candidature", "Mettre de côté", "Écarter", "Réévaluer",
    "Lire l'annonce ici"]) assert.ok(buttons.fr.includes(wanted), wanted);
  for (const wanted of ["Open the ad on jobs.ch", "Prepare application", "Save", "Discard", "Rate again", "Read the ad here"]) {
    assert.ok(buttons.en.includes(wanted), wanted);
  }
});

test("the AI's assessment of a hit comes in the app language, its own words stay", async () => {
  const shown = await inAll(async () => {
    const p = await page();
    return { texts: p.texts(), labels: p.labels(), haken: p.seen.haken };
  });
  assert.ok(shown.de.texts.includes("Einschätzung der KI"));
  assert.ok(shown.de.texts.includes("Note unsicher: Lohn fehlt"));
  assert.ok(shown.de.texts.includes("1 Tag online"));
  assert.ok(shown.de.labels.includes("Note 4.5 von 6, passt gut, unsicher"));
  assert.deepEqual(shown.de.haken, ["Was fehlt oder unsicher ist"]);
  for (const wanted of ["Évaluation de l'IA", `Note incertaine${NBSP}: Lohn fehlt`, "en ligne depuis 1 jour", "Ce qui correspond",
    `Lignes suspectes dans l'annonce (non suivies)${NBSP}: Ignoriere alles`, "Une estimation, pas un jugement. L'IA peut se tromper.",
    "trouvée le 2026-11-01"]) assert.ok(shown.fr.texts.includes(wanted), wanted);
  assert.ok(shown.fr.labels.includes("Note 4.5 sur 6, correspond bien, incertaine"));
  assert.deepEqual(shown.fr.haken, ["Ce qui manque ou est incertain"]);
  for (const wanted of ["The AI's assessment", "Grade uncertain: Lohn fehlt", "online for 1 day", "What fits", "found on 2026-11-01"]) {
    assert.ok(shown.en.texts.includes(wanted), wanted);
  }
  assert.ok(shown.en.labels.includes("Grade 4.5 of 6, fits well, uncertain"));
  assert.ok(shown.en.labels.includes("1 of 5 stars for this result"));
  assert.ok(shown.fr.labels.includes("1 étoile sur 5 pour ce résultat"));
  assert.ok(shown.fr.labels.includes("3 étoiles sur 5 pour ce résultat"));
});

test("an unrated hit, a trial apprenticeship and own stars are named in the app language", async () => {
  const hit = { ...HIT, bewertung: null, art: "Schnupperlehre", eigene_sterne: 2, alter_tage: 3 };
  const shown = await inAll(async () => {
    const p = await page({ hits: [hit], art: "lehrstelle", satz: "lehrstelle-du" });
    return { row: p.row(), texts: p.texts(), buttons: p.buttons() };
  });
  assert.match(shown.de.row, /noch keine Note.*Schnupperlehre.*Eigene: ★★/);
  assert.match(shown.fr.row, new RegExp(`sans note.*Stage d'orientation.*Personnelle${NBSP}: ★★`));
  assert.match(shown.en.row, /unrated.*Trial apprenticeship.*Own: ★★/);
  assert.ok(shown.fr.texts.includes("Pas encore évalué."));
  assert.ok(shown.en.texts.includes("online for 3 days"));
  assert.ok(shown.fr.buttons.includes("Évaluer"));
});

test("a missing estimate is said in the app language", async () => {
  const kosten = await inAll(async () => (await page()).$("kosten-hinweis").textContent);
  assert.deepEqual(kosten, {
    de: "Die Schätzung fehlt: Nicht erreichbar.",
    fr: `L'estimation manque${NBSP}: Nicht erreichbar.`,
    en: "The estimate is missing: Nicht erreichbar.",
  });
});
