// Suche einstellen, part B, and Suchbegriffe prüfen in French and English (#425, G10, docs/design/sprachen.md): what
// the scripts of both pages say at run time comes in the app language with the catalog in bewerbungen/sprachen/ as
// /uebersetzung.js hands it to the pages: the yield of the search, the title filter examples, the exclusions the AI
// proposes, the pairs searched twice, further sites, the dismissed words and the proposal of the AI on the terms. Terms,
// titles, places, portals and the grammar of the search profile are data and stay as they are; German stays as it was.
// Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const DotLine = require("../seiten/dot-line.js");
const SucheErtragLogik = require("../seiten/suche-ertrag-logik.js");
const TitelfilterLogik = require("../seiten/titelfilter-logik.js");
const KiAusschluesseLogik = require("../seiten/ki-ausschluesse-logik.js");

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
const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };
// "~" stands for the no-break space French puts before « : ? ! ; » and inside « »
const fr = value => (typeof value === "string" ? value.replaceAll("~", NBSP) : value.map(fr));

// A small stand-in for the DOM: elements by id, and what App.el builds.
function element(tag = "div", attrs = {}, kinder = []) {
  const handlers = {};
  return {
    tag, attrs, kinder, textContent: "", value: "", hidden: false, disabled: false, href: "", className: "", dataset: {},
    classList: { toggle() {} },
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type, event = {}) { return handlers[type]({ preventDefault() {}, ...event }); },
    replaceChildren(...neu) { this.kinder = neu; },
    get children() { return this.kinder; },
    setAttribute(name, value) { this.attrs = { ...this.attrs, [name]: String(value) }; },
    focus() {}, showModal() {}, scrollIntoView() {},
    querySelector() { return this.kinder.find(k => k && k.tag === "button") || null; },
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
  const listeners = {};
  const document = { getElementById: $, addEventListener() {}, dispatchEvent() {},
                     documentElement: { lang: "de", dataset: {} } };
  const app = { el, holen: async () => ({}), senden: async () => ({}), textsatz: async () => satz,
                status: (ziel, inhalt, stufe, optionen = {}) => said.push({ ziel: ziel && ziel.attrs ? ziel.attrs.id : null,
                  text: text({ kinder: [inhalt].flat() }), stufe, optionen }), ...window.App };
  const full = { Texte: texte, DotLine, SucheErtragLogik, TitelfilterLogik, KiAusschluesseLogik,
                 Meldungen: { isInputRejection: () => false }, addEventListener: (type, fn) => { listeners[type] = fn; },
                 postMessage() {}, ...window, App: app };
  const context = { window: full, document, console, location: { hash: "", origin: "http://127.0.0.1" }, CustomEvent: class {},
                    setTimeout: () => 0, clearTimeout: () => {} };
  vm.createContext(context);
  for (const name of names) vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  return { $, said, window: full };
}

// What the search brings, without DOM

const ENTRY = { suchen: 36, treffer: 40, neu: 5, ab_note_4: 3, aussortiert: 12, ohne_pflichtbezug: 2, ausserhalb_region: 4 };
const ONE = { suchen: 1, treffer: 1, neu: 1, ab_note_4: 1, aussortiert: 1, ohne_pflichtbezug: 1, ausserhalb_region: 1 };

test("the yield line of a term names its numbers in the app language, with a singular for one", async () => {
  const E = SucheErtragLogik;
  const shown = await inAll(() => [E.teile(ENTRY), E.teile(ONE), E.teile({ suchen: 2, treffer: 0, aussortiert: 1 }), E.teile(null, 2),
    E.OHNE_ERTRAG]);
  assert.deepEqual(shown.de, [
    ["36 Suchen", "40 Treffer", "5 neu", "3 ab Note 4", "12 aussortiert", "2 ohne Pflichtbezug", "4 ausserhalb der Region"],
    ["1 Suche", "1 Treffer", "1 neu", "1 ab Note 4", "1 aussortiert", "1 ohne Pflichtbezug", "1 ausserhalb der Region"],
    ["2 Suchen", "keine Treffer", "1 aussortiert"], ["noch nicht gesucht"], "ohne Ertrag"]);
  assert.deepEqual(shown.fr, [
    ["36 recherches", "40 résultats", "5 à voir", "3 dès la note 4", "12 filtrés", "2 sans mot requis", "4 hors région"],
    ["1 recherche", "1 résultat", "1 à voir", "1 dès la note 4", "1 filtré", "1 sans mot requis", "1 hors région"],
    ["2 recherches", "aucun résultat", "1 filtré"], ["pas encore recherché"], "improductif"]);
  assert.deepEqual(shown.en, [
    ["36 searches", "40 results", "5 new", "3 from grade 4", "12 filtered out", "2 without a required word", "4 outside the region"],
    ["1 search", "1 result", "1 new", "1 from grade 4", "1 filtered out", "1 without a required word", "1 outside the region"],
    ["2 searches", "no results", "1 filtered out"], ["not searched yet"], "unproductive"]);
});

