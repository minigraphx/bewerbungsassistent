// Meine Angaben in French and English, the page around the form (#432, G10, docs/design/sprachen.md): the steps, the
// start with the choice of the setup, the buttons between the steps, an entry of a list, the lines the form does not
// know and the last step with its result speak the app language. The page runs here as build_template.py builds it,
// with a stand-in for the app; the file for sharing has no texte.js and stays German. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { FakeNode, findAll } = require("./fake_dom.cjs");
const { catalogFor, fr } = require("./catalog_for.cjs");

const SRC = path.join(__dirname, "..", "src");
const SEITEN = path.join(__dirname, "..", "..", "bewerbungen", "seiten");
const FORM = fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8");
const SHARED = ["words.js", "validate.js", "model.js", "presets.js", "steps.js", "dom.js", "documents.js", "zip.js",
  "uploadstore.js", "uploads.js"];
const APP = ["kindguess.js", "droparea.js", "appuploads.js", "appestimate.js", "prefill.js", "replacechoice.js"];
const PAGE_SCRIPTS = ["texte.js", "dateien-logik.js", "treffer-logik.js"];
const ESTIMATE = { anzahl: 0, kosten: 0, dauer_minuten: 0, waehrung: "USD", guthaben: null, danach: null, nicht_gelesen: [], gekuerzt: [] };
const CHOICE = { track: "job", anrede: "sie", rav: true, gewaehlt: true };
const OTHER_LINES = { daten: {}, fremd: [{ datei: "suchprofil.md", titel: "Suchprofil", ueberschrift: "Region", abschnitt: "searchJob", zeilen: ["- Orte (jobs.ch): Bern"] }] };

/** A node that takes plain strings among its children, as the DOM does (app.js gives replaceChildren text too). */
class PageNode extends FakeNode {
  append(...nodes) { super.append(...nodes.map(PageNode.text)); }
  replaceChildren(...nodes) { super.replaceChildren(...nodes.map(PageNode.text)); }
  static text(node) { return typeof node === "string" ? { textContent: node } : node; }
}

const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const texts = (node, tag) => byTag(node, tag).map((n) => n.textContent);
const settle = async () => { for (let i = 0; i < 20; i += 1) await new Promise((resolve) => setImmediate(resolve)); };

/** The stand-in for the app: what overview() returns and what a take-over answers. */
function fakeBackend({ stand = null, wahl = CHOICE, grundlagen = null, result = null } = {}) {
  return () => ({
    overview: async () => ({ wahl, stand, lebenslauf: null, grundlagen, unterlagen: [], vorhanden: [], tags: [] }),
    keep: async () => ({}),
    discard: async () => ({}),
    estimatePrefill: async () => ESTIMATE,
    takeOver: async () => result,
  });
}

/**
 * The page in one sandbox, as build_template.py inlines it; `language` sets the catalog before the scripts run, as
 * /uebersetzung.js does. Without a backend it is the file for sharing, which loads no script of the app.
 */
async function openPage({ language = null, backend = null } = {}) {
  const fixed = Object.fromEntries(["main", "steps", "autosave"].map((id) => [id, Object.assign(new PageNode("div"), { id })]));
  fixed.main.querySelectorAll = () => [];
  fixed.main.querySelector = () => null;
  const definition = Object.assign(new PageNode("script"), { text: FORM });
  const document = {
    createElement: (tag) => new PageNode(tag),
    createTextNode: (text) => ({ textContent: text }),
    getElementById: (id) => (id === "form-definition" ? definition : fixed[id]
      ?? [fixed.main, fixed.steps].flatMap((root) => findAll(root, (n) => n.id === id))[0] ?? null),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
    body: { append() {} },
    activeElement: null,
  };
  const page = vm.createContext({
    document, console, URLSearchParams, TextEncoder, TextDecoder, setImmediate,
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    location: { hash: "", pathname: "/angaben", search: "" }, history: { replaceState() {} },
    addEventListener() {}, setTimeout: () => 0, clearTimeout() {}, scrollTo() {},
    ...(backend ? { createAppBackend: backend } : {}),
  });
  page.window = page;
  const run = (folder, name) => vm.runInContext(fs.readFileSync(path.join(folder, name), "utf8"), page, { filename: name });
  if (backend) PAGE_SCRIPTS.forEach((name) => run(SEITEN, name));
  SHARED.forEach((name) => run(SRC, name));
  if (backend) APP.forEach((name) => run(SRC, name));
  if (language) page.Texte.setzeSprache(language, catalogFor(language));
  run(SRC, "app.js");
  await settle();
  const at = (step) => { vm.runInContext(`goTo(${step})`, page); return fixed.main; };
  return { page, main: fixed.main, nav: fixed.steps, at, eval: (code) => vm.runInContext(code, page) };
}

const stepLabels = (nav) => findAll(nav, (n) => n.className === "step__label").map((n) => n.textContent);
const stepMetas = (nav) => findAll(nav, (n) => n.className === "step__meta").map((n) => n.textContent);
const buttons = (node) => texts(node, "button");

