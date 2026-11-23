// The page Firmen in French and English (#423, G10, docs/design/sprachen.md): what firmen.js says at run time comes in
// the app language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages: the kununu
// cell, the buttons, the line under the title with its singular, the dialogs, the choice among several companies and
// the messages. Company names and places are data and stay as they are; German stays as it was. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const logik = require("../seiten/firmen-logik.js");
const DotLine = require("../seiten/dot-line.js");

const CATALOG = path.join(__dirname, "..", "sprachen");
const CODE = fs.readFileSync(path.join(__dirname, "..", "seiten", "firmen.js"), "utf8");
const SET_PREFIX = "texte:";
const NBSP = String.fromCharCode(0xa0);
const HEUTE = "2026-11-09";
const LINK = "https://www.kununu.com/ch/muster-industrie";
const LINK2 = "https://www.kununu.com/ch/probe-handel";

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

const el = (tag, attrs = {}, ...kinder) => ({ tag, attrs: attrs || {},
  kinder: kinder.flat().filter(k => k !== null && k !== undefined && k !== false) });
const text = node => (node && typeof node === "object" ? (node.kinder ? node.kinder.map(text).join("") : node.textContent || "")
  : String(node ?? ""));
const nodes = node => (node && typeof node === "object" && node.kinder ? [node, ...node.kinder.flatMap(nodes)] : []);
const label = node => text(node.kinder[0]);
const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };

function element(id) {
  const handlers = {};
  return { id, textContent: "", value: "", placeholder: "", hidden: false, dataset: {}, kinder: [], classList: { toggle() {} },
           addEventListener(type, handler) { handlers[type] = handler; }, fire(type, event) { return handlers[type](event); },
           setAttribute() {}, removeAttribute() {}, focus() {}, showModal() {}, close() {}, querySelector: () => null,
           replaceChildren(...kinder) { this.kinder = kinder; } };
}

const firma = (name, kununu, extra = {}) => ({ schluessel: name.toLowerCase().replace(/\W+/g, "-"), name, ort: "Bern",
  treffer: [{ id: `${name}-1`, zustand: "neu" }], bewerbungen: [], kununu, ausgeschlossen: false,
  suche: `https://www.kununu.com/ch/search?q=${encodeURIComponent(name)}`, ...extra });

const ALL = [
  firma("Muster Industrie AG", { zustand: "gefunden", wert: 3.8, bewertungen: 214, empfehlung: 80, geprueft_am: "2026-07-01",
                                 link: LINK, seite: "ch" }),
  firma("Beispiel Bau AG", null, { bewerbungen: [{ id: "b1", stelle: "", status: "Gemerkt" }] }),
  firma("Testlogistik GmbH", { zustand: "nicht_gefunden", geprueft_am: "2026-10-01" }, { ausgeschlossen: true }),
  firma("Probe Handel AG", { zustand: "mehrere", geprueft_am: "2026-10-02",
                             kandidaten: [{ name: "Probe Handel AG", ort: "Zürich", bewertungen: 12, link: LINK2 }] }),
  firma("Musterwerk AG", { zustand: "zugeordnet", link: LINK, seite: "ch" }),
  firma("Leerbau AG", { zustand: "keine", geprueft_am: "2026-11-01", link: LINK, seite: "ch" }),
  firma("Fehlerhaus AG", { zustand: "fehler", geprueft_am: "2026-10-03" }),
  firma("Kleinbetrieb AG", { zustand: "gefunden", wert: 4.6, bewertungen: 4, geprueft_am: "2026-11-05", link: LINK, seite: "ch" }),
];