test("the caption under the list says where the numbers come from, for one run and for several", async () => {
  const E = SucheErtragLogik;
  const shown = await inAll(() => [E.hinweis(0, false), E.hinweis(0, true), E.hinweis(1, true), E.hinweis(3, false, true)]);
  assert.deepEqual(shown.de, ["Nach dem nächsten Suchlauf steht hier bei jedem Begriff, was er bringt.",
    "Nach dem nächsten Suchlauf steht hier bei jedem Beruf, was er bringt.",
    "Die Zahlen stammen aus dem letzten Suchlauf. Findet die Suche eine Lehrstelle über mehrere Berufe, zählt sie bei jedem.",
    "Die Zahlen stammen aus den letzten 3 Suchläufen. Findet die Suche eine Stelle über mehrere Begriffe, zählt sie bei jedem. "
      + "„Aussortiert“ heisst: Der Titelfilter hat den Titel nicht durchgelassen. „Ohne Pflichtbezug“: Titel und Inserat nennen "
      + "keines der Pflichtwörter des Begriffs."]);
  assert.deepEqual(shown.fr, fr(["Après la prochaine série de recherches, chaque terme indique ici ce qu'il rapporte.",
    "Après la prochaine série de recherches, chaque métier indique ici ce qu'il rapporte.",
    "Les chiffres viennent de la dernière série de recherches. Si la recherche trouve une place d'apprentissage par plusieurs "
      + "métiers, elle compte pour chacun.",
    "Les chiffres viennent des 3 dernières séries de recherches. Si la recherche trouve une offre par plusieurs termes, elle "
      + "compte pour chacun. «~Filtré~» signifie~: le filtre de titre n'a pas laissé passer le titre. «~Sans mot requis~»~: ni le "
      + "titre ni l'annonce ne nomment un des mots requis du terme."]));
  assert.deepEqual(shown.en, ["After the next search run, each term shows here what it brings.",
    "After the next search run, each occupation shows here what it brings.",
    "The numbers come from the last search run. If the search finds an apprenticeship through several occupations, it counts for each.",
    "The numbers come from the last 3 search runs. If the search finds a job through several terms, it counts for each. "
      + "“Filtered out” means: the title filter did not let the title through. “Without a required word”: neither title nor ad "
      + "names any of the term's required words."]);
});

test("the places say where their numbers come from and what outside the region means, in Sie and du", async () => {
  const E = SucheErtragLogik;
  const shown = await inAll(() => [E.ortHinweis(1), E.ortHinweis(2, true, false), E.ortHinweis(2, true, true)]);
  assert.deepEqual(shown.de, [
    "Aus dem letzten Suchlauf, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen.",
    "Aus den letzten 2 Suchläufen, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen. "
      + "„Ausserhalb der Region“: Die Stelle liegt ausserhalb Ihrer Kantone und Orte, und das Inserat nennt kein Remote.",
    "Aus den letzten 2 Suchläufen, gezählt wie bei den Suchbegriffen. „Ohne Ort“ sind Suchen ohne Ortsangabe, etwa für die Nischen. "
      + "„Ausserhalb der Region“: Die Stelle liegt ausserhalb deiner Kantone und Orte, und das Inserat nennt kein Remote."]);
  assert.deepEqual(shown.fr, fr([
    "De la dernière série de recherches, comptés comme pour les mots-clés. «~Sans lieu~» désigne les recherches sans indication "
      + "de lieu, par exemple pour les niches.",
    "Des 2 dernières séries de recherches, comptés comme pour les mots-clés. «~Sans lieu~» désigne les recherches sans "
      + "indication de lieu, par exemple pour les niches. «~Hors région~»~: l'offre se trouve hors de vos cantons et lieux, et "
      + "l'annonce ne mentionne pas le télétravail.",
    "Des 2 dernières séries de recherches, comptés comme pour les mots-clés. «~Sans lieu~» désigne les recherches sans "
      + "indication de lieu, par exemple pour les niches. «~Hors région~»~: l'offre se trouve hors de tes cantons et lieux, et "
      + "l'annonce ne mentionne pas le télétravail."]));
  assert.equal(shown.en[2], "From the last 2 search runs, counted as for the search terms. “No place” means searches without a "
    + "place, for example for the niches. “Outside the region”: the job lies outside your cantons and places, and the ad does "
    + "not mention remote work.");
});

