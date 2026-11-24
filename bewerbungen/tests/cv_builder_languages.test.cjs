// Lebenslauf erstellen, its preview, the documents step and the cuts in French and English (#428, G10,
// docs/design/sprachen.md): what lebenslauf-erstellen(-logik).js, lebenslauf-vorschau(-logik).js, unterlagen-wahl.js,
// unterlagen-ergebnis.js, kuerzen-logik.js and kuerzen.js say at run time comes in the app language with the catalog
// in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages. Data (stations, file names, names of a version,
// messages of the server) stays as it is; German stays as it was. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const L = require("../seiten/lebenslauf-erstellen-logik.js");
const V = require("../seiten/lebenslauf-vorschau-logik.js");
const W = require("../seiten/unterlagen-wahl.js");
const R = require("../seiten/unterlagen-ergebnis.js");
const K = require("../seiten/kuerzen-logik.js");

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

// ---------- lebenslauf-erstellen-logik.js ----------

const ANSWER = {
  stand: "abc",
  abschnitte: [{ abschnitt: "work", titel: "Berufserfahrung", stationen: [
    { index: 0, titel: "Planerin", zusatz: "Muster AG", zeit: "2015 – 2018", gewaehlt: true }] }],
  berufsbezeichnung: "Planerin", kurzprofil: "Plant gern.", design: "zweispaltig", bezeichnung: "Planung, Muster AG",
  aussehen: { foto: true, zeichen: "passend", akzent: "passend" },
  aussehen_angebot: { foto_vorhanden: true, initialen: "EB", logo: false },
};

test("the two designs of a CV are named and described in the app language", async () => {
  const shown = await inAll(() => L.DESIGNS.map(design => [design.id, design.name, design.text]));
  assert.deepEqual(shown.de, [["zweispaltig", "Zweispaltig", "Foto und Kontakt im Kopf, zwei Spalten."],
    ["einspaltig", "Einspaltig", "Schlicht, alles untereinander."]]);
  assert.deepEqual(shown.fr, [["zweispaltig", "Deux colonnes", "Photo et coordonnées en en-tête, deux colonnes."],
    ["einspaltig", "Une colonne", "Sobre, tout à la suite."]]);
  assert.deepEqual(shown.en, [["zweispaltig", "Two columns", "Photo and contact details in the header, two columns."],
    ["einspaltig", "One column", "Plain, everything one below the other."]]);
});

test("refusals of the panel come in the app language", async () => {
  const message = change => { try { change(); return ""; } catch (error) { return error.message; } };
  const shown = await inAll(() => [
    message(() => L.choose(L.start(ANSWER), "dossier-siegel")),
    message(() => L.setLook(L.start(ANSWER), { zeichen: "unbekannt" })),
    message(() => L.setLook(L.start(ANSWER), { zeichen: "logo" })),
    message(() => L.setLook(L.start(ANSWER), { akzent: "#000000" })),
    message(() => L.setLook(L.start(ANSWER), { foto: "ja" })),
  ]);
  assert.deepEqual(shown.de, ["Bitte Zweispaltig oder Einspaltig wählen.", "Dieses Zeichen gibt es nicht.",
    "Für dieses Zeichen fehlt noch etwas, etwa ein Logo.", "Diese Farbe steht nicht zur Wahl.", "Bitte mit oder ohne Foto wählen."]);
  assert.deepEqual(shown.fr, ["Merci de choisir Deux colonnes ou Une colonne.", "Cet emblème n'existe pas.",
    "Il manque encore quelque chose pour cet emblème, par exemple un logo.", "Cette couleur n'est pas proposée.",
    "Merci de choisir avec ou sans photo."]);
  assert.deepEqual(shown.en, ["Please choose Two columns or One column.", "This mark does not exist.",
    "Something is still missing for this mark, such as a logo.", "This colour is not available.",
    "Please choose with or without photo."]);
});

