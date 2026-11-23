// The shared search logic in French and English (#421, G10, docs/design/sprachen.md): the texts treffer-logik.js,
// suche-anzeige.js, suchbegriffe-logik.js, verworfen-woerter-logik.js, firmen-logik.js and kununu-pruefen.js build at
// run time come in the app language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the
// pages. Search terms, cantons, places, portals, company names, title words and the lines of the search profile are
// data and stay German inside a French or English sentence; German stays as it was. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const T = require("../seiten/treffer-logik.js");
const A = require("../seiten/suche-anzeige.js");
const S = require("../seiten/suchbegriffe-logik.js");
const V = require("../seiten/verworfen-woerter-logik.js");
const F = require("../seiten/firmen-logik.js");

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
function inLanguage(language, check) {
  texte.setzeSprache(language, catalogFor(language));
  try {
    return check();
  } finally {
    texte.setzeSprache();
  }
}

const inAll = check => ({ de: check(), fr: inLanguage("fr", check), en: inLanguage("en", check) });

// ---------- treffer-logik.js: rating all hits ----------

const ESTIMATE = { anzahl: 12, kosten: 0.35, dauer_minuten: 3, laden: [], nicht_ladbar: [], guthaben: 4.8, danach: 4.45,
                   reicht_fuer: null, waehrung: "CHF" };

test("the progress of rating all hits comes in the app language", () => {
  assert.deepEqual(inAll(() => T.pruefSchritt({ bewertet: 0, von: 14 }, ["a", "b", "c"], 2)), {
    de: "Stellen 1 bis 3 von 14 prüfen …",
    fr: "Évaluation des offres 1 à 3 sur 14…",
    en: "Rating jobs 1 to 3 of 14…",
  });
  assert.deepEqual(inAll(() => T.pruefSchritt({ bewertet: 4, von: 14 }, ["e"], 12)), {
    de: `Stelle 5 von 14 prüfen, seit 12${NBSP}Sekunden …`,
    fr: `Évaluation de l'offre 5 sur 14, depuis 12${NBSP}secondes…`,
    en: `Rating job 5 of 14, for 12${NBSP}seconds…`,
  });
  assert.deepEqual(inAll(() => T.inseratSchritt({ fertig: 1, von: 3 })), {
    de: "Inserat 2 von 3 holen …", fr: "Récupération de l'annonce 2 sur 3…", en: "Fetching ad 2 of 3…",
  });
});

test("the question before the run names jobs, cost and credit in the app language", () => {
  const question = inAll(() => T.confirmation(ESTIMATE, false, true));
  assert.equal(question.de.title, "12 Stellen prüfen?");
  assert.equal(question.fr.title, `Évaluer 12 offres${NBSP}?`);
  assert.equal(question.en.title, "Rate 12 jobs?");
  assert.deepEqual(question.fr.sentences, [
    "L'IA évalue 12 offres encore sans note.",
    `Cela coûte environ CHF${NBSP}0.35 et prend environ 3${NBSP}minutes.`,
    `Il reste CHF${NBSP}4.80 de crédit, ensuite environ CHF${NBSP}4.45.`,
  ]);
  assert.deepEqual(question.en.sentences, [
    "The AI rates 12 jobs without a grade yet.",
    `This costs about CHF${NBSP}0.35 and takes about 3${NBSP}minutes.`,
    `CHF${NBSP}4.80 of credit is left, afterwards about CHF${NBSP}4.45.`,
  ]);
  assert.equal(inLanguage("fr", () => T.confirmation({ ...ESTIMATE, anzahl: 1 }, true, true).title),
    `Évaluer 1 place d'apprentissage${NBSP}?`);
});

test("the cost line and a used-up credit keep the word that links to a new code", () => {
  const line = inAll(() => T.estimateLine({ ...ESTIMATE, anzahl: 2, kosten: 0.06, dauer_minuten: 1, reicht_fuer: 1, danach: 0 }));
  assert.equal(line.de, `Etwa CHF${NBSP}0.06 und 1${NBSP}Minute. Das Guthaben reicht für etwa 1 Stelle.`);
  assert.equal(line.fr, `Environ CHF${NBSP}0.06 et 1${NBSP}minute. Le crédit suffit pour environ 1 offre.`);
  assert.equal(line.en, `About CHF${NBSP}0.06 and 1${NBSP}minute. The credit is enough for about 1 job.`);
  const usedUp = inAll(() => T.costLine({ ...ESTIMATE, guthaben: 0, danach: 0 }).text);
  assert.match(usedUp.fr, /demander/);
  assert.match(usedUp.en, /request/);
});