test("the places, the empty searches and the hits without a required word come in the app language", async () => {
  const E = SucheErtragLogik;
  const shown = await inAll(() => [
    E.ortName({ nischen: true }), E.ortName({ portal: "jobs.ch" }), E.ortName({ portal: "jobscout24", ort: "3000" }),
    E.ortName({ portal: "job-room", ort: "BE" }), E.ortName({ portal: "job-room", ort: "BE,SO" }), E.ortName({ portal: "jobs.ch", ort: "Thun" }),
    E.ausserhalbOrte({ ausserhalb_orte: [{ ort: "Biel", anzahl: 2 }], ausserhalb_andere: 1 }),
    E.ausserhalbOrte({ ausserhalb_orte: [{ ort: "Biel", anzahl: 2 }], ausserhalb_andere: 3 }),
    E.leerTitel(2, false), E.leerTitel(1, true),
    E.leerZeile({ begriff: "Kursplaner", portal: "jobs.ch", suchen: 1, laeufe: 1 }),
    E.leerZeile({ begriff: "Lernatelier", nische: true, portal: "job-room", suchen: 4, laeufe: 2 }),
    E.pflichtTitel([{ anzahl: 1 }]), E.pflichtTitel([{ anzahl: 2 }, { anzahl: 3 }]),
    E.pflichtZeile({ begriff: "Berufsbildner", anzahl: 1, beispiele: ["Koch EFZ"] }),
    E.pflichtZeile({ begriff: "Berufsbildner", anzahl: 4, beispiele: ["Koch EFZ", "Gärtner"] }),
    E.pflichtZeile({ begriff: "Berufsbildner", anzahl: 4 }),
  ]);
  assert.deepEqual(shown.de, ["Ohne Ort (Nischen)", "jobs.ch, ohne Ort", "jobscout24, PLZ 3000", "job-room, Kanton BE",
    "job-room, Kantone BE,SO", "jobs.ch, Thun", "Ausserhalb der Region, ohne Remote: Biel 2, andere 1",
    "Ausserhalb der Region, ohne Remote: Biel 2, andere 3", "Wo ein Begriff nichts findet (2)", "Wo ein Beruf nichts findet (1)",
    "„Kursplaner“ auf jobs.ch: 1 Suche in 1 Suchlauf, kein Treffer.",
    "„Lernatelier“ (Nische) auf job-room: 4 Suchen in 2 Suchläufen, kein Treffer.",
    "Ohne Pflichtbezug aussortiert (1)", "Ohne Pflichtbezug aussortiert (5)", "„Berufsbildner“: 1 Treffer, „Koch EFZ“",
    "„Berufsbildner“: 4 Treffer, zum Beispiel „Koch EFZ“, „Gärtner“", "„Berufsbildner“: 4 Treffer"]);
  assert.deepEqual(shown.fr, fr(["Sans lieu (niches)", "jobs.ch, sans lieu", "jobscout24, NPA 3000", "job-room, canton BE",
    "job-room, cantons BE,SO", "jobs.ch, Thun", "Hors région, sans télétravail~: Biel 2, 1 autre",
    "Hors région, sans télétravail~: Biel 2, 3 autres", "Là où un terme ne trouve rien (2)", "Là où un métier ne trouve rien (1)",
    "«~Kursplaner~» sur jobs.ch~: 1 recherche en 1 série de recherches, aucun résultat.",
    "«~Lernatelier~» (niche) sur job-room~: 4 recherches en 2 séries de recherches, aucun résultat.",
    "Filtré faute de mot requis (1)", "Filtrés faute de mot requis (5)", "«~Berufsbildner~»~: 1 résultat, «~Koch EFZ~»",
    "«~Berufsbildner~»~: 4 résultats, par exemple «~Koch EFZ~», «~Gärtner~»", "«~Berufsbildner~»~: 4 résultats"]));
  assert.deepEqual(shown.en, ["No place (niches)", "jobs.ch, no place", "jobscout24, postcode 3000", "job-room, canton BE",
    "job-room, cantons BE,SO", "jobs.ch, Thun", "Outside the region, not remote: Biel 2, 1 other",
    "Outside the region, not remote: Biel 2, 3 other", "Where a term finds nothing (2)", "Where an occupation finds nothing (1)",
    "“Kursplaner” on jobs.ch: 1 search in 1 search run, no result.",
    "“Lernatelier” (niche) on job-room: 4 searches in 2 search runs, no result.",
    "Filtered out without a required word (1)", "Filtered out without a required word (5)", "“Berufsbildner”: 1 result, “Koch EFZ”",
    "“Berufsbildner”: 4 results, for example “Koch EFZ”, “Gärtner”", "“Berufsbildner”: 4 results"]);
});

test("hits from before the app kept the query name their count with a singular for one", async () => {
  const E = SucheErtragLogik;
  const shown = await inAll(() => [E.ohneAngabe(1, false), E.ohneAngabe(5, true), E.ohneAngabe(0, false)]);
  // „sie kamen“ for one hit is the German as it was; #448 looks at it
  assert.deepEqual(shown.de, ["Ohne Angabe: 1 Treffer aus Suchläufen vor Version 0.3.3. Über welchen Begriff sie kamen, hat die "
    + "App damals nicht festgehalten.", "Ohne Angabe: 5 Treffer aus Suchläufen vor Version 0.3.3. Über welchen Beruf sie kamen, "
    + "hat die App damals nicht festgehalten.", ""]);
  assert.deepEqual(shown.fr, fr(["Non précisé~: 1 résultat de séries de recherches antérieures à la version 0.3.3. L'app "
    + "n'enregistrait pas encore par quel terme il est venu.", "Non précisé~: 5 résultats de séries de recherches antérieures à "
    + "la version 0.3.3. L'app n'enregistrait pas encore par quel métier ils sont venus.", ""]));
  assert.deepEqual(shown.en, ["Not specified: 1 result from search runs before version 0.3.3. The app did not record back then "
    + "which term it came through.", "Not specified: 5 results from search runs before version 0.3.3. The app did not record "
    + "back then which occupation they came through.", ""]);
});

// The title filter examples, without DOM

const EXAMPLES = { lauf: true, positiv: [{ begriff: "Software", anzahl: 8, beispiele: ["Software Engineer"] }, { begriff: "Kurs", anzahl: 1 }],
  ausschluss: [{ begriff: "Sales (ganzes Wort)", anzahl: 1, beispiele: ["Sales Manager"] }], ohne_begriff: { anzahl: 1 } };