test("no station chosen is refused in the words the page ties to the stations", async () => {
  const none = { ...ANSWER, abschnitte: [{ ...ANSWER.abschnitte[0], stationen: [{ ...ANSWER.abschnitte[0].stationen[0], gewaehlt: false }] }] };
  const shown = await inAll(() => {
    try {
      L.request(L.start(none), {});
      return null;
    } catch (error) {
      return [error.message, error.message === L.NOTHING_CHOSEN];
    }
  });
  assert.deepEqual(shown, { de: ["Bitte mindestens eine Station wählen.", true],
    fr: ["Merci de choisir au moins une entrée.", true], en: ["Please choose at least one entry.", true] });
});

test("the announcements of the AI count one recommendation in the singular and keep the server's cost", async () => {
  const recommendation = { was: "«Planerin, Muster AG»: omettre" };
  const shown = await inAll(() => [L.suggestedText(1), L.suggestedText(2, "Cost."), L.suggestedText(0),
    L.recommendationText(recommendation, true), L.recommendationText(recommendation, false)]);
  assert.deepEqual(shown.de, ["Vorschlag der KI angewendet: 1 Empfehlung.", "Vorschlag der KI angewendet: 2 Empfehlungen. Cost.",
    "Die KI schlägt für diese Stelle nichts anderes vor.", "Wieder angewendet: «Planerin, Muster AG»: omettre.",
    "Zurückgenommen: «Planerin, Muster AG»: omettre."]);
  assert.deepEqual(shown.fr, [fr("Proposition de l'IA appliquée~: 1 recommandation."),
    fr("Proposition de l'IA appliquée~: 2 recommandations. Cost."), "L'IA ne propose rien d'autre pour ce poste.",
    fr("Appliquée à nouveau~: «Planerin, Muster AG»: omettre."), fr("Retirée~: «Planerin, Muster AG»: omettre.")]);
  assert.deepEqual(shown.en, ["AI proposal applied: 1 recommendation.", "AI proposal applied: 2 recommendations. Cost.",
    "The AI suggests nothing different for this job.", "Applied again: «Planerin, Muster AG»: omettre.",
    "Undone: «Planerin, Muster AG»: omettre."]);
});

test("saving names the version as the person called it, in the app language around it", async () => {
  const shown = await inAll(() => [L.savedText({ variante: { beschreibung: "Planung, Muster AG" }, gebaut: true }),
    L.savedText({ variante: { id: "muster-ag" }, gebaut: false }), L.savedText({ hinweis: "Vom Server." })]);
  assert.deepEqual(shown.de, ["Gespeichert als «Planung, Muster AG» und als PDF erstellt. Er gilt jetzt für diese Bewerbung.",
    "Gespeichert als «muster-ag». Er gilt jetzt für diese Bewerbung.", "Vom Server."]);
  assert.deepEqual(shown.fr, [fr("Enregistré sous «~Planung, Muster AG~» et créé en PDF. Il s'applique désormais à cette candidature."),
    fr("Enregistré sous «~muster-ag~». Il s'applique désormais à cette candidature."), "Vom Server."]);
  assert.deepEqual(shown.en, ["Saved as “Planung, Muster AG” and created as PDF. It now applies to this application.",
    "Saved as “muster-ag”. It now applies to this application.", "Vom Server."]);
});

test("the line beside «Farbe und Zeichen ändern» names mark and colour in the app language", async () => {
  // As the page's `word`: keys of texte.js become words, a mark's own name stays (lebenslauf-erstellen.js).
  const say = key => (key.startsWith("lebenslauf.") ? texte.text(key, "stelle-sie") : key);
  const shown = await inAll(() => [L.lookParts(L.start(ANSWER), say),
    L.lookParts(L.setLook(L.start(ANSWER), { zeichen: "ring" }), say)[0]]);
  assert.deepEqual(shown.de, [["Ohne Zeichen", "Farbe: passend zum Design"], "Zeichen: Ring"]);
  assert.deepEqual(shown.fr, [["Sans emblème", fr("Couleur~: assortie au design")], fr("Emblème~: Ring")]);
  assert.deepEqual(shown.en, [["No mark", "Colour: matching the design"], "Mark: Ring"]);
});