test("the steps of the app say their names and lines in the app language", async () => {
  const de = await openPage({ backend: fakeBackend() });
  const french = await openPage({ language: "fr", backend: fakeBackend() });
  const english = await openPage({ language: "en", backend: fakeBackend() });

  assert.deepEqual(stepLabels(de.nav), ["Start", "Person und Kontakt", "Werdegang", "Können", "Was Sie suchen", "Wie Sie schreiben", "Übernehmen"]);
  assert.equal(stepMetas(de.nav)[0], "Unterlagen");
  assert.deepEqual(stepLabels(french.nav), ["Début", "Personne et contact", "Parcours", "Compétences", "Ce que vous cherchez", "Votre façon d'écrire", "Appliquer"]);
  assert.equal(stepMetas(french.nav)[0], "Documents");
  assert.deepEqual(stepLabels(english.nav), ["Start", "Person and contact", "Career", "Skills", "What you are looking for", "How you write", "Apply"]);
});

test("the start of the app shows the choice of the setup in the app language", async () => {
  const card = (opened) => findAll(opened.main, (n) => (n.className || "").includes("choice-card"))[0];
  const de = card(await openPage({ backend: fakeBackend() }));
  const french = card(await openPage({ language: "fr", backend: fakeBackend() }));
  const english = card(await openPage({ language: "en", backend: fakeBackend({ wahl: { ...CHOICE, anrede: "du", rav: false, gewaehlt: false } }) }));

  assert.equal(de.getAttribute("aria-label"), "Wahl aus der Einrichtung");
  assert.deepEqual(texts(de, "p"), ["Gesucht wird: eine Stelle · Anrede: Sie · RAV: ja Ändern",
    "Gewählt in der Einrichtung. Eine Änderung passt die Texte und die Suche an."]);
  assert.equal(french.getAttribute("aria-label"), "Choix de la configuration");
  assert.deepEqual(texts(french, "p"), [fr("Recherche~: un poste · Vouvoiement · ORP~: oui Modifier"),
    "Choisi dans la configuration. Une modification adapte les textes et la recherche."]);
  assert.deepEqual(texts(english, "p"), ["Searching for: a job · Informal address · RAV: no Change",
    "Taken from the search profile, not chosen in the setup yet. A change adapts the texts and the search."]);
});

test("the start says in the app language when the page holds answers for the other track", async () => {
  const stand = { track: "apprenticeship", data: {}, step: 0 };
  const suggestion = async (language) => {
    const opened = await openPage({ language, backend: fakeBackend({ stand }) });
    return findAll(opened.main, (n) => n.className === "suggestion")[0].textContent;
  };

  assert.equal(await suggestion(null), "Die Angaben auf dieser Seite sind für eine Lehrstelle erfasst. Für eine Stelle weiterfahren");
  assert.equal(await suggestion("fr"), "Les informations de cette page sont saisies pour une place d'apprentissage. Continuer pour un poste");
  assert.equal(await suggestion("en"), "The details on this page are entered for an apprenticeship. Continue for a job");
});

test("a step says its note, its entries and the buttons around it in the app language", async () => {
  const stand = { track: "job", data: { work: [{ position: "Entwicklerin" }] }, step: 0 };
  const shown = async (language) => {
    const main = (await openPage({ language, backend: fakeBackend({ stand }) })).at(2);
    return {
      note: texts(main, "p").find((t) => t.includes("*")),
      legend: texts(main, "legend").find((t) => /1$/.test(t)),
      buttons: buttons(main).filter((t) => /Station|Entrée|Entry|Zurück|Retour|Back|Weiter|Continuer|Next/.test(t)),
    };
  };

  assert.deepEqual(await shown(null), { note: "Felder mit * müssen ausgefüllt sein.", legend: "Station 1",
    buttons: ["Station 1 entfernen", "+ Station hinzufügen", "Zurück: Person und Kontakt", "Weiter: Können"] });
  assert.deepEqual(await shown("fr"), { note: "Les champs marqués d'un * sont obligatoires.", legend: "Entrée 1",
    buttons: ["Retirer Entrée 1", "+ Ajouter Entrée", fr("Retour~: Personne et contact"), fr("Continuer~: Compétences")] });
  assert.deepEqual(await shown("en"), { note: "Fields marked * are required.", legend: "Entry 1",
    buttons: ["Remove Entry 1", "+ Add Entry", "Back: Person and contact", "Next: Skills"] });
});