test("the title filter examples come in the app language, with the terms and titles as they are", async () => {
  const L = TitelfilterLogik;
  const shown = await inAll(() => [L.ansicht(["Software", "Kurs", "Web"], ["Sales (ganzes Wort)"], EXAMPLES),
    L.ansicht([], [], null).leer, L.ansicht(["Kurs"], [], { lauf: false }).hinweis, L.ohneBegriff({ anzahl: 0 }),
    L.ohneBegriff({ anzahl: 3, beispiele: ["Koch"] })]);
  const lines = view => view.gruppen.map(g => [g.titel, ...g.eintraege.map(e => `${e.begriff} | ${e.zeile}`), g.nachsatz]);
  assert.deepEqual(lines(shown.de[0]), [["Titel, die passen", "Software | 8 Titel durchgelassen, zum Beispiel „Software Engineer“",
    "Kurs | 1 Titel durchgelassen", "Web | Im letzten Suchlauf kein Titel. Begriffe mit höchstens drei Buchstaben passen nur als ganzes Wort.",
    "Ohne passenden Begriff aussortiert: 1 Titel"],
    ["Titel, die nicht passen", "Sales (ganzes Wort) | 1 Titel aussortiert, zum Beispiel „Sales Manager“", ""]]);
  assert.deepEqual(lines(shown.fr[0]), fr([["Titres qui correspondent",
    "Software | 8 titres laissés passer, par exemple «~Software Engineer~»", "Kurs | 1 titre laissé passer",
    "Web | Aucun titre lors de la dernière série de recherches. Les termes de trois lettres au plus ne correspondent qu'en mot entier.",
    "Filtrés faute de terme correspondant~: 1 titre"],
    ["Titres qui ne correspondent pas", "Sales (ganzes Wort) | 1 titre filtré, par exemple «~Sales Manager~»", ""]]));
  assert.deepEqual(lines(shown.en[0]), [["Titles that fit", "Software | 8 titles let through, for example “Software Engineer”",
    "Kurs | 1 title let through", "Web | No title in the last search run. Terms of at most three letters only match as a whole word.",
    "Filtered out for lack of a matching term: 1 title"],
    ["Titles that do not fit", "Sales (ganzes Wort) | 1 title filtered out, for example “Sales Manager”", ""]]);
  assert.deepEqual(shown.de.slice(1), ["Kein Titelfilter", "Beispiele gibt es nach dem nächsten Suchlauf.",
    "Ohne passenden Begriff aussortiert: kein Titel.", "Ohne passenden Begriff aussortiert: 3 Titel, zum Beispiel „Koch“"]);
  assert.deepEqual(shown.fr.slice(1), fr(["Aucun filtre de titre", "Des exemples apparaîtront après la prochaine série de recherches.",
    "Filtrés faute de terme correspondant~: aucun titre.", "Filtrés faute de terme correspondant~: 3 titres, par exemple «~Koch~»"]));
  assert.deepEqual(shown.en.slice(1), ["No title filter", "Examples come after the next search run.",
    "Filtered out for lack of a matching term: no title.", "Filtered out for lack of a matching term: 3 titles, for example “Koch”"]);
});

// The exclusions the AI proposes, without DOM

const STAND = { verfuegbar: true, anzahl: 5, mindestens: 3 };
const PROPOSAL = { nummer: 0, art: "ausschluss", ort: "Im Inserat", kategorie: "Branche", wert: "Detailhandel", treffer: [{}, {}] };
const TITLE = { ...PROPOSAL, art: "titel_ausschluss", ort: "Im Titel", wert: "Praktikum" };

test("the box of the AI exclusions speaks the app language, Sie and du, with the value as the AI named it", async () => {
  const L = KiAusschluesseLogik;
  const shown = await inAll(() => [L.einleitung(STAND, "stelle-sie", texte), L.wasGeht("stelle-du", texte),
    L.leer({ ...STAND, anzahl: 0 }, "stelle-sie", texte), L.leer({ ...STAND, anzahl: 1 }, "stelle-du", texte),
    L.leer({ ...STAND, anzahl: 2 }, "stelle-sie", texte), L.ansicht({ ...STAND, anzahl: 1 }, true, "stelle-du", texte).satz]);
  assert.equal(shown.de[3], "Erst 1 verworfene Stelle, die das Suchprofil noch nicht ausschliesst. Ab 3 verworfenen Stellen kann "
    + "die KI hier vorschlagen, was du künftig nicht mehr sehen willst.");
  assert.deepEqual(shown.fr, fr([
    "L'IA cherche des motifs communs, comme le taux d'activité, le secteur, le lieu de travail ou des mots du titre, dans les 5 "
      + "offres écartées que le profil de recherche n'exclut pas encore. Seul ce que vous appliquez entre dans le profil de recherche.",
    "Seulement le titre, l'entreprise, le lieu et le taux d'activité des offres écartées. Pas de CV, pas de profil de recherche, "
      + "rien sur toi.",
    "Aucune offre écartée que le profil de recherche n'exclut pas encore. À partir de 3 offres écartées, l'IA peut proposer ici "
      + "ce que vous ne voulez plus voir.",
    "Seulement 1 offre écartée que le profil de recherche n'exclut pas encore. À partir de 3 offres écartées, l'IA peut proposer "
      + "ici ce que tu ne veux plus voir.",
    "Seulement 2 offres écartées que le profil de recherche n'exclut pas encore. À partir de 3 offres écartées, l'IA peut proposer "
      + "ici ce que vous ne voulez plus voir.",
    "Tu peux continuer à appliquer ou retirer les propositions ci-dessous. De nouvelles propositions sont possibles à partir de "
      + "3 offres écartées que le profil de recherche n'exclut pas encore."]));
  assert.deepEqual(shown.en.slice(0, 3), [
    "The AI looks for common reasons, such as workload, industry, place of work or words in the title, in the 5 discarded jobs "
      + "that the search profile does not exclude yet. Only what you apply goes into the search profile.",
    "Only title, company, place and workload of the discarded jobs. No CV, no search profile, nothing about you.",
    "No discarded jobs that the search profile does not exclude yet. Once there are 3 discarded jobs, the AI can suggest here "
      + "what you no longer want to see."]);
  const du = await inLanguage("fr", () => L.einleitung(STAND, "stelle-du", texte));
  assert.equal(du, "L'IA cherche des motifs communs, comme le taux d'activité, le secteur, le lieu de travail ou des mots du titre, "
    + "dans les 5 offres écartées que le profil de recherche n'exclut pas encore. Seul ce que tu appliques entre dans le profil "
    + "de recherche.");
});

