// The page of one application and its steps in French and English (#426, G10, docs/design/sprachen.md): what the
// scripts of the page say at run time comes in the app language with the catalog in bewerbungen/sprachen/ as
// /uebersetzung.js hands it to the pages: the short line under each step, the lines of the check, the history and the
// note on a grade. Stored values (stage, kind of dispatch, variant names) stay as they are; German stays as it was.
// Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const texte = require("../seiten/texte.js");
const BewerbungLogik = require("../seiten/bewerbung-logik.js");
const FormularLogik = require("../seiten/formular-logik.js");
const UebersichtLogik = require("../seiten/uebersicht-logik.js");

const CATALOG = path.join(__dirname, "..", "sprachen");
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

function inLanguage(language, check) {
  texte.setzeSprache(language, catalogFor(language));
  try {
    return check();
  } finally {
    texte.setzeSprache();
  }
}

const inAll = check => ({ de: check(), fr: inLanguage("fr", check), en: inLanguage("en", check) });
const fr = text => text.replaceAll("~", NBSP);  // "~" stands for the no-break space French puts before « : ? ! ; » and inside « »
const metas = (daten, optionen) => BewerbungLogik.schritte(daten, optionen).map(s => s.meta);

const NEW_ONE = {
  bewerbung: { id: "muster-ag-planer", status: "Bewerben", unterlagen: "einzeln" },
  stellentext: "", varianten: [{ name: "Kurs" }], hat_anschreiben: false, pdfs: {},
};
const DRAFTED = {
  bewerbung: { id: "muster-ag-planer", status: "Bewerben", unterlagen: "einzeln", eingetragen_am: "2026-11-05", variante: "Kurs" },
  stellentext: "Wir suchen eine Planerin.", varianten: [{ name: "Kurs" }], hat_anschreiben: true,
  anschreiben_freigabe: { noetig: true, freigegeben: false }, pdfs: { lebenslauf: "a.pdf", anschreiben: "b.pdf" },
};
const SENT = {
  bewerbung: { id: "muster-ag-planer", status: "Beworben", unterlagen: "einzeln", beworben_am: "2026-11-10",
               versand: { datum: "2026-11-10", art: "schriftlich" } },
  stellentext: "Wir suchen eine Planerin.", varianten: [], hat_anschreiben: true, eigenes_anschreiben: true,
  pdfs: { lebenslauf: "a.pdf", anschreiben: "b.pdf" },
};

// The short line under each step

test("the line under each step of a new application comes in the app language, polite or familiar", () => {
  const shown = inAll(() => [metas(NEW_ONE), metas(NEW_ONE, { du: true })]);
  assert.deepEqual(shown.de, [["Inserat fehlt", "Variante wählen", "fehlt noch", "PDFs erstellen", "machen Sie selbst", ""],
    ["Inserat fehlt", "Variante wählen", "fehlt noch", "PDFs erstellen", "machst du selbst", ""]]);
  assert.deepEqual(shown.fr, [["annonce manquante", "choisir une variante", "manque encore", "créer les PDF", "à faire vous-même", ""],
    ["annonce manquante", "choisir une variante", "manque encore", "créer les PDF", "à faire toi-même", ""]]);
  assert.deepEqual(shown.en, [["ad missing", "choose a variant", "still missing", "create the PDFs", "you do it yourself", ""],
    ["ad missing", "choose a variant", "still missing", "create the PDFs", "you do it yourself", ""]]);
});

test("the line under each step names the variant and the date as they are", () => {
  const shown = inAll(() => [metas(DRAFTED), metas(DRAFTED, { befunde: [] }), metas(SENT, { rav: true })]);
  assert.deepEqual(shown.de, [["erfasst 05.11.", "Variante Kurs", "lesen und freigeben", "wird geprüft", "machen Sie selbst", ""],
    ["erfasst 05.11.", "Variante Kurs", "lesen und freigeben", "in Ordnung", "machen Sie selbst", ""],
    ["Inserat da", "ganzer Lebenslauf", "eigenes PDF", "wird geprüft", "am 10.11.2026", "Job-Room offen"]]);
  assert.deepEqual(shown.fr, [["ajoutée le 05.11.", "variante Kurs", "à lire et valider", "vérification en cours", "à faire vous-même", ""],
    ["ajoutée le 05.11.", "variante Kurs", "à lire et valider", "en ordre", "à faire vous-même", ""],
    ["annonce présente", "CV complet", "PDF personnel", "vérification en cours", "le 10.11.2026", "Job-Room à faire"]]);
  assert.deepEqual(shown.en, [["added 05.11.", "variant Kurs", "read and approve", "being checked", "you do it yourself", ""],
    ["added 05.11.", "variant Kurs", "read and approve", "all fine", "you do it yourself", ""],
    ["ad present", "full CV", "own PDF", "being checked", "on 10.11.2026", "Job-Room to do"]]);
});