test("the end of a run, the second look and the open hits come in the app language", () => {
  const stand = { bewertet: 10, von: 14, offen: [], ohneText: 0, gestoppt: true, kosten: 0.12 };
  assert.deepEqual(inAll(() => T.schlussText(stand, 4, "CHF")), {
    de: `10 von 14 Treffern bewertet, angehalten, noch 4 offen. Kosten: CHF${NBSP}0.12.`,
    fr: `Résultats évalués${NBSP}: 10 sur 14, arrêtée, encore 4 sans note. Coût${NBSP}: CHF${NBSP}0.12.`,
    en: `Results rated: 10 of 14, stopped, 4 still unrated. Cost: CHF${NBSP}0.12.`,
  });
  assert.equal(inLanguage("en", () => T.schlussText({ ...stand, gestoppt: false, offen: ["a", "b"] }, 0, "CHF")),
    `Results rated: 10 of 14, 2 without a usable answer, which can be retried individually. Cost: CHF${NBSP}0.12.`);
  const bewertung = { nachpruefung: { noten: [5, 4] } };
  assert.equal(inLanguage("en", () => T.nachpruefungText(bewertung, String)),
    "Checked again: rated alone, grades 5 and 4; the lower one counts.");
  assert.deepEqual(inAll(() => T.offenText(1, false)), {
    de: "1 Stelle ist noch nicht geprüft.", fr: "1 offre n'est pas encore évaluée.", en: "1 job is not rated yet.",
  });
});