/** The page Firmen in the language set at the time, with a stand-in for the DOM and the app. */
async function page({ firmen = ALL, satz = "stelle-sie" } = {}) {
  const elements = new Map();
  const $ = id => elements.get(id) || elements.set(id, element(id)).get(id);
  const said = [];
  const sent = [];
  const chosen = { value: null };
  const document = {
    title: "", documentElement: { dataset: {} }, getElementById: $, querySelectorAll: () => [],
    querySelector: selector => (selector.endsWith("input:checked") && chosen.value !== null ? { value: chosen.value } : null),
  };
  const window = {
    FirmenLogik: logik, DotLine, Texte: texte,
    KununuPruefen: { pruefe: async () => null },
    FirmenAusschluss: { ausschliessen: async () => ({}), wiederZeigen: async () => ({}) },
    Meldungen: { zeige: (_ziel, inhalt) => said.push(text({ kinder: [inhalt].flat() })), isInputRejection: () => false,
                 clearOnInput() {} },
    App: { el, holen: async () => ({ firmen: structuredClone(firmen), heute: HEUTE }), textsatz: async () => satz,
           senden: async (pfad, body) => { sent.push(pfad, body); return {}; } },
  };
  vm.runInNewContext(CODE, { window, document, URLSearchParams, CSS: { escape: value => value } });
  await settle();
  const rows = () => new Map($("liste").kinder.map(row => [row.attrs["data-schluessel"] || row.attrs.id, row]));
  return { $, said, sent, chosen, rows, document,
           rowText: schluessel => text(rows().get(schluessel)),
           buttons: schluessel => nodes(rows().get(schluessel).kinder.find(cell => cell.attrs.class === "companies__actions"))
             .filter(n => ["button", "a"].includes(n.tag)).map(label),
           cellLabels: schluessel => nodes(rows().get(schluessel)).map(n => n.attrs["data-label"]).filter(Boolean),
           line: () => text({ kinder: $("zeile").kinder }) };
}

test("the kununu cell says what is known in the app language, with the company's own values", async () => {
  const shown = await inAll(async () => {
    const p = await page();
    return Object.fromEntries(["muster-industrie-ag", "beispiel-bau-ag", "testlogistik-gmbh", "probe-handel-ag", "musterwerk-ag",
      "leerbau-ag", "fehlerhaus-ag", "kleinbetrieb-ag"].map(key => [key, p.rowText(key)]));
  });
  assert.match(shown.de["muster-industrie-ag"], /3\.8 von 5.*214 Bewertungen.*80 % empfehlen.*Stand 01\.07\.2026/);
  assert.match(shown.fr["muster-industrie-ag"], /3\.8 sur 5.*214 avis.*80 % recommandent.*État au 01\.07\.2026/);
  assert.match(shown.en["muster-industrie-ag"], /3\.8 out of 5.*214 reviews.*80 % recommend.*As of 01\.07\.2026/);
  const fr = {
    "beispiel-bau-ag": "Pas encore vérifié", "testlogistik-gmbh": "Introuvable sur kununu", "probe-handel-ag": "Plusieurs entreprises sur kununu",
    "musterwerk-ag": "Pas encore vérifié, page associée", "leerbau-ag": "Pas encore d'avis",
    "fehlerhaus-ag": "Non vérifié. kununu n'était pas joignable. Merci de vérifier à nouveau plus tard.",
    "kleinbetrieb-ag": "Seulement 4 avis, peu significatif.",
  };
  const en = {
    "beispiel-bau-ag": "Not checked yet", "testlogistik-gmbh": "Not found on kununu", "probe-handel-ag": "Several companies on kununu",
    "musterwerk-ag": "Not checked yet, page assigned", "leerbau-ag": "No reviews yet",
    "fehlerhaus-ag": "Not checked. kununu could not be reached. Please check again later.", "kleinbetrieb-ag": "Only 4 reviews, not very telling.",
  };
  for (const [key, wanted] of Object.entries(fr)) assert.ok(shown.fr[key].includes(wanted), `${key}: ${wanted}`);
  for (const [key, wanted] of Object.entries(en)) assert.ok(shown.en[key].includes(wanted), `${key}: ${wanted}`);
  assert.ok(shown.de["testlogistik-gmbh"].includes("Bei kununu nicht gefunden"));
  assert.ok(shown.fr["testlogistik-gmbh"].includes("Plus dans la recherche"));
  assert.ok(shown.en["testlogistik-gmbh"].includes("No longer in the search"));
  assert.ok(shown.de["testlogistik-gmbh"].includes("Nicht mehr in der Suche"));
  assert.ok(shown.fr["beispiel-bau-ag"].includes("Candidature"));
  assert.ok(shown.en["beispiel-bau-ag"].includes("Application"));
});