test("the line under the check counts errors, messages and notes, with one in the singular", () => {
  const error = { stufe: "fehler", text: "x" };
  const open = { stufe: "hinweis", text: "x", schluessel: "k" };
  const note = { stufe: "hinweis", text: "x" };
  const check = befunde => metas(DRAFTED, { befunde })[3];
  const shown = inAll(() => [check([error]), check([error, error]), check([open]), check([open, open]), check([note]),
    check([note, note]), check([{ stufe: "hinweis", text: "x", kuerzen: [] }])]);
  assert.deepEqual(shown.de, ["1 Fehler", "2 Fehler", "1 Meldung bestätigen", "2 Meldungen bestätigen", "1 Hinweis", "2 Hinweise",
    "Lebenslauf zu lang"]);
  assert.deepEqual(shown.fr, ["1 erreur", "2 erreurs", "1 message à confirmer", "2 messages à confirmer", "1 remarque", "2 remarques",
    "CV trop long"]);
  assert.deepEqual(shown.en, ["1 error", "2 errors", "1 message to confirm", "2 messages to confirm", "1 note", "2 notes",
    "CV too long"]);
});

test("a sent application with its Job-Room entry done says recorded", () => {
  const done = { ...SENT, bewerbung: { ...SENT.bewerbung, rav_eingetragen_am: "2026-11-11" } };
  const shown = inAll(() => metas(done, { rav: true })[5]);
  assert.deepEqual(shown, { de: "festgehalten", fr: "consignée", en: "recorded" });
});

// The lines of the check

test("the buttons of the check and the label of the longest paragraph come in the app language", () => {
  const over = { text: "Das Anschreiben ist länger als eine Seite.", stufe: "fehler", schluessel: "k", letter_cut: { lines: 3, paragraph: 1 } };
  const shown = inAll(() => {
    const zeile = BewerbungLogik.befundZeile(over);
    return [zeile.knopf, zeile.cutInLetter, BewerbungLogik.LONGEST_LABEL];
  });
  assert.deepEqual(shown.de, ["So lassen", "Im Anschreiben kürzen", "Längster Absatz"]);
  assert.deepEqual(shown.fr, ["Laisser ainsi", "Raccourcir dans la lettre", "Paragraphe le plus long"]);
  assert.deepEqual(shown.en, ["Leave as is", "Shorten in the cover letter", "Longest paragraph"]);
});

test("a confirmed page over the limit says pages and lines in the app language, one line in the singular", () => {
  const kept = cut => BewerbungLogik.befundZeile({ text: "x", stufe: "hinweis", bestaetigt: true, ...cut }).text;
  const shown = inAll(() => [kept({ letter_cut: { pages: 2, lines: 0 } }), kept({ letter_cut: { pages: 2, lines: 1 } }),
    kept({ cv_over: { pages: 4, lines: 7 } }),
    BewerbungLogik.befundZeile({ text: "Text im Rand auf Seite 2.", stufe: "hinweis", schluessel: "k", bestaetigt: true }).text]);
  assert.deepEqual(shown.de, ["Anschreiben: 2 Seiten. Bestätigt: so lassen.",
    "Anschreiben: 2 Seiten, etwa 1 Zeile zu viel. Bestätigt: so lassen.",
    "Lebenslauf: 4 Seiten, etwa 7 Zeilen zu viel. Bestätigt: so lassen.",
    "Text im Rand auf Seite 2. Bestätigt: so lassen."]);
  assert.deepEqual(shown.fr, [fr("Lettre de motivation~: 2 pages. Confirmé~: laisser ainsi."),
    fr("Lettre de motivation~: 2 pages, environ 1 ligne de trop. Confirmé~: laisser ainsi."),
    fr("CV~: 4 pages, environ 7 lignes de trop. Confirmé~: laisser ainsi."),
    fr("Text im Rand auf Seite 2. Confirmé~: laisser ainsi.")]);
  assert.deepEqual(shown.en, ["Cover letter: 2 pages. Confirmed: leave as is.",
    "Cover letter: 2 pages, about 1 line too many. Confirmed: leave as is.",
    "CV: 4 pages, about 7 lines too many. Confirmed: leave as is.",
    "Text im Rand auf Seite 2. Confirmed: leave as is."]);
});