test("the text sets of the panel say tu in French where the set says du", async () => {
  const shown = await inLanguage("fr", () => [texte.text("lebenslauf.foto-fehlt", "stelle-du"),
    texte.text("lebenslauf.vorschau-geaendert", "stelle-du"), texte.text("lebenslauf.ki-bereit", "lehrstelle-du"),
    texte.text("lebenslauf.zeichen-logo", "stelle-sie")]);
  assert.deepEqual(shown, [fr("Pas encore de photo. Tu ajoutes des photos sous «~CV et fichiers~»."),
    fr("Mes informations ont changé entre-temps. Rouvre «~Créer le CV~» pour que l'aperçu les montre."),
    fr("L'IA peut proposer pour cette place d'apprentissage des entrées, un ordre et un profil en bref. L'enregistrement se fait seulement avec «~Utiliser ce CV~»."),
    "Votre logo"]);
  const english = await inLanguage("en", () => texte.text("lebenslauf.ki-holen", "stelle-du"));
  assert.equal(english, "Get proposals");
});

test("the AI's proposals, the photo lines and the buttons of the panel read as the review settled them", async () => {
  const sets = ["lebenslauf.ki-aus", "lebenslauf.ki-ohne-inserat", "lebenslauf.ki-laeuft", "lebenslauf.ki-nochmals",
    "lebenslauf.foto-einspaltig", "lebenslauf.foto-fehlt"];
  const shown = await inAll(() => sets.map(key => texte.text(key, "stelle-sie")));
  assert.deepEqual(shown.fr.slice(0, 1).concat(shown.fr.slice(3, 5)), [
    "Avec l'IA, l'app propose pour ce poste des entrées, un ordre et un profil en bref.", "Proposer à nouveau",
    "La mise en page Une colonne n'affiche pas de photo."]);
  assert.deepEqual(shown.en.slice(1), ["The job ad text is still missing for AI proposals.", "The AI is making proposals…",
    "Suggest again", "The one-column layout shows no photo.", "No photo yet. Photos are added under “CV and files”."]);
});

test("the cuts say in French what the app is doing while it builds", async () => {
  const shown = await inLanguage("fr", () => ["Wird gekürzt und neu erstellt …", "Wird zurückgeholt und neu erstellt …",
    "Drei Seiten erlaubt, wird neu erstellt …"].map(text => texte.t(text)));
  assert.deepEqual(shown, ["Le CV est raccourci et recréé…", "Le CV est rétabli et recréé…",
    "Trois pages autorisées, le CV est recréé…"]);
});

// ---------- lebenslauf-vorschau-logik.js ----------

test("the preview counts its pages and says what happened in the app language", async () => {
  const failure = (message, status, aktion) => Object.assign(new Error(message), { status, daten: aktion ? { aktion } : undefined });
  const say = key => texte.text(key, "stelle-sie");
  const shown = await inAll(() => [V.title(1), V.title(3), V.pageAlt(2, 3), V.announcement({ failed: "x" }, { pages: 1 }),
    V.announcement({ pages: 1 }, { pages: 2 }), V.ofDraft({ empty: true }).text, V.ofDraft({ reason: "Vom Server." }).text,
    V.problem(failure("Schlüssel fehlt", 400), say).text, V.problem(failure("", 500), say).text,
    V.problem(failure("Feld x", 400, V.CHECK_DATA), say), V.NOT_SHOWN]);
  assert.deepEqual(shown.de, [["Vorschau", "1 Seite"], ["Vorschau", "3 Seiten"], "Lebenslauf, Seite 2 von 3",
    "Die Vorschau ist wieder da, 1 Seite.", "Die Vorschau hat jetzt 2 Seiten.",
    "Noch keine Station angehakt. Die Vorschau erscheint, sobald mindestens eine angehakt ist.", "Vom Server.",
    "Die Vorschau lässt sich nicht erstellen. Schlüssel fehlt",
    "Die Vorschau lässt sich gerade nicht erstellen: Die App antwortet nicht. Bitte nochmals ändern oder später versuchen.",
    { text: "Die Vorschau lässt sich nicht erstellen: In Meine Angaben steht etwas, das die App nicht lesen kann.", link: true, details: "Feld x" },
    "Die Vorschau lässt sich gerade nicht anzeigen. Bitte nochmals ändern oder die Seite neu laden."]);
  assert.deepEqual(shown.fr, [["Aperçu", "1 page"], ["Aperçu", "3 pages"], "CV, page 2 sur 3",
    "L'aperçu est de retour, 1 page.", "L'aperçu compte maintenant 2 pages.",
    "Aucune entrée cochée pour l'instant. L'aperçu apparaît dès qu'au moins une est cochée.", "Vom Server.",
    "L'aperçu ne peut pas être créé. Schlüssel fehlt",
    fr("L'aperçu ne peut pas être créé pour l'instant~: l'app ne répond pas. Merci de modifier à nouveau ou de réessayer plus tard."),
    { text: fr("L'aperçu ne peut pas être créé~: Mes informations contiennent quelque chose que l'app ne peut pas lire."), link: true, details: "Feld x" },
    "L'aperçu ne peut pas s'afficher pour l'instant. Merci de modifier à nouveau ou de recharger la page."]);
  assert.deepEqual(shown.en.slice(0, 5), [["Preview", "1 page"], ["Preview", "3 pages"], "CV, page 2 of 3",
    "The preview is back, 1 page.", "The preview now has 2 pages."]);
  assert.equal(shown.en[7], "The preview cannot be created. Schlüssel fehlt");
});

