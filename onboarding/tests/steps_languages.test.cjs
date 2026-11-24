// Meine Angaben in French and English, the steps and checks (#432, G10, docs/design/sprachen.md): the five steps of
// steps.js, the messages of validate.js with where they stand, and the own words of dom.js speak the app language.
// German stays as it was, word for word, and so does the file for sharing, which loads no texte.js. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { findAll, loadScripts } = require("./fake_dom.cjs");
const { catalogFor, fr } = require("./catalog_for.cjs");

const TEXTE = "../../bewerbungen/seiten/texte.js";
const form = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "form.json"), "utf8"));
const SCRIPTS = ["words.js", "validate.js", "model.js", "steps.js", "dom.js"];
const app = loadScripts([TEXTE, ...SCRIPTS]);
const standalone = loadScripts(SCRIPTS);
const field = (sectionId, id) => form.sections.find((s) => s.id === sectionId).fields.find((f) => f.id === id);
const byTag = (node, tag) => findAll(node, (n) => n.tagName === tag);
const texts = (node, tag) => byTag(node, tag).map((n) => n.textContent);
const labels = (node, tag) => byTag(node, tag).map((n) => n.getAttribute("aria-label")).filter(Boolean);

function inLanguage(language, check) {
  app.Texte.setzeSprache(language, catalogFor(language));
  try {
    return check(app);
  } finally {
    app.Texte.setzeSprache();
  }
}

const inAll = (check) => ({ de: check(app), fr: inLanguage("fr", check), en: inLanguage("en", check) });

function view(page, sectionId, id, value, track = "job") {
  return page.fieldView(field(sectionId, id), {
    track, value, path: `${sectionId}.${id}`, cantons: form.cantons, tagSuggestions: [], onChange() {}, onBlur() {},
  });
}

// Array.from builds the lists in this realm, so that deepEqual compares them with the literals below.
const steps = (page, track) => Array.from(page.stepGroups(page.sectionsFor(form, track), track), (g) => [g.title, g.meta]);

test("the five steps say title and line in the app language, per track", () => {
  const job = inAll((page) => steps(page, "job"));
  const apprenticeship = inAll((page) => steps(page, "apprenticeship"));

  assert.deepEqual(job.de, [
    ["Person und Kontakt", "Name, Adresse, Kontakt"], ["Werdegang", "Stationen, Lehre, Projekte, Ausbildung, Kurse"],
    ["Können", "Sprachen, Kenntnisse, Stärken"], ["Was Sie suchen", "Stellen, Region, Rahmen"],
    ["Wie Sie schreiben", "Kurzprofil, Lücken, Ton"]]);
  assert.deepEqual(apprenticeship.de[0], ["Du und deine Kontakte", "Name, Adresse, Kontakt"]);
  assert.deepEqual(job.fr[0], ["Personne et contact", "Nom, adresse, contact"]);
  assert.deepEqual(job.fr[3], ["Ce que vous cherchez", "Postes, région, conditions"]);
  assert.deepEqual(apprenticeship.fr[3], ["Ce que tu cherches", "Métiers, région, début de l'apprentissage"]);
  assert.deepEqual(apprenticeship.fr[4][0], "Ta façon d'écrire");
  assert.deepEqual(job.en[1], ["Career", "Entries, teaching, projects, education, courses"]);
  assert.deepEqual(job.en[4], ["How you write", "Profile summary, gaps, tone"]);
});

test("a message names where it stands and what is wrong in the app language", () => {
  const error = { path: "work.0.highlights.1.tags.0", code: "format" };
  const shown = inAll((page) => ({ where: page.describe(form, "job", error), alone: page.messageText(form, "job", error) }));

  assert.equal(shown.de.where, "Berufliche Stationen, Station 1, Tätigkeiten und Erfolge, Zeile 2, Tags, Tag 1: Ungültiges Format, zum Beispiel: daten.");
  assert.equal(shown.de.alone, "Ungültiges Format, zum Beispiel: daten.");
  assert.equal(shown.fr.where, fr("Parcours professionnel, Entrée 1, Activités et réussites, ligne 2, Tags, tag 1~: Format non valable, par exemple~: données."));
  assert.equal(shown.en.where, "Work experience, Entry 1, Tasks and achievements, line 2, Tags, tag 1: Invalid format, for example: data.");
});