test("the lines the form does not know are named in the app language, their file and heading kept", async () => {
  const shown = async (language) => {
    const main = (await openPage({ language, backend: fakeBackend({ grundlagen: OTHER_LINES }) })).at(4);
    const details = findAll(main, (n) => n.className === "other-lines")[0];
    return { summary: texts(details, "summary")[0], texts: texts(details, "p"), link: texts(details, "a")[0] };
  };

  assert.deepEqual(await shown(null), {
    summary: "Eine weitere Zeile aus „Suchprofil“",
    texts: ["Diese Zeilen kennt das Formular nicht. Beim Speichern bleiben sie, wie sie sind.", "Suchprofil, Region", "Suchprofil unter „Inhalte als Text“ ändern"],
    link: "Suchprofil unter „Inhalte als Text“ ändern",
  });
  const french = await shown("fr");
  assert.equal(french.summary, fr("Une autre ligne de «~Profil de recherche~»"));
  assert.equal(french.texts[1], "Profil de recherche, Region", "the heading is the profile's own and stays German");
  assert.equal(french.link, fr("Modifier Profil de recherche sous «~Contenus en texte~»"));
  assert.equal((await shown("en")).summary, "One more line from “Search profile”");
});

test("the last step of the app and its result speak the app language", async () => {
  const result = { geschrieben: ["cv.yaml"], unvollstaendig: false, behalten: ["Data Engineer"], unveraendert: [],
    nicht_ersetzt: ["suchprofil.md"], hinweis: "" };
  const shown = async (language) => {
    const opened = await openPage({ language, backend: fakeBackend({ result }) });
    const main = opened.at(6);
    const before = { heading: texts(main, "h2")[0], intro: texts(main, "p")[0], buttons: buttons(main) };
    await opened.eval("takeOver(null)");
    await settle();
    return { ...before, done: findAll(main, (n) => n.id === "take-over-done")[0].textContent };
  };

  const de = await shown(null);
  assert.equal(de.heading, "Übernehmen");
  assert.equal(de.intro, "Prüfen Sie die Übersicht. Mit «Angaben übernehmen» erstellt die App daraus Ihren Lebenslauf, Ihr Suchprofil und Ihren Schreibstil.");
  assert.ok(de.buttons.includes("Angaben übernehmen") && de.buttons.includes("Eingaben verwerfen"), de.buttons.join(" | "));
  assert.equal(de.done, "Ihre Angaben sind übernommen. Aus Ihrer bisherigen Suche bleibt dabei: Data Engineer. Entfernen können Sie das unter „Suche“. Unverändert geblieben: suchprofil.md. Zu den Bewerbungen");

  const french = await shown("fr");
  assert.equal(french.heading, "Appliquer");
  assert.ok(french.buttons.includes("Appliquer les informations"), french.buttons.join(" | "));
  assert.ok(french.buttons.includes("Abandonner les saisies"), french.buttons.join(" | "));
  assert.equal(french.done, fr("Vos informations sont appliquées. De votre recherche existante, il reste~: Data Engineer. Vous pouvez le retirer sous «~Recherche~». Inchangé~: suchprofil.md. Vers les candidatures"));
  const english = await shown("en");
  assert.ok(english.buttons.includes("Apply details"), english.buttons.join(" | "));
  assert.equal(english.done, "Your details are applied. From your existing search this stays: Data Engineer. You can remove it under “Search”. Unchanged: suchprofil.md. To the applications");
});

test("the file for sharing stays German on its start, its steps and its last step", async () => {
  const opened = await openPage();
  assert.equal(typeof opened.page.Texte, "undefined");
  assert.equal(texts(opened.main, "h2")[0], "Worum geht es?");
  assert.equal(texts(opened.main, "p")[0], "Hier erfassen Sie Schritt für Schritt alles, was der Bewerbungsbegleiter braucht: Lebenslauf, Suche, Stärken und Ton der Anschreiben. Am Schluss speichern Sie eine Datei.");
  assert.deepEqual(texts(opened.main, "strong"), ["Ich suche eine Stelle", "Ich suche eine Lehrstelle"]);
  assert.ok(texts(opened.main, "p").includes("Sie haben schon einen Lebenslauf, Zeugnisse oder frühere Anschreiben? Dann müssen Sie nichts abtippen: Im Schritt „Unterlagen“ laden Sie sie hoch. Die App übernimmt daraus Angaben, Belege und Ihre eigenen Formulierungen und fragt nur nach, was fehlt."));
  opened.eval('update({ ...state, track: "apprenticeship" })');
  const last = opened.at(7);
  assert.deepEqual(stepLabels(opened.nav), ["Start", "Unterlagen", "Du und deine Kontakte", "Schule und Schnuppern", "Was du kannst", "Was du suchst", "Wie du schreibst", "Speichern"]);
  assert.equal(stepMetas(opened.nav)[0], "Stelle oder Lehrstelle");
  assert.equal(texts(last, "h2")[0], "Prüfen und speichern");
  assert.ok(buttons(last).includes("Datei speichern") && buttons(last).includes("Alles löschen"));
  assert.ok(texts(last, "p").includes("So geht es weiter: Schick die Datei an die Person, die dich begleitet, oder öffne sie später in der App. Mit „Datei laden“ auf der ersten Seite kannst du jederzeit weiterarbeiten."));
});