test("a proposal of the AI says where it goes and what happened, the value and its place in quotes", async () => {
  const L = KiAusschluesseLogik;
  const shown = await inAll(() => [L.KNOPF, L.RUECKGAENGIG, L.NEU_FRAGEN, L.DENKT, L.stuetze(PROPOSAL), L.wo(PROPOSAL), L.wo(TITLE),
    L.knopfLabel(PROPOSAL), L.uebernommen(PROPOSAL), L.uebernommen(TITLE), L.zurueck(PROPOSAL), L.schonDa(PROPOSAL),
    L.nichtGeladen("x"), L.nichtUebernommen("x"), L.nichtZurueck("x")]);
  assert.deepEqual(shown.de, ["Übernehmen", "Rückgängig", "Neu vorschlagen lassen",
    "Die KI sucht nach gemeinsamen Gründen, das dauert einen Moment …", "Aus 2 verworfenen Stellen:",
    "Branche, kommt unter «Im Inserat»", "Kommt unter «Im Titel»", "«Detailhandel» übernehmen",
    "«Detailhandel» steht jetzt unter «Im Inserat». Gilt ab der nächsten Einschätzung.",
    "«Praktikum» steht jetzt unter «Im Titel». Gilt ab der nächsten Suche.", "«Detailhandel» steht nicht mehr unter «Im Inserat».",
    "«Detailhandel» steht schon unter «Im Inserat».", "Ausschlüsse von der KI lassen sich gerade nicht anbieten. x",
    "Nicht übernommen. x", "Nicht zurückgenommen. x"]);
  assert.deepEqual(shown.fr, fr(["Appliquer", "Annuler", "Demander de nouvelles propositions",
    "L'IA cherche des motifs communs, cela prend un moment…",
    "D'après 2 offres écartées~:", "Branche, s'ajoute sous «~Im Inserat~»", "S'ajoute sous «~Im Titel~»", "Appliquer «~Detailhandel~»",
    "«~Detailhandel~» figure maintenant sous «~Im Inserat~». S'applique dès la prochaine évaluation.",
    "«~Praktikum~» figure maintenant sous «~Im Titel~». S'applique dès la prochaine recherche.",
    "«~Detailhandel~» ne figure plus sous «~Im Inserat~».", "«~Detailhandel~» figure déjà sous «~Im Inserat~».",
    "Les exclusions de l'IA ne peuvent pas être proposées pour le moment. x", "Non appliqué. x", "Non retiré. x"]));
  assert.deepEqual(shown.en, ["Apply", "Undo", "Ask for new proposals", "The AI is looking for common reasons, this takes a moment…",
    "From 2 discarded jobs:", "Branche, goes under “Im Inserat”", "Goes under “Im Titel”", "Apply “Detailhandel”",
    "“Detailhandel” is now under “Im Inserat”. Applies from the next assessment.",
    "“Praktikum” is now under “Im Titel”. Applies from the next search.", "“Detailhandel” is no longer under “Im Inserat”.",
    "“Detailhandel” is already under “Im Inserat”.", "Exclusions from the AI cannot be offered right now. x", "Not applied. x",
    "Not withdrawn. x"]);
});

test("the count of the proposals takes the singular for one, in Sie and du, and German stays as it was", async () => {
  const L = KiAusschluesseLogik;
  const shown = await inAll(() => [L.fertig(0, "stelle-sie", texte), L.fertig(1, "stelle-sie", texte), L.fertig(1, "stelle-du", texte),
    L.fertig(2, "stelle-sie", texte), L.fertig(2, "stelle-du", texte)]);
  assert.deepEqual(shown.de, ["Die KI hat keinen gemeinsamen Grund gefunden. Am Suchprofil hat sich nichts geändert.",
    "1 Vorschlag. Am Suchprofil ändert sich erst etwas, wenn Sie ihn übernehmen.",
    "1 Vorschlag. Am Suchprofil ändert sich erst etwas, wenn du ihn übernimmst.",
    "2 Vorschläge. Am Suchprofil ändert sich erst etwas, wenn Sie einen übernehmen.",
    "2 Vorschläge. Am Suchprofil ändert sich erst etwas, wenn du einen übernimmst."]);
  assert.deepEqual(shown.fr, ["L'IA n'a trouvé aucun motif commun. Le profil de recherche n'a pas changé.",
    "1 proposition. Le profil de recherche ne change que lorsque vous l'appliquez.",
    "1 proposition. Le profil de recherche ne change que lorsque tu l'appliques.",
    "2 propositions. Le profil de recherche ne change que lorsque vous en appliquez une.",
    "2 propositions. Le profil de recherche ne change que lorsque tu en appliques une."]);
  assert.deepEqual(shown.en, ["The AI found no common reason. The search profile has not changed.",
    "1 proposal. The search profile only changes once you apply it.", "1 proposal. The search profile only changes once you apply it.",
    "2 proposals. The search profile only changes once you apply one.", "2 proposals. The search profile only changes once you apply one."]);
});

// The scripts of Suche einstellen, part B

test("the yield of the places names each place with a colon in the app language", async () => {
  const shown = await inAll(() => {
    const page = run(["suche-ertrag.js"], { Suchliste: { ertrag() {} } });
    page.window.SucheErtrag.zeige({ art: "stelle", laeufe: 1, begriffe: [], leer: [], ohne_angabe: 0,
      orte: [{ portal: "jobs.ch", ort: "Thun", suchen: 1, treffer: 0 }] }, "stelle-sie");
    return text(page.$("orte-ertrag-liste").kinder[0]);
  });
  // dot-line.js puts a no-break space before «·» and a hidden comma after it, which screen readers hear
  assert.deepEqual(shown, { de: fr("jobs.ch, Thun: 1 Suche~·, keine Treffer"), fr: fr("jobs.ch, Thun~: 1 recherche~·, aucun résultat"),
    en: fr("jobs.ch, Thun: 1 search~·, no results") });
});