// The history

test("the history names each date in the app language, with the kind of dispatch worded and stored German", () => {
  const b = { eingetragen_am: "2026-11-01", beworben_am: "2026-11-02", versand: { datum: "2026-11-02", art: "persönlich" },
              rav_eingetragen_am: "2026-11-03", gespraech_am: "2026-11-04", absage_am: "2026-11-05" };
  const shown = inAll(() => BewerbungLogik.verlauf(b).map(v => v.text));
  assert.deepEqual(shown.de, ["Erfasst", "Beworben", "Versand erfasst (persönlich)", "Im Job-Room eingetragen", "Gespräch", "Absage"]);
  assert.deepEqual(shown.fr, ["Ajoutée", "Envoyée", "Envoi enregistré (en personne)", "Saisie sur Job-Room",
    "Entretien", "Refus"]);
  assert.deepEqual(shown.en, ["Added", "Applied", "Sending recorded (in person)", "Entered in Job-Room", "Interview", "Rejection"]);
  assert.equal(b.versand.art, "persönlich");
});

test("a kind of dispatch the app does not know is shown as stored", () => {
  const b = { versand: { datum: "2026-11-02", art: "per Kurier" } };
  assert.deepEqual(inAll(() => BewerbungLogik.verlauf(b).map(v => v.text)),
    { de: ["Versand erfasst (per Kurier)"], fr: ["Envoi enregistré (per Kurier)"], en: ["Sending recorded (per Kurier)"] });
});

test("ending an application keeps the German stage it stores", () => {
  const shown = inAll(() => [BewerbungLogik.beenden({ status: "Gemerkt" }), BewerbungLogik.beenden({ status: "Gespräch" })]);
  assert.deepEqual(shown.fr, [{ stand: "Verworfen" }, { stand: "Zurückgezogen" }]);
});

// The note on a grade

test("the note on a new grade of the AI comes in the app language, with the grade as it is", () => {
  const shown = inAll(() => [FormularLogik.notenHinweis("4.5", 4.5), FormularLogik.notenHinweis("4.5", 5), FormularLogik.notenHinweis("", 5)]);
  assert.deepEqual(shown.de, ["Das ist auch die eingetragene Note.",
    "Bisher eingetragen: Note 4.5. Eine KI-Note ist eine Einschätzung und kann von Lauf zu Lauf abweichen. Die eingetragene Note ändert sich erst mit „Note übernehmen“.", ""]);
  assert.deepEqual(shown.fr, ["C'est aussi la note enregistrée.",
    fr("Enregistrée jusqu'ici~: note 4.5. Une note de l'IA est une estimation et peut varier d'une fois à l'autre. La note enregistrée ne change qu'avec «~Appliquer la note~»."), ""]);
  assert.deepEqual(shown.en, ["That is also the grade entered.",
    "Entered so far: grade 4.5. An AI grade is an estimate and can vary from run to run. The grade entered changes only with “Apply the grade”.", ""]);
});

// Heute and Bewerbungen take the step from the server's code, so a translated reason still leads there (#426 fact)

test("a reason in French still leads to its own step through the server's code", () => {
  const b = { id: "a", firma: "Muster AG", stelle: "Planer:in", status: "Bewerben", eingetragen_am: "2026-11-01" };
  const grund = fr("Pas de lien vers le formulaire~: l'ouvrir et saisir le lien");
  const step = (schritt, reason = grund) => inLanguage("fr", () => UebersichtLogik.naechsterSchritt(b, { grund: reason, schritt }).art);
  assert.equal(step("link"), "link");
  assert.equal(step("unterlagen"), "unterlagen");
  assert.equal(step("freigeben"), "freigeben");
  assert.equal(step(undefined, fr("Statut «~Gespräch~»")), "offen");
  const [row] = inLanguage("fr", () => UebersichtLogik.mitSchritten([b], new Map([["a", grund]]), new Map(), new Map([["a", "link"]])));
  assert.equal(row.schritt.art, "link");
});