// ---------- unterlagen-wahl.js and unterlagen-ergebnis.js ----------

test("the tiles name each document, its pages and how it was set, and where to adapt it", async () => {
  const pdfs = { dossier: "d.pdf", anschreiben: "a.pdf", lebenslauf: "l.pdf" };
  const notes = { dossier: { seiten: 4, ausgleich: { letter: "tightest", cv: "slightly-tighter" } },
    lebenslauf: { seiten: 1, ausgleich: { cv: "wider" } } };
  const shown = await inAll(() => R.tiles(pdfs, "dossier", { notes }).map(tile => [tile.name, tile.alt, tile.open,
    tile.adapt.text, tile.note]));
  assert.deepEqual(shown.de, [
    ["Dossier", "Dossier, Seite 1", "Als PDF öffnen", "Dossier gestalten", ["4 Seiten", "Anschreiben so eng wie möglich", "Lebenslauf etwas enger gesetzt"]],
    ["Anschreiben", "Anschreiben, Seite 1", "Als PDF öffnen", "Anschreiben ändern", []],
    ["Lebenslauf", "Lebenslauf, Seite 1", "Als PDF öffnen", "Für diese Stelle anpassen", ["1 Seite", "etwas grosszügiger gesetzt"]]]);
  assert.deepEqual(shown.fr, [
    ["Dossier", "Dossier, page 1", "Ouvrir en PDF", "Concevoir le dossier",
      ["4 pages", fr("Lettre de motivation~: mise en page la plus serrée possible"), fr("CV~: mise en page un peu plus serrée")]],
    ["Lettre de motivation", "Lettre de motivation, page 1", "Ouvrir en PDF", "Modifier la lettre", []],
    ["CV", "CV, page 1", "Ouvrir en PDF", "Adapter pour ce poste", ["1 page", "mise en page un peu plus aérée"]]]);
  assert.deepEqual(shown.en[2], ["CV", "CV, page 1", "Open as PDF", "Adapt for this job", ["1 page", "set slightly more loosely"]]);
  assert.deepEqual(shown.en[0][4], ["4 pages", "Cover letter set as tightly as possible", "CV set slightly tighter"]);
  const own = await inLanguage("en", () => R.tiles({ lebenslauf: "l.pdf" }, "einzeln", { ownCv: true })[0].adapt.text);
  assert.equal(own, "Change in CV and files");
});