test("Doppelt gesucht offers Rückgängig and says a failed load in the app language", async () => {
  const shown = await inAll(async () => {
    let fail = false;
    const pair = { id: "p", text: "…", behalten: "…", behalten_name: "…", optionen: [{ seite: "a", knopf: "…", name: "…" }] };
    const page = run(["doppelt-gesucht.js"], { App: {
      holen: async () => { if (fail) throw new Error("x"); return { paare: [pair] }; },
      senden: async () => ({ text: "…", beruf: "Kursplaner", rueckgaengig: "a".repeat(64) }) } });
    await page.window.DoppeltGesucht.lade();
    const knopf = nodes(page.$("doppelt-liste")).find(n => n.tag === "button");
    await knopf.fire("click");
    fail = true;
    await page.window.DoppeltGesucht.lade();
    return [page.said[0].optionen.aktion.text, page.said[1].text];
  });
  assert.deepEqual(shown.de, ["Rückgängig", "Doppelt gesuchte Begriffe liessen sich nicht laden: x"]);
  assert.deepEqual(shown.fr, ["Annuler", fr("Impossible de charger les termes recherchés en double~: x")]);
  assert.deepEqual(shown.en, ["Undo", "The terms searched twice could not be loaded: x"]);
});

test("further sites say saved and what the extension does in the app language", async () => {
  const shown = await inAll(async () => {
    const page = run(["weitere-seiten.js"], { App: {
      holen: async () => ({ eigener_schluessel: true, max_seiten: 5, seiten: [] }),
      senden: async () => ({ eigener_schluessel: true, max_seiten: 5, seiten: [] }) } });
    await settle();
    page.$("seiten").value = "https://beispiel.ch/stellen";
    await page.$("seiten-speichern").fire("click");
    page.$("seiten").value = "";
    await page.$("seiten-speichern").fire("click");
    page.$("zugriff").fire("click");
    return page.said.map(m => m.text);
  });
  assert.deepEqual(shown.de, ["Gespeichert. Die Seiten kommen bei der nächsten Suche dazu.", "Gespeichert.",
    "Die Browser-Erweiterung antwortet nicht. Bitte diese Seite im Browser mit der Erweiterung öffnen."]);
  assert.deepEqual(shown.fr, ["Enregistré. Les sites s'ajoutent dès la prochaine recherche.", "Enregistré.",
    "L'extension du navigateur ne répond pas. Merci d'ouvrir cette page dans le navigateur qui a l'extension."]);
  assert.deepEqual(shown.en, ["Saved. The sites are added from the next search on.", "Saved.",
    "The browser extension does not answer. Please open this page in the browser with the extension."]);
});

test("the word from dismissed hits says a failed load and a failed save in the app language", async () => {
  const shown = await inAll(async () => {
    const page = run(["verworfen-woerter.js"], { VerworfenWoerterLogik: {}, App: {
      holen: async () => { throw new Error("x"); } } });
    await settle();
    return page.said.map(m => m.text);
  });
  assert.deepEqual(shown, { de: ["Der Vorschlag aus den verworfenen Stellen fehlt. x"],
    fr: ["La proposition tirée des offres écartées manque. x"], en: ["The proposal from the discarded jobs is missing. x"] });
});

test("the AI exclusions page script shows the count, the value and its buttons in the app language", async () => {
  const shown = await inAll(async () => {
    const page = run(["ki-ausschluesse.js"], { TrefferLogik: { costLine: () => ({ text: "" }) }, App: {
      holen: async () => ({ ...STAND }),
      senden: async route => (route.endsWith("/vorschlag") ? { vorschlag: "v", vorschlaege: [PROPOSAL] } : {}) } });
    await settle();
    await page.$("ki-ausschluesse-knopf").fire("click");
    const karte = page.$("ki-ausschluesse-liste").kinder[0];
    return { status: page.said.map(m => m.text), knopf: page.$("ki-ausschluesse-knopf").textContent,
             wert: text(nodes(karte).find(n => n.tag === "strong")), uebernehmen: text(nodes(karte).find(n => n.tag === "button")) };
  });
  assert.deepEqual(shown.de, { status: ["Die KI sucht nach gemeinsamen Gründen, das dauert einen Moment …",
    "1 Vorschlag. Am Suchprofil ändert sich erst etwas, wenn Sie ihn übernehmen."], knopf: "Neu vorschlagen lassen",
    wert: "«Detailhandel»", uebernehmen: "Übernehmen" });
  assert.deepEqual(shown.fr, { status: ["L'IA cherche des motifs communs, cela prend un moment…",
    "1 proposition. Le profil de recherche ne change que lorsque vous l'appliquez."], knopf: "Demander de nouvelles propositions",
    wert: fr("«~Detailhandel~»"), uebernehmen: "Appliquer" });
  assert.deepEqual(shown.en, { status: ["The AI is looking for common reasons, this takes a moment…",
    "1 proposal. The search profile only changes once you apply it."], knopf: "Ask for new proposals",
    wert: "“Detailhandel”", uebernehmen: "Apply" });
});

// Suchbegriffe prüfen

const LIMITS = { teile: ["Danach: 3 von 15 Suchbegriffen", "bis 6 Suchen pro Portal"], gesperrt: null,
  zu_viel: { suchbegriffe: 0, positiv: 0, ausschluss: 0 }, erlaubt: { suchbegriffe: 15, positiv: 30, ausschluss: 30 } };