test("the buttons of a row and the labels of its cells come in the app language", async () => {
  const shown = await inAll(async () => {
    const p = await page();
    return { found: p.buttons("muster-industrie-ag"), open: p.buttons("beispiel-bau-ag"), missing: p.buttons("testlogistik-gmbh"),
             several: p.buttons("probe-handel-ag"), failed: p.buttons("fehlerhaus-ag"), cells: p.cellLabels("muster-industrie-ag"),
             hidden: p.rowText("muster-industrie-ag") };
  });
  assert.deepEqual(shown.de.found, ["Neu prüfen", "Bei kununu ansehen", "Von Hand eintragen", "Diese Firma nicht mehr zeigen"]);
  assert.deepEqual(shown.fr.found, ["Revérifier", "Voir sur kununu", "Saisir à la main", "Ne plus afficher cette entreprise"]);
  assert.deepEqual(shown.en.found, ["Re-check", "View on kununu", "Enter by hand", "Stop showing this company"]);
  assert.deepEqual(shown.fr.open, ["Vérifier", "Saisir à la main", "Ne plus afficher cette entreprise"]);
  assert.deepEqual(shown.en.missing, ["Search on kununu", "Assign by hand", "Enter by hand", "Show this company again"]);
  assert.deepEqual(shown.fr.missing, ["Chercher sur kununu", "Associer à la main", "Saisir à la main", "Afficher à nouveau cette entreprise"]);
  assert.deepEqual(shown.fr.several.slice(0, 1), ["Choisir la bonne"]);
  assert.deepEqual(shown.en.several.slice(0, 1), ["Choose the matching one"]);
  assert.deepEqual(shown.fr.failed.slice(0, 1), ["Vérifier à nouveau"]);
  assert.deepEqual(shown.de.cells, ["kununu", "Treffer und Bewerbungen", "Geprüft"]);
  assert.deepEqual(shown.fr.cells, ["kununu", "Résultats et candidatures", "Vérification"]);
  assert.deepEqual(shown.en.cells, ["kununu", "Results and applications", "Checked"]);
  assert.ok(shown.de.hidden.includes(": Muster Industrie AG, öffnet neuen Tab"));
  assert.ok(shown.fr.hidden.includes(": Muster Industrie AG, ouvre un nouvel onglet"));
  assert.ok(shown.en.hidden.includes(": Muster Industrie AG, opens a new tab"));
});

test("the line under the title has a singular for one company and one found", async () => {
  const one = [ALL[0]];
  const lines = await inAll(async () => ({ all: (await page()).line(), one: (await page({ firmen: one })).line(),
    apprenticeship: (await page({ firmen: one, satz: "lehrstelle-du" })).line() }));
  assert.equal(lines.de.all.includes("8 Firmen aus Treffern und Bewerbungen"), true);
  assert.equal(lines.de.one.includes("1 Firmen aus Treffern und Bewerbungen"), true);
  assert.equal(lines.de.one.includes("1 bei kununu gefunden"), true);
  assert.equal(lines.de.one.includes("zuletzt geprüft am 01.07.2026"), true);
  assert.equal(lines.de.apprenticeship.includes("1 Lehrbetriebe aus Treffern und Bewerbungen"), true);
  for (const wanted of ["8 entreprises issues des résultats et candidatures", "3 trouvées sur kununu",
    "dernière vérification le 05.11.2026"]) assert.ok(lines.fr.all.includes(wanted), wanted);
  for (const wanted of ["1 entreprise issue des résultats et candidatures", "1 trouvée sur kununu",
    "dernière vérification le 01.07.2026"]) assert.ok(lines.fr.one.includes(wanted), wanted);
  assert.ok(lines.fr.apprenticeship.includes("1 entreprise formatrice issue des résultats et candidatures"));
  for (const wanted of ["8 companies from results and applications", "3 found on kununu", "last checked on 05.11.2026"]) {
    assert.ok(lines.en.all.includes(wanted), wanted);
  }
  for (const wanted of ["1 company from results and applications", "1 found on kununu"]) assert.ok(lines.en.one.includes(wanted), wanted);
  assert.ok(lines.en.apprenticeship.includes("1 host company from results and applications"));
});