test("every code of validate.js has its message in French and English, with its values", () => {
  const codes = ["required", "type", "max", "maxItems", "format", "option", "notBefore", "newline", "unknown", "bundle", "track"];
  const say = (page, code) => page.messageText(form, "job", { path: "person.email", code });
  const shown = inAll((page) => codes.map((code) => say(page, code)));

  assert.equal(shown.de[0], "Bitte ausfüllen.");
  assert.equal(shown.de[2], "Zu lang (höchstens 200 Zeichen).");
  assert.equal(shown.de[4], "Ungültiges Format, zum Beispiel: vorname.nachname@example.ch.");
  for (const language of ["fr", "en"]) {
    shown[language].forEach((text, index) => assert.notEqual(text, shown.de[index], `${language} ${codes[index]}`));
  }
  assert.equal(shown.fr[2], "Trop long (200 caractères au maximum).");
  assert.equal(shown.en[4], "Invalid format, for example: firstname.lastname@example.ch.");
  assert.equal(shown.en[0], "Please fill this in.");
  assert.equal(shown.en[6], "Is before the start date.");
});

test("the wording the UI/UX review ruled for the steps holds in French and English", () => {
  const say = (language, german, values) => inLanguage(language, (page) => page.Texte.t(german, values));
  const kept = "Aus deiner bisherigen Suche bleibt dabei: {namen}. Entfernen kannst du das unter „Suche“.";
  const existing = "Sie haben schon einen Lebenslauf, Zeugnisse oder frühere Anschreiben? Dann müssen Sie nichts abtippen: "
    + "Im Schritt „Unterlagen“ laden Sie sie hoch. Die App übernimmt daraus Angaben, Belege und Ihre eigenen Formulierungen "
    + "und fragt nur nach, was fehlt.";

  assert.equal(say("fr", kept, { namen: "Data Engineer" }), fr("De ta recherche précédente, il reste~: Data Engineer. Tu peux le retirer sous «~Recherche~»."));
  assert.equal(say("en", kept, { namen: "Data Engineer" }), "From your previous search this stays: Data Engineer. You can remove it under “Search”.");
  assert.equal(say("fr", "Hier ergänzen. Es zählt für die Suche, sobald es unter „Übernehmen“ abgeschlossen ist."),
    fr("À compléter ici. Cela compte pour la recherche dès que c'est terminé sous «~Appliquer~»."));
  assert.ok(say("en", existing).startsWith("Do you already have a CV, references or earlier cover letters? Then you do not need"));
  assert.equal(say("fr", "Angaben fehlen"), "Informations manquantes");
  assert.equal(say("en", "Angaben fehlen"), "Details missing");
});

test("a field's own message from form.json follows the app language", () => {
  const own = Object.entries(field("searchJob", "portalsOff").messages || {})[0];
  assert.ok(own, "the portals say a message in their own words (#291)");
  const [code, german] = own;
  const shown = inAll((page) => page.messageText(form, "job", { path: "searchJob.portalsOff", code }));
  assert.equal(shown.de, german);
  assert.notEqual(shown.fr, german);
  assert.notEqual(shown.en, german);
});

test("a select without its own empty label offers the choice in the app language", () => {
  const shown = inAll((page) => texts(byTag(view(page, "searchJob", "remote", ""), "select")[0], "option")[0]);
  assert.deepEqual(shown, { de: "– bitte wählen –", fr: "– choisir –", en: "– please choose –" });
});

test("a list says its placeholder, a tags field its example in the app language", () => {
  const shown = inAll((page) => ({
    list: byTag(view(page, "searchJob", "directions", []), "textarea")[0].placeholder,
    tags: byTag(view(page, "work", "tags", []), "input")[0].placeholder,
  }));
  assert.deepEqual(shown.de, { list: "Eine Angabe pro Zeile", tags: "z.B. daten, führung" });
  assert.deepEqual(shown.fr, { list: "Une information par ligne", tags: "p. ex. données, conduite" });
  assert.deepEqual(shown.en, { list: "One entry per line", tags: "e.g. data, leadership" });
});