const ADD = { nummer: 0, bereich: "keywords", bereich_name: "Suchbegriffe", zu_allgemein: true,
  satz: "Suchbegriff «Datenanalyst» aufnehmen", entfaellt: [], neu: ["Datenanalyst"], grund: "Steht im Lebenslauf.", beleg: null };
const TERMS = { vorschlag: "v2", runde: 2, aenderungen: [ADD], zusammenfassung: "Eine Änderung.", geaendert: "Weniger Begriffe.",
  hinweis: "Trainer behalten", treffer: 40, seit: "2026-11-01", modell: "claude-sonnet-5-5", kosten_usd: 0.03, waehrung: "CHF",
  datum: "2026-11-21", jetzt: { suchbegriffe: ["Python"], positiv: [], ausschluss: [] },
  bisherige: { suchbegriffe: ["Python"], positiv: [], ausschluss: [] },
  endstand: { suchbegriffe: ["Python", "Datenanalyst"], positiv: [], ausschluss: [] }, entfaellt: [], grenzen: LIMITS };

class FakeElement {
  constructor(tag) { Object.assign(this, { tag, attrs: new Map(), children: [], listeners: {}, className: "", value: "", style: {} }); }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.has(name) ? this.attrs.get(name) : null; }
  removeAttribute(name) { this.attrs.delete(name); }
  get hidden() { return this.attrs.has("hidden"); }
  set hidden(value) { if (value) this.attrs.set("hidden", ""); else this.attrs.delete("hidden"); }
  append(...nodes) { this.children.push(...nodes.map(node => (node instanceof FakeElement ? node : String(node)))); }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  get textContent() { return this.children.map(child => (child instanceof FakeElement ? child.textContent : child)).join(""); }
  set textContent(value) { this.replaceChildren(...(value === "" ? [] : [String(value)])); }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  click() { for (const handler of this.listeners.click || []) handler(); if (this.onclick) this.onclick(); }
  querySelector(tag) { return this.children.find(child => child instanceof FakeElement && child.tag === tag) || null; }
  focus() {}
}

function fakeEl(tag, attributes = {}, ...children) {
  const created = new FakeElement(tag);
  for (const [name, value] of Object.entries(attributes || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "class") created.className = value;
    else if (name.startsWith("on") && typeof value === "function") created.addEventListener(name.slice(2), value);
    else created.setAttribute(name, value);
  }
  created.append(...children.flat().filter(child => child !== null && child !== undefined && child !== false));
  return created;
}

/** Runs Suchbegriffe prüfen; `answers` maps a route to its answer, an Error, or a function of the body giving one. */
async function termsPage(answers) {
  const elements = new Map();
  const statuses = [];
  const document = { getElementById: id => elements.get(id) || elements.set(id, new FakeElement("div")).get(id) };
  const answer = async (route, body) => {
    const found = typeof answers[route] === "function" ? answers[route](body) : answers[route];
    if (found instanceof Error) throw found;
    if (found === undefined) throw new Error(`unexpected route ${route}`);
    return found;
  };
  const window = { Texte: texte, DotLine, Meldungen: { clearInputError() {} }, Einwilligung: { zeile() {} },
    App: { el: fakeEl, holen: answer, senden: answer, textsatz: async () => "stelle-sie",
           status: (target, message, stufe, optionen = {}) => statuses.push({ message, optionen }) } };
  const context = { window, document, console, setTimeout: () => 0, CustomEvent: class {} };
  vm.createContext(context);
  for (const name of ["treffer-logik.js", "suchbegriffe-logik.js", "suchbegriffe-schalter.js", "suchbegriffe-gezaehlt.js", "suchbegriffe.js"]) {
    vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  }
  await settle();
  return { $: id => document.getElementById(id), statuses };
}

const BASE = { "/api/suchbegriffe/hinweis": { verfuegbar: true, treffer: 40, seit: "2026-11-01" },
  "/api/ki/status": { einwilligung: null }, "/api/suchbegriffe/gezaehlt": { verfuegbar: false },
  "/api/suchbegriffe/schaetzung": { verfuegbar: false }, "/api/suchbegriffe/endstand": { veraltet: false, ...TERMS } };

const notice = page => [page.$("meldung-titel").textContent, page.$("meldung-text").textContent,
  ...page.$("meldung-knoepfe").children.map(button => button.textContent)];

test("a proposal of the second round names its round, the hint and the former proposal in the app language", async () => {
  const shown = await inAll(async () => {
    const page = await termsPage({ ...BASE, "/api/suchbegriffe/vorschlag": TERMS });
    const flags = page.$("aenderungen").children[0].children[0].children.filter(child => child instanceof FakeElement).map(f => f.textContent);
    return [page.$("geaendert").textContent, page.$("ihr-hinweis").textContent, flags[0]];
  });
  assert.deepEqual(shown.de, ["Geändert gegenüber Vorschlag 1: Weniger Begriffe.", "Ihr Hinweis: «Trainer behalten»", "zu allgemein"]);
  assert.deepEqual(shown.fr, fr(["Modifié par rapport à la proposition 1~: Weniger Begriffe.",
    "Votre remarque~: «~Trainer behalten~»", "trop général"]));
  assert.deepEqual(shown.en, ["Changed from proposal 1: Weniger Begriffe.", "Your note: “Trainer behalten”", "too general"]);
});