test("the check is counted and announced in the app language", async () => {
  const findings = [{ stufe: "fehler" }, { stufe: "hinweis" }, { stufe: "hinweis" }, { stufe: "ok" }];
  const shown = await inAll(() => [R.announcement(findings), R.announcement([]), R.findingGroups(findings).okLabel,
    R.findingGroups([{ stufe: "ok" }, { stufe: "ok" }]).okLabel, R.nextClarify(1), R.nextClarify(3), R.STEP_TITLE,
    R.NEXT_CREATE]);
  assert.deepEqual(shown.de, ["Geprüft: 1 Fehler, 2 Hinweise, 1 Prüfung in Ordnung.", "Geprüft.", "1 Prüfung in Ordnung",
    "2 Prüfungen in Ordnung", "Die Prüfung hat einen Fehler gefunden. Er steht unter «Unterlagen erstellen und prüfen».",
    "Die Prüfung hat 3 Fehler gefunden. Sie stehen unter «Unterlagen erstellen und prüfen».", "Unterlagen erstellen und prüfen",
    "Die App erstellt Lebenslauf und Anschreiben als PDF und prüft sie gleich. Danach stehen sie unter «Unterlagen erstellen und prüfen» zum Ansehen bereit."]);
  assert.deepEqual(shown.fr, [fr("Vérifié~: 1 erreur, 2 remarques, 1 vérification réussie."), "Vérifié.",
    "1 vérification réussie", "2 vérifications réussies",
    fr("La vérification a trouvé une erreur. Elle figure sous «~Créer et vérifier les documents~»."),
    fr("La vérification a trouvé 3 erreurs. Elles figurent sous «~Créer et vérifier les documents~»."),
    "Créer et vérifier les documents",
    fr("L'app crée le CV et la lettre de motivation en PDF et les vérifie aussitôt. Ensuite, ils sont prêts à être consultés sous «~Créer et vérifier les documents~».")]);
  assert.deepEqual(shown.en.slice(0, 4), ["Checked: 1 error, 2 remarks, 1 check passed.", "Checked.", "1 check passed",
    "2 checks passed"]);
  assert.equal(shown.en[5], "The check found 3 errors. They are listed under “Create and check documents”.");
});

test("the short lines name attachments, form and design in the app language, file names stay", async () => {
  const shown = await inAll(() => [R.attachmentsLine([], null, []), R.attachmentsLine(["z/a.pdf"], [], []),
    R.attachmentsLine(["z/a.pdf"], ["z/Kurs.pdf"], []), R.attachmentsLine(["z/a.pdf"], null, ["z/Kurs.pdf"]),
    R.designLine({}), R.designLine({ dossier_design: "raster", dossier_seiten: { deckblatt: "siegel" } }),
    R.formLine({}), R.formLine({ unterlagen: "dossier", dossier_design: "register" }),
    R.textsState({ gruss: "Hallo", dank: "Danke" }), R.textsState({ gruss: "Hallo" }), R.textsState({ dank: "Danke" }),
    R.textsState({})]);
  assert.deepEqual(shown.de, ["Beilagen: noch keine Zertifikate hochgeladen.", "Beilagen: keine gewählt.", "Beilagen: Kurs.pdf",
    "Beilagen: Kurs.pdf (Vorschlag, noch nicht gespeichert)", "Design Siegel", "Design pro Seite",
    "Form: Anschreiben und Lebenslauf", "Form: Dossier, Register", "Begrüssung und Dank geschrieben",
    "Begrüssung geschrieben, ohne Dank", "Dank geschrieben, ohne Begrüssung", "Ohne Begrüssung und Dank"]);
  assert.deepEqual(shown.fr, [fr("Annexes~: aucun certificat téléversé pour l'instant."), fr("Annexes~: aucune choisie."),
    fr("Annexes~: Kurs.pdf"), fr("Annexes~: Kurs.pdf (proposition, pas encore enregistrée)"), "Design Sceau",
    "Design par page", fr("Format~: lettre de motivation et CV"), fr("Format~: dossier, Registre"),
    "Accueil et remerciements rédigés", "Accueil rédigé, sans remerciements", "Remerciements rédigés, sans accueil",
    "Sans accueil ni remerciements"]);
  assert.deepEqual(shown.en, ["Attachments: no certificates uploaded yet.", "Attachments: none chosen.", "Attachments: Kurs.pdf",
    "Attachments: Kurs.pdf (suggestion, not saved yet)", "Seal design", "Design per page", "Format: cover letter and CV",
    "Format: dossier, Register", "Welcome and thanks written", "Welcome written, without thanks",
    "Thanks written, without welcome", "Without welcome and thanks"]);
});