test("a text that can get English says so in the app language, and its languages by name", () => {
  const plain = inAll((page) => {
    const button = byTag(view(page, "summary", "summary", "Erfahren."), "button")[0];
    return { text: button.textContent, label: button.getAttribute("aria-label") };
  });
  const both = inAll((page) => {
    const node = view(page, "summary", "summary", { de: "Erfahren.", en: "Experienced." });
    return { names: texts(node, "span"), labels: labels(node, "textarea"), drop: byTag(node, "button")[0].textContent };
  });

  assert.deepEqual(plain.de, { text: "+ Englisch", label: "Kurzprofil: Englisch ergänzen" });
  assert.deepEqual(plain.fr, { text: "+ anglais", label: fr("Profil en bref~: ajouter l'anglais") });
  assert.deepEqual(plain.en, { text: "+ English", label: "Profile summary: add English" });
  assert.deepEqual(both.de, { names: ["Deutsch", "Englisch"], labels: ["Kurzprofil, Deutsch", "Kurzprofil, Englisch"], drop: "Englisch entfernen" });
  assert.deepEqual(both.fr, { names: ["Allemand", "Anglais"], labels: ["Profil en bref, Allemand", "Profil en bref, Anglais"], drop: "Retirer l'anglais" });
  assert.deepEqual(both.en.drop, "Remove English");
});

test("the rows of a list name their line, their tags and their rating in the app language", () => {
  const tagged = inAll((page) => {
    const node = view(page, "work", "highlights", ["Ein Projekt geleitet"]);
    return { labels: [...labels(node, "input"), ...labels(node, "button")], add: texts(node, "button").at(-1) };
  });
  const leveled = inAll((page) => labels(view(page, "skills", "keywords", [{ text: "Tabellen", level: "4" }]), "select"));
  const bilingual = inAll((page) => labels(view(page, "interests", "interests", ["Lesen"]), "button"));

  assert.deepEqual(tagged.de, { labels: ["Tätigkeiten und Erfolge, Zeile 1", "Tags zu Zeile 1", "Zeile 1 auf Englisch ergänzen", "Zeile 1 entfernen"], add: "+ Zeile hinzufügen" });
  assert.deepEqual(tagged.fr, { labels: ["Activités et réussites, ligne 1", "Tags de la ligne 1", "Ajouter la ligne 1 en anglais", "Retirer la ligne 1"], add: "+ Ajouter une ligne" });
  assert.deepEqual(tagged.en.labels, ["Tasks and achievements, line 1", "Tags for line 1", "Add line 1 in English", "Remove line 1"]);
  assert.deepEqual(leveled, { de: ["Stufe zu Zeile 1"], fr: ["Échelon de la ligne 1"], en: ["Rating for line 1"] });
  assert.deepEqual(bilingual.fr, ["Ajouter la ligne 1 en anglais", "Retirer la ligne 1"]);
});

test("a choice offers its own wording in the app language", () => {
  const shown = inAll((page) => {
    const node = view(page, "style", "opening", "");
    return { text: texts(node, "span").at(-1), label: byTag(node, "input").at(-1).getAttribute("aria-label") };
  });
  assert.deepEqual(shown.de, { text: "Eigene Formulierung:", label: "Eigene Formulierung" });
  assert.deepEqual(shown.fr, { text: fr("Formulation personnelle~:"), label: "Formulation personnelle" });
  assert.deepEqual(shown.en, { text: "Your own wording:", label: "Your own wording" });
});

test("the file for sharing keeps every word German", () => {
  assert.equal(typeof standalone.Texte, "undefined");
  assert.deepEqual(steps(standalone, "job")[2], ["Können", "Sprachen, Kenntnisse, Stärken"]);
  assert.equal(standalone.describe(form, "job", { path: "work.0.highlights.1.tags.0", code: "format" }),
    "Berufliche Stationen, Station 1, Tätigkeiten und Erfolge, Zeile 2, Tags, Tag 1: Ungültiges Format, zum Beispiel: daten.");
  const node = view(standalone, "work", "highlights", ["Ein Projekt geleitet"]);
  assert.deepEqual(labels(node, "input"), ["Tätigkeiten und Erfolge, Zeile 1", "Tags zu Zeile 1"]);
});

test("validate.js required alone, as the other tests and tools do, keeps its German messages", () => {
  const { describe } = require("../src/validate.js");
  assert.equal(describe(form, "job", { path: "person.name", code: "required" }), "Person und Kontakt, Vor- und Nachname: Bitte ausfüllen.");
});