test("title and search field follow the text set in the app language", async () => {
  const shown = await inAll(async () => {
    const p = await page({ satz: "lehrstelle-du" });
    return [p.document.title, p.$("suche").placeholder];
  });
  assert.deepEqual(shown.de, ["Lehrbetriebe", "Lehrbetrieb suchen"]);
  assert.deepEqual(shown.fr, ["Entreprises formatrices", "Chercher une entreprise formatrice"]);
  assert.deepEqual(shown.en, ["Host companies", "Search for a host company"]);
});

test("the help on reading kununu speaks of the staff, as the UI/UX ruling on #423 says", async () => {
  const help = await inAll(async () => ["stelle-sie", "stelle-du", "lehrstelle-du"].map(satz => texte.text("firmen.hilfe", satz)));
  assert.ok(help.de[0].startsWith("Auf kununu bewerten heutige und frühere Mitarbeitende ihre Firma: 5 ist"));
  assert.ok(help.fr[0].startsWith(`Sur kununu, le personnel actuel et ancien évalue son entreprise${NBSP}: 5 est la meilleure valeur`));
  assert.ok(help.fr[0].endsWith("correspond à vos informations."));
  assert.ok(help.fr[1].startsWith(`Sur kununu, le personnel actuel et ancien évalue son entreprise${NBSP}: 5 est`));
  assert.ok(help.fr[1].endsWith("correspond à tes informations."));
  assert.ok(help.fr[2].startsWith("Sur kununu, le personnel et les apprentis, actuels et anciens, évaluent leur entreprise "
    + `formatrice${NBSP}: 5 est`));
  assert.ok(help.en[0].startsWith("On kununu, current and former employees rate their company"));
});

test("the dialogs to assign a page and to enter a value say the company in the app language", async () => {
  const shown = await inAll(async () => {
    const p = await page();
    nodes(p.rows().get("testlogistik-gmbh")).filter(n => n.tag === "button")[0].attrs.onclick();
    const assign = p.$("zuordnen-titel").textContent;
    p.$("zuordnen-link").value = LINK;
    await p.$("zuordnen-form").fire("submit", { preventDefault() {} });
    const hand = nodes(p.rows().get("beispiel-bau-ag")).filter(n => n.tag === "button")[1];
    hand.attrs.onclick();
    const handTitle = p.$("hand-titel").textContent;
    p.$("hand-wert").value = "4.2";
    p.$("hand-bewertungen").value = "12";
    await p.$("hand-form").fire("submit", { preventDefault() {} });
    return { assign, handTitle, said: p.said.filter(Boolean) };
  });
  assert.equal(shown.de.assign, "Welche kununu-Seite gehört zu Testlogistik GmbH?");
  assert.equal(shown.fr.assign, `Quelle page kununu correspond à Testlogistik GmbH${NBSP}?`);
  assert.equal(shown.en.assign, "Which kununu page belongs to Testlogistik GmbH?");
  assert.equal(shown.de.handTitle, "kununu-Wert für Beispiel Bau AG eintragen");
  assert.equal(shown.fr.handTitle, "Saisir la valeur kununu pour Beispiel Bau AG");
  assert.equal(shown.en.handTitle, "Enter the kununu value for Beispiel Bau AG");
  assert.deepEqual(shown.de.said, ["Testlogistik GmbH: Seite bei kununu zugeordnet. Der Wert kommt mit der nächsten Prüfung.",
    "Beispiel Bau AG: kununu-Wert eingetragen."]);
  assert.deepEqual(shown.fr.said, [
    `Testlogistik GmbH${NBSP}: page kununu associée. La valeur arrive avec la prochaine vérification.`,
    `Beispiel Bau AG${NBSP}: valeur kununu saisie.`]);
  assert.deepEqual(shown.en.said, ["Testlogistik GmbH: kununu page assigned. The value comes with the next check.",
    "Beispiel Bau AG: kununu value entered."]);
});