test("what is searched for after the choice on Suche einstellen is a sentence of its own in every language", () => {
  assert.deepEqual(inAll(() => T.gesuchtText(["lehrstelle", "schnupperlehre"])), {
    de: "Gesucht wird: Lehrstellen und Schnupperlehren.",
    fr: `Recherche${NBSP}: places d'apprentissage et stages d'orientation.`,
    en: "Searching for: apprenticeships and trial apprenticeships.",
  });
  assert.equal(T.gesuchtText(["schnupperlehre"]), "Gesucht wird: Schnupperlehren.");
  const source = fs.readFileSync(path.join(SEITEN, "suche-einstellen.js"), "utf8");
  assert.doesNotMatch(source, /suchen\$\//, "Suche einstellen no longer cuts a word off a visible label");
  assert.match(source, /logik\.gesuchtText\(angebote\)/);
});

// ---------- suche-anzeige.js: the line of the settings, the empty list and the last search ----------

test("the summary of the search keeps search terms, cantons and places as they are", () => {
  const settings = { begriffe: ["Projektleiter", "Bauführer", "Polier", "Kalkulator"],
                     region: { kantone: ["Bern", "Solothurn"], orte: ["Thun"] }, portale: 3 };
  assert.deepEqual(inAll(() => A.zusammenfassung(settings)), {
    de: ["Sucht nach Projektleiter, Bauführer, Polier und 1 weiteren", "Kantone Bern und Solothurn", "3 Portale"],
    fr: [`Recherche${NBSP}: Projektleiter, Bauführer, Polier et 1 autre`, "Cantons Bern et Solothurn", "3 portails"],
    en: ["Searches for Projektleiter, Bauführer, Polier and 1 more", "Cantons Bern and Solothurn", "3 portals"],
  });
  const more = { begriffe: [...settings.begriffe, "Maurer"] };
  assert.deepEqual(inAll(() => A.zusammenfassung(more)[0]), {
    de: "Sucht nach Projektleiter, Bauführer, Polier und 2 weiteren",
    fr: `Recherche${NBSP}: Projektleiter, Bauführer, Polier et 2 autres`,
    en: "Searches for Projektleiter, Bauführer, Polier and 2 more",
  });
  assert.equal(inLanguage("fr", () => A.zusammenfassung({ begriffe: ["Polier"] })[0]), `Recherche${NBSP}: Polier`);
  assert.equal(inLanguage("fr", () => A.nischenText({ nischen: true, kantone: ["Bern"] }, false, true)),
    "Recherche sans lieu. Sont conservées les offres dans Bern, dans tes localités ou en télétravail.");
  assert.equal(inLanguage("en", () => A.nischenText({ nischen: true, kantone: ["Bern"] }, false, false)),
    "Searched without a place. Jobs in Bern, in your places or with remote work are kept.");
});

test("a time window of one day is a day in French and English, and stays as it was in German", () => {
  assert.deepEqual(inAll(() => A.zeitfensterWahl(1)[0].text), { de: "1 Tage", fr: "1 jour", en: "1 day" });
});

test("the empty lists and the line of the last search come in the app language", () => {
  assert.deepEqual(inLanguage("fr", () => A.leer("neu", false, "")),
    { titel: "Pas encore de recherche.", text: "La première recherche prend quelques minutes." });
  assert.equal(inLanguage("en", () => A.NOCH_NICHT.titel), "Not searched yet.");
  assert.equal(inLanguage("en", () => A.OHNE_ERWEITERUNG), "Set up the extension first.");
  const alle = [{ zustand: "neu" }, { zustand: "neu" }, { zustand: "verworfen" }];
  assert.deepEqual(inAll(() => A.letzteSuche({ datum: "2026-11-20", portale: { "jobs.ch": {} } }, alle, d => d)), {
    de: ["Letzte Suche am 2026-11-20", "jobs.ch", "3 Treffer, 2 neu"],
    fr: ["Dernière recherche le 2026-11-20", "jobs.ch", "3 résultats, 2 à voir"],
    en: ["Last search on 2026-11-20", "jobs.ch", "3 results, 2 new"],
  });
  assert.deepEqual(inLanguage("en", () => A.zeitfensterWahl(21).map(w => w.text).slice(1, 3)), ["14 days", "21 days (default)"]);
});

// ---------- verworfen-woerter-logik.js: a word of dismissed hits ----------

test("the proposal to exclude a title word keeps the word as it is", () => {
  const vorschlag = { wort: "Aussendienst", verworfen: 3, andere: 2 };
  assert.deepEqual(inAll(() => V.satz(vorschlag, "stelle-du", texte)), {
    de: "Aus den Stellen, die du verworfen hast: 3 haben «Aussendienst» im Titel.",
    fr: `Parmi les offres que tu as écartées, 3 ont «${NBSP}Aussendienst${NBSP}» dans le titre.`,
    en: "Of the jobs you discarded, 3 have “Aussendienst” in the title.",
  });
  assert.equal(inLanguage("en", () => V.knopf(vorschlag)), "Stop showing “Aussendienst”");
  assert.equal(inLanguage("fr", () => V.filterText(1, "Aussendienst")),
    `Affichée${NBSP}: 1 offre écartée avec «${NBSP}Aussendienst${NBSP}» dans le titre.`);
  assert.equal(inLanguage("en", () => V.andere(vorschlag)), "2 jobs that are not discarded also have this word in their title.");
});

// ---------- firmen-logik.js and kununu-pruefen.js: kununu ----------

test("what a kununu check says keeps the company name and kununu as names", () => {
  const gefunden = { gelesen: true, kununu: { zustand: "gefunden", wert: 3.8, bewertungen: 214 } };
  assert.deepEqual(inAll(() => F.pruefErgebnis(gefunden, "Muster AG").text), {
    de: "Muster AG: kununu 3.8 von 5, 214 Bewertungen.",
    fr: `Muster AG${NBSP}: kununu 3.8 sur 5, 214 avis.`,
    en: "Muster AG: kununu 3.8 of 5, 214 reviews.",
  });
  assert.equal(inLanguage("en", () => F.pruefErgebnis({ gelesen: true, kununu: { zustand: "keine" } }, "Muster AG").text),
    "Muster AG: no reviews on kununu yet.");
});

test("a page that could not be read says where to enter the value, without cutting a translated sentence", () => {
  const ungelesen = wo => F.pruefErgebnis({ gelesen: false }, "Muster AG", { wo }).text;
  assert.equal(ungelesen("Firmen"),
    "Bei kununu liess sich für Muster AG kein Wert lesen. Der Tab bleibt offen; der Wert lässt sich unter Firmen von Hand eintragen.");
  assert.equal(inLanguage("fr", () => ungelesen("Entreprises")),
    `Aucune valeur n'a pu être lue sur kununu pour Muster AG. L'onglet reste ouvert${NBSP}; la valeur peut être saisie à la main sous Entreprises.`);
  assert.equal(inLanguage("en", () => ungelesen("")),
    "No value could be read on kununu for Muster AG. The tab stays open; the value can be entered by hand.");
});

test("the kununu mark and the company row come in the app language", () => {
  const firma = { schluessel: "muster-ag", name: "Muster AG", treffer: [], bewerbungen: [],
                  kununu: { zustand: "gefunden", wert: 3.8, bewertungen: 6, geprueft_am: "2026-11-20", seite: "ch" } };
  assert.deepEqual(inLanguage("fr", () => F.marke(firma)),
    { text: "kununu 3.8 sur 5, peu d'avis", vorlesen: "kununu 3.8 sur 5, seulement 6 avis", art: "wenige" });
  const zeile = inLanguage("en", () => F.firmenZeile(firma, "2026-11-21"));
  assert.equal(zeile.titel, "Muster AG on kununu");
  assert.equal(zeile.datum, "Checked on 20.11.2026");
  assert.ok(zeile.angaben.includes("Only 6 reviews, not very telling."), zeile.angaben.join(" | "));
});

/** kununu-pruefen.js in a small stand-in for the page, whose wait for the extension ends at once. */
function kununuPage() {
  const window = { Texte: texte, FirmenLogik: F, addEventListener() {}, removeEventListener() {}, postMessage() {} };
  const context = { window, document: { documentElement: { dataset: { bewerbungsbegleiterErweiterung: "1" } } },
                    location: { origin: "http://127.0.0.1" }, setTimeout: fn => { queueMicrotask(fn); return 1; },
                    clearTimeout() {} };
  vm.runInNewContext(fs.readFileSync(path.join(SEITEN, "kununu-pruefen.js"), "utf8"), context);
  return window.KununuPruefen;
}

test("an extension that does not answer is said in the app language", async () => {
  // the answer is an object of the page's own realm, so only its text is compared
  const pruefe = async () => (await kununuPage().pruefe({ schluessel: "muster-ag", name: "Muster AG" })).fehler;
  assert.equal(await pruefe(), "Die Erweiterung antwortet nicht. Bitte sie neu laden und es nochmals versuchen.");
  texte.setzeSprache("en", catalogFor("en"));
  try {
    assert.equal(await pruefe(), "The extension is not responding. Please reload it and try again.");
  } finally {
    texte.setzeSprache();
  }
});

// ---------- suchbegriffe-logik.js: checking the search terms ----------

test("the texts of the check come in the app language, in du only for the du set", () => {
  assert.equal(inLanguage("fr", () => S.texte("stelle-du").satz),
    "L'IA propose, tu décides. Le profil de recherche ne change que lorsque tu appliques.");
  assert.equal(inLanguage("fr", () => S.texte("stelle-sie").satz),
    "L'IA propose, vous décidez. Le profil de recherche ne change que lorsque vous appliquez.");
  assert.equal(inLanguage("en", () => S.texte("stelle-sie").wartenNotiz),
    `Usually under 30${NBSP}seconds. The search profile does not change until you apply something.`);
  assert.equal(inLanguage("en", () => S.HAUPTKNOPF), "Apply selection");
  assert.deepEqual(inLanguage("fr", () => S.TABELLE_SPALTEN),
    ["Terme", "Recherches", "Résultats", "filtrés", "seulement via ce terme", "dès la note 4"]);
});

test("the notice about a title filter term keeps the term and names the title filter as the app does", () => {
  const beleg = { begriff: "Engineer", anzahl: 1, alle: 40, unter: 1, beispiele: ["Sales Engineer"] };
  assert.deepEqual(inAll(() => S.hinweisText(beleg)), {
    de: "«Engineer» im Titelfilter: 1 von 40 Treffern, 1 davon unter Note 4, zum Beispiel Sales Engineer.",
    fr: `«${NBSP}Engineer${NBSP}» dans le filtre de titre${NBSP}: 1 sur 40 résultats, dont 1 sous la note 4, par exemple Sales Engineer.`,
    en: "“Engineer” in the title filter: 1 of 40 results, 1 of them below grade 4, for example Sales Engineer.",
  });
  assert.equal(inLanguage("en", () => S.belegSatz({ ...beleg, anzahl: 9 })),
    "Only through “Engineer”: 9 of 40 results, 1 of them below grade 4.");
});

test("the counted numbers from a single search run say so in French and English, and stay as they were in German", () => {
  assert.deepEqual(inAll(() => S.gezaehltUnterzeile({ noetig: 1 })), {
    de: "Aus den letzten 1 Suchläufen, gezählt von der App, nicht von der KI. Treffer zählt sie bei jeder Suche, Stellen nur einmal.",
    fr: "D'après la dernière série de recherches, comptée par l'app, pas par l'IA. Elle compte les résultats à chaque recherche, les offres une seule fois.",
    en: "From the last search run, counted by the app, not by the AI. It counts results at every search, jobs only once.",
  });
  assert.equal(inLanguage("fr", () => S.gezaehltUnterzeile({ noetig: 3 })),
    "D'après les 3 dernières séries de recherches, comptées par l'app, pas par l'IA. Elle compte les résultats à chaque recherche, les offres une seule fois.");
});

test("what was applied and what is too many come in the app language", () => {
  assert.equal(inLanguage("en", () => S.uebernommen(2, 1)),
    "Applied: 2 new terms, 1 removed. The next search uses it. The previous version stays under Drafts.");
  assert.equal(inLanguage("fr", () => S.kopfTeile(1).join(" · ")), "Proposition de l'IA · 1 modification");
  const gesperrt = { gesperrt: "x", zu_viel: { positiv: 2 } };
  assert.equal(inLanguage("fr", () => S.ansage({ gesperrt: "" }, gesperrt)),
    `Encore 2 termes de trop dans «${NBSP}Le titre contient l'un d'eux${NBSP}»`);
  assert.equal(inLanguage("en", () => S.ansage(gesperrt, { gesperrt: "" })), "The selection can be applied.");
});

test("the lines of the search profile stay German in every language", () => {
  const antwort = { nischen: ["E-Learning"], nur_zeilen: [{ portale: ["jobs.ch", "job-room"], begriffe: ["Didaktik"] }] };
  const namen = check => check().map(zeile => zeile.name);
  assert.deepEqual(inLanguage("fr", () => namen(() => S.endstandZeilen(antwort))),
    ["Nischen (ohne Ort suchen)", "Nur jobs.ch, job-room"]);
  assert.deepEqual(inLanguage("en", () => S.endstand({ suchbegriffe: [], positiv: [], ausschluss: [] },
    { suchbegriffe: ["Didaktik"], positiv: [], ausschluss: [] }).map(b => b.name)),
  ["Search terms", "Title contains one of them", "Title contains none of them"]);
});

test("the counted marks keep the keyword and name the title filter as the app does", () => {
  const counts = { genug: true, begriffe: [{ begriff: "Trainer", marke: "ohne_ertrag", suchen: 6, treffer_portale: 4,
    aussortiert: 4, ohne_pflichtbezug: 0, ausserhalb_region: 0 }] };
  assert.deepEqual(inLanguage("fr", () => S.markiert(counts)), [{ name: `«${NBSP}Trainer${NBSP}»`, marke: "improductif",
    rest: `${NBSP}: 6 recherches, 4 résultats, tous filtrés par le filtre de titre.` }]);
  assert.equal(inLanguage("en", () => S.markiert(counts)[0].marke), "unproductive");
  assert.deepEqual(S.markiert(counts), [{ name: "„Trainer“", marke: "ohne Ertrag",
    rest: ": 6 Suchen, 4 Treffer, alle vom Titelfilter aussortiert." }]);
});