test("taking the proposal over offers to undo and to search, and discarding it says nothing changed", async () => {
  const shown = await inAll(async () => {
    const page = await termsPage({ ...BASE, "/api/suchbegriffe/vorschlag": TERMS,
      "/api/suchbegriffe/uebernehmen": { neu: 1, entfallen: 0, verschoben: 0, vorher: "a".repeat(64), nachher: "b".repeat(64) } });
    page.$("uebernehmen").click();
    await settle();
    const taken = [page.statuses[0].optionen.aktion.text, page.$("uebernehmen-grund").textContent];
    page.$("verwerfen").click();
    return [...taken, ...notice(page)];
  });
  // „Vorschlag verworfen“ is the title's own key (UI/UX ruling #425), so «Verworfen» of Stellen stays «Écartées»
  assert.deepEqual(shown.de, ["Rückgängig machen", "Jetzt suchen", "Vorschlag verworfen", "Am Suchprofil hat sich nichts geändert.",
    "Neu vorschlagen"]);
  assert.deepEqual(shown.fr, ["Annuler", "Rechercher maintenant", "Proposition écartée", "Le profil de recherche n'a pas changé.",
    "Proposer à nouveau"]);
  assert.deepEqual(shown.en, ["Undo", "Search now", "Proposal discarded", "The search profile has not changed.", "Suggest again"]);
});

test("a stale proposal is known by the action the app names, not by its German words", async () => {
  const stale = message => Object.assign(new Error(message), { daten: { fehler: message, aktion: "vorschlag-veraltet" }, status: 400 });
  const shown = await inAll(async () => {
    // the server's message in the page's language, as _fehler sends it
    const message = `${texte.t("Vorschlag veraltet")}. …`;
    const page = await termsPage({ ...BASE, "/api/suchbegriffe/vorschlag": TERMS, "/api/suchbegriffe/uebernehmen": stale(message) });
    page.$("uebernehmen").click();
    await settle();
    return [page.$("vorschlag").hidden, ...notice(page)];
  });
  assert.deepEqual(shown.de, [true, "Vorschlag veraltet", "Vorschlag veraltet. …", "Neu vorschlagen"]);
  assert.deepEqual(shown.fr, [true, "Proposition dépassée", "Proposition dépassée. …", "Proposer à nouveau"]);
  assert.deepEqual(shown.en, [true, "Proposal out of date", "Proposal out of date. …", "Suggest again"]);
});

test("another refusal of the takeover stays in the status line, even if it starts like a stale one", async () => {
  const page = await termsPage({ ...BASE, "/api/suchbegriffe/vorschlag": TERMS,
    "/api/suchbegriffe/uebernehmen": new Error("Vorschlag veraltet, aber anders") });
  page.$("uebernehmen").click();
  await settle();
  assert.equal(page.$("vorschlag").hidden, false);
  assert.deepEqual(page.statuses.map(s => s.message), ["Vorschlag veraltet, aber anders"]);
});

test("a failed proposal, an empty hint, a cancel and a search without jobs speak the app language", async () => {
  const shown = await inAll(async () => {
    const failed = await termsPage({ ...BASE, "/api/suchbegriffe/vorschlag": new Error("x") });
    const failedNotice = notice(failed);
    failed.$("neu-vorschlagen").click();
    failed.$("abbrechen").click();
    const apprenticeship = await termsPage({ ...BASE, "/api/suchbegriffe/hinweis": { verfuegbar: false } });
    return [...failedNotice, failed.statuses[0].message, ...notice(failed), ...notice(apprenticeship)];
  });
  assert.deepEqual(shown.de, ["", "x", "Nochmals versuchen", "Bitte schreiben, was anders sein soll.", "Abgebrochen",
    "Am Suchprofil hat sich nichts geändert.", "Neu vorschlagen", "Nur bei der Stellensuche",
    "Suchbegriffe prüfen gibt es vorerst nur bei der Stellensuche."]);
  assert.deepEqual(shown.fr, ["", "x", "Réessayer", "Merci d'écrire ce qui doit changer.", "Annulé",
    "Le profil de recherche n'a pas changé.", "Proposer à nouveau", "Seulement pour la recherche d'emploi",
    "La vérification des mots-clés n'existe pour l'instant que pour la recherche d'emploi."]);
  assert.deepEqual(shown.en, ["", "x", "Try again", "Please write what should be different.", "Cancelled",
    "The search profile has not changed.", "Suggest again", "Only for the job search",
    "Checking search terms is only available for the job search for now."]);
});

test("the former proposal can be shown again under its number in the app language", async () => {
  const shown = await inAll(async () => {
    const page = await termsPage({ ...BASE, "/api/suchbegriffe/vorschlag": body => (body && body.hinweis ? TERMS : { ...TERMS, runde: 1, geaendert: "" }) });
    page.$("anders-text").value = "Trainer behalten";
    page.$("neu-vorschlagen").click();
    await settle();
    return page.$("frueher").textContent;
  });
  assert.deepEqual(shown, { de: "Vorschlag 1 zeigen", fr: "Afficher la proposition 1", en: "Show proposal 1" });
});

test("the page title says Check search terms while the cost task on Einstellungen keeps Checking search terms", async () => {
  const EinstellungenLogik = require("../seiten/einstellungen-logik.js");
  const budget = { monat: "2026-11", eingerichtet: true, vermittlung: true, eigener_schluessel: false, guthaben_chf: 5,
                   verbraucht_chf: 1, kosten_usd: 1 };
  const costs = { monat_usd: 1, gesamt_usd: 1, aufrufe: 2, aufgaben: { terms: { aufrufe: 2, usd: 1 } } };
  const shown = await inAll(() => [texte.t("Suchbegriffe prüfen"),
    EinstellungenLogik.budgetView(budget, costs).rows.map(row => row.label)[0]]);
  assert.deepEqual(shown, { de: ["Suchbegriffe prüfen", "Suchbegriffe prüfen"], fr: ["Vérifier les mots-clés", "Vérifier les mots-clés"],
    en: ["Check search terms", "Checking search terms"] });
});