test("the choice of the documents names them and refuses in the app language", async () => {
  const message = change => { try { change(); return ""; } catch (error) { return error.message; } };
  const shown = await inAll(() => [W.rahmen({ lebenslauf: "l", anschreiben: "a" }, "einzeln"),
    message(() => W.zuSpeichern({ id: "a" }, "mappe")), message(() => W.entwurfDesign(W.entwurf({}), "bunt")),
    message(() => W.entwurfSeite(W.entwurf({}), "rueckseite", "raster"))]);
  assert.deepEqual(shown.de, [[["lebenslauf", "Lebenslauf"], ["anschreiben", "Anschreiben"]],
    "Bitte Dossier oder Anschreiben und Lebenslauf wählen", "Bitte Siegel, Raster oder Register wählen", "Unbekannte Seite: rueckseite"]);
  assert.deepEqual(shown.fr, [[["lebenslauf", "CV"], ["anschreiben", "Lettre de motivation"]],
    "Merci de choisir Dossier ou Lettre de motivation et CV", "Merci de choisir Sceau, Trame ou Registre",
    fr("Page inconnue~: rueckseite")]);
  assert.deepEqual(shown.en[3], "Unknown page: rueckseite");
});

// ---------- kuerzen-logik.js ----------

test("the cuts are offered, done and taken back in the app language, the server's cut texts stay", async () => {
  const kuerzen = { optionen: [{ id: "stichpunkte:a", text: "2 points de «Planerin»" }], drei_seiten: true };
  const shown = await inAll(() => [K.LEGEND, K.NEXT_TITLE, K.LEFT_OUT_TITLE, K.buttons(kuerzen).map(b => b.text),
    K.leftOut({ weggelassen: [{ id: "x", text: "Vom Server" }] })[0], K.threePages({ drei_seiten: true }),
    K.doneMessage("kuerzen", { neu_erstellt: true }, true), K.doneMessage("kuerzen", { neu_erstellt: true }, false, true),
    K.doneMessage("drei-seiten", { neu_erstellt: true }, false), K.doneMessage("zurueck", { neu_erstellt: true }, false),
    K.doneMessage("kuerzen", { neu_erstellt: false, fehler: "Kein Typst." }, false)]);
  assert.deepEqual(shown.de, ["Für diese Bewerbung weglassen", "Lebenslauf kürzen", "Für diese Bewerbung weggelassen",
    ["Gekürzt neu erstellen", "Drei Seiten erlauben"], { id: "x", text: "Vom Server", button: "Zurückholen" },
    { id: "drei-seiten", text: "Drei Seiten erlaubt, nur für diese Bewerbung.", button: "Zurücknehmen" },
    "Gekürzt und neu erstellt. Der Lebenslauf ist noch zu lang; die nächste Kürzung ist angehakt.",
    "Gekürzt und neu erstellt. Der Lebenslauf ist noch zu lang; weiter kürzen lässt sich mit «Lebenslauf erstellen» oder unter «Meine Angaben».",
    "Drei Seiten erlaubt und neu erstellt.", "Zurückgeholt und neu erstellt.", "Gespeichert, aber nicht neu erstellt: Kein Typst."]);
  assert.deepEqual(shown.fr, ["Omettre pour cette candidature", "Raccourcir le CV", "Omis pour cette candidature",
    ["Recréer en version raccourcie", "Autoriser trois pages"], { id: "x", text: "Vom Server", button: "Récupérer" },
    { id: "drei-seiten", text: "Trois pages autorisées, seulement pour cette candidature.", button: "Revenir à deux pages" },
    fr("Raccourci et recréé. Le CV est encore trop long~; la coupe suivante est cochée."),
    fr("Raccourci et recréé. Le CV est encore trop long~; pour le raccourcir davantage, utiliser «~Créer le CV~» ou «~Mes informations~»."),
    "Trois pages autorisées et CV recréé.", "Récupéré et recréé.", fr("Enregistré, mais pas recréé~: Kein Typst.")]);
  assert.deepEqual(shown.en.slice(0, 4), ["Leave out for this application", "Shorten the CV", "Left out for this application",
    ["Recreate shortened", "Allow three pages"]]);
  assert.equal(shown.en[6], "Shortened and recreated. The CV is still too long; the next cut is ticked.");
  assert.equal(shown.en[5].button, "Back to two pages");
  assert.equal(shown.en[8], "Three pages allowed and CV recreated.");
});