test("the choice among several companies and its messages come in the app language", async () => {
  const shown = await inAll(async () => {
    const p = await page();
    nodes(p.rows().get("probe-handel-ag")).filter(n => n.tag === "button")[0].attrs.onclick();
    const chooser = p.rows().get("wahl-probe-handel-ag");
    const words = nodes(chooser).filter(n => ["legend", "p", "a", "button"].includes(n.tag) || n.attrs.class === "choice__name")
      .map(n => (n.tag === "a" ? label(n) : text(n)));
    const assign = nodes(chooser).filter(n => n.tag === "button")[0];
    await assign.attrs.onclick();
    p.chosen.value = "";
    await assign.attrs.onclick();
    nodes(p.rows().get("probe-handel-ag")).filter(n => n.tag === "button")[0].attrs.onclick();
    p.chosen.value = LINK2;
    await nodes(p.rows().get("wahl-probe-handel-ag")).filter(n => n.tag === "button")[0].attrs.onclick();
    return { words, said: p.said.filter(Boolean) };
  });
  assert.deepEqual(shown.de.words, ["Welche ist Probe Handel AG, Bern?", "Ort und Anzahl Bewertungen helfen beim Wählen.",
    "Probe Handel AG", "Bei kununu ansehen", "Keine davon passt", "Zuordnen", "Abbrechen"]);
  assert.deepEqual(shown.fr.words, [`Laquelle est Probe Handel AG, Bern${NBSP}?`, "Le lieu et le nombre d'avis aident à choisir.",
    "Probe Handel AG", "Voir sur kununu", "Aucune ne correspond", "Associer", "Annuler"]);
  assert.deepEqual(shown.en.words, ["Which one is Probe Handel AG, Bern?", "The place and the number of reviews help you choose.",
    "Probe Handel AG", "View on kununu", "None of them matches", "Assign", "Cancel"]);
  assert.deepEqual(shown.de.said, ["Bitte eine Firma wählen oder «Keine davon passt».", "Probe Handel AG: bei kununu nicht gefunden.",
    "Probe Handel AG: Seite bei kununu zugeordnet."]);
  assert.deepEqual(shown.fr.said, [`Merci de choisir une entreprise ou «${NBSP}Aucune ne correspond${NBSP}».`,
    `Probe Handel AG${NBSP}: introuvable sur kununu.`, `Probe Handel AG${NBSP}: page kununu associée.`]);
  assert.deepEqual(shown.en.said, ["Please choose a company or “None of them matches”.", "Probe Handel AG: not found on kununu.",
    "Probe Handel AG: kununu page assigned."]);
});

test("a check announces itself in the app language", async () => {
  const shown = await inAll(async () => {
    const p = await page();
    const check = nodes(p.rows().get("beispiel-bau-ag")).filter(n => n.tag === "button")[0];
    await check.attrs.onclick({ currentTarget: check.attrs });
    return p.said[0];
  });
  assert.deepEqual(shown, { de: "Beispiel Bau AG: wird bei kununu geprüft …", fr: `Beispiel Bau AG${NBSP}: vérification sur kununu…`,
                            en: "Beispiel Bau AG: checking on kununu…" });
});