// ---------- kuerzen.js and lebenslauf-erstellen.js on a stand-in page ----------

function element(tag = "div", attrs = {}, children = []) {
  return {
    tag, attrs, children, hidden: false, disabled: false, textContent: "", said: "", handlers: {},
    addEventListener(type, handler) { this.handlers[type] = handler; },
    fire(type) { return this.handlers[type]({ currentTarget: this, target: this }); },
    setAttribute(key, value) { this.attrs[key] = value; },
    querySelectorAll: () => [], querySelector: () => null, append(...items) { this.children.push(...items); },
    replaceChildren(...items) { this.children = items; }, focus() {},
  };
}

const textOf = node => (node && typeof node === "object" ? (node.children || []).flat().map(textOf).join("") || node.textContent : String(node ?? ""));
const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };

async function run(names, app) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  const document = { getElementById: $, addEventListener() {}, dispatchEvent() {}, documentElement: { dataset: {} } };
  const window = {
    App: { el: (tag, attrs, ...children) => element(tag, attrs || {}, children), status: (target, text) => { target.said = text; },
      textsatz: async () => "stelle-sie", ...app },
    Texte: texte, KuerzenLogik: K, LebenslaufErstellenLogik: L, Meldungen: { clearOnInput() {} },
  };
  const context = { window, document, URLSearchParams, location: { search: "?id=muster-ag" }, console,
    CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } } };
  vm.createContext(context);
  for (const name of names) vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  return { $, window };
}

test("the choice under the finding is headed and refuses nothing ticked in the app language", async () => {
  const shown = await inAll(async () => {
    const { window } = await run(["kuerzen.js"], { senden: async () => ({}) });
    const fieldset = window.Kuerzen.chooser({ drei_seiten: false, optionen: [{ id: "a", text: "Vom Server" }] },
      { entryId: "muster-ag", note: "", after: async () => {} });
    const bare = window.Kuerzen.chooser({ drei_seiten: true }, { entryId: "muster-ag", note: "", after: async () => {} });
    const actions = fieldset.children.find(child => child.attrs && child.attrs.class === "btn-row cut-choice__actions");
    await actions.children[0].attrs.onclick();
    const status = fieldset.children.at(-1);
    return [textOf(fieldset.children[0]), textOf(bare.children[0]), status.textContent];
  });
  assert.deepEqual(shown.de, ["Für diese Bewerbung weglassen", "Für diese Bewerbung",
    "Bitte mindestens eine Kürzung anhaken oder drei Seiten erlauben."]);
  assert.deepEqual(shown.fr, ["Omettre pour cette candidature", "Pour cette candidature",
    "Merci de cocher au moins une coupe ou d'autoriser trois pages."]);
  assert.deepEqual(shown.en, ["Leave out for this application", "For this application",
    "Please tick at least one cut or allow three pages."]);
});

test("a panel that cannot open says why in the app language, the server's reason as it comes", async () => {
  const shown = await inAll(async () => {
    const page = await run(["lebenslauf-erstellen.js"], { holen: async () => { throw new Error("Nicht erreichbar."); } });
    page.$("cv-erstellen").hidden = true;
    await page.$("cv-erstellen-oeffnen").fire("click");
    await settle();
    return page.$("cv-erstellen-status").said;
  });
  assert.deepEqual(shown, { de: "Lebenslauf erstellen geht gerade nicht: Nicht erreichbar.",
    fr: fr("Impossible de créer le CV pour l'instant~: Nicht erreichbar."),
    en: "Creating the CV is not possible right now: Nicht erreichbar." });
});
