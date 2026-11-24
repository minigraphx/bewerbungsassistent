// The main script of the application page and its helpers in French and English (#427, G10, docs/design/sprachen.md):
// what bewerbung.js, ki.js, firma-ausschliessen.js, eigenes-anschreiben.js and dateien-ordner.js say at run time
// comes in the app language with the catalog in bewerbungen/sprachen/ as /uebersetzung.js hands it to the pages.
// Each script runs on a stand-in page. Data (firm, job, file names, the AI's own words) stays as it is; German stays
// as it was. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const texte = require("../seiten/texte.js");
const BewerbungLogik = require("../seiten/bewerbung-logik.js");
const FormularLogik = require("../seiten/formular-logik.js");
const TrefferLogik = require("../seiten/treffer-logik.js");
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

// ---------- A stand-in page ----------

function element(tag = "div", attrs = {}, children = []) {
  const handlers = {};
  return {
    tag, attrs, children, hidden: false, disabled: false, checked: false, textContent: "", value: "", dataset: {},
    files: [], said: "",
    addEventListener(type, handler) { handlers[type] = handler; },
    fire(type, event = {}) { return handlers[type]({ currentTarget: this, target: this, preventDefault() {}, ...event }); },
    setAttribute(key, value) { this.attrs[key] = value; },
    replaceChildren(...items) { this.children = items; },
    scrollIntoView() {}, focus() {}, showModal() {}, close() {}, click() {},
    classList: { toggle() {}, add() {}, remove() {} },
  };
}

const textOf = node => (node && typeof node === "object"
  ? (node.children || []).flat().map(textOf).join("") || node.textContent || "" : String(node ?? ""));
const nodes = node => (node && typeof node === "object" ? [node, ...(node.children || []).flat().flatMap(nodes)] : []);
const settle = async () => { for (let i = 0; i < 10; i += 1) await new Promise(resolve => setImmediate(resolve)); };
// A module the script calls but this test does not look at: every property a function that does nothing.
const stub = () => new Proxy({}, { get: () => () => null });

/** One script, or several in order, on a page whose elements appear when asked for. */
async function run(names, { holen = async () => ({}), senden = async () => ({}), search = "?id=muster-ag-planer",
  satz = "stelle-sie", extra = {} } = {}) {
  const elements = new Map();
  const $ = id => { if (!elements.has(id)) elements.set(id, element()); return elements.get(id); };
  const listeners = {};
  const confirms = [];
  const document = {
    title: "", getElementById: $, querySelectorAll: () => [], querySelector: () => element(),
    addEventListener(type, handler) { (listeners[type] ||= []).push(handler); },
    dispatchEvent(event) { for (const handler of listeners[event.type] || []) handler(event); },
    documentElement: { dataset: {} },
  };
  const say = (target, inhalt) => { target.said = textOf({ children: [inhalt].flat() }); };
  const window = {
    App: {
      holen, senden, el: (tag, attrs, ...children) => element(tag, attrs || {}, children),
      status: say, datum: iso => (iso ? iso.split("-").reverse().join(".") : ""), url: (pfad) => pfad,
      bestaetigen: (knopf, frage, aktion) => { confirms.push(frage); knopf.fire = () => aktion(); },
      beobachten() {}, textsatz: async () => satz, wahl: async () => ({ rav: true }), kiEinrichten: async () => {},
      alsBase64: async () => "",
    },
    Texte: texte, DotLine, FormularLogik, BewerbungLogik, TrefferLogik,
    Meldungen: { zeige: say, zeigeNeu: say, listenZeile: (doc, inhalt) => element("li", {}, [inhalt]) },
    UnterlagenWahl: stub(), UnterlagenErgebnis: stub(), UnterlagenSchritt: stub(), KuerzenLogik: stub(),
    Kuerzen: stub(), LetterEditor: stub(), FindingRow: stub(), BewerbungWieder: stub(), Einwilligung: stub(),
    LebenslaufAnpassen: { ziel: () => ({ href: null }) }, FirmenAusschluss: stub(),
    addEventListener() {}, postMessage() {}, ...extra,
  };
  const context = {
    window, document, URLSearchParams, console, FindingRow: window.FindingRow, navigator: { clipboard: {} },
    CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } },
    location: { origin: "http://127.0.0.1:1", hash: "", search }, setTimeout: () => 0, clearTimeout() {},
  };
  vm.createContext(context);
  for (const name of [names].flat()) vm.runInContext(fs.readFileSync(path.join(SEITEN, name), "utf8"), context);
  await settle();
  return { $, confirms, fire: (type, detail) => document.dispatchEvent(new context.CustomEvent(type, { detail })) };
}

// ---------- bewerbung.js ----------

const ENTRY = { id: "muster-ag-planer", firma: "Muster AG", stelle: "Planer:in", status: "Bewerben", ort: "Zürich",
  pensum: "80-100%", kontaktperson: "Erika Beispiel", eingetragen_am: "2026-11-01", portal: "jobs.ch", frist: "2026-11-30" };
const NEW_ONE = {
  bewerbung: ENTRY, stellentext: "", varianten: [], status: ["Bewerben", "Beworben"], pdfs: {}, hat_anschreiben: false,
  formular_abweichend: [], jobroom: { datum: "2026-11-01", arbeitgeber: "Muster AG", stelle: "Planer:in", rav_zuweisung: true },
};
const certificates = async pfad => {
  if (pfad === "/api/zertifikate") return { verfuegbar: [], vorschlag: [], gewaehlt: null };
  throw new Error(`unexpected ${pfad}`);
};
// The page loads its words before its main script, as bewerbung.html does.
const APPLICATION_SCRIPTS = ["bewerbung-texte.js", "bewerbung.js"];

async function applicationPage(data, options = {}) {
  return run(APPLICATION_SCRIPTS, {
    ...options,
    holen: async pfad => (pfad === "/api/bewerbung" ? structuredClone(data) : pfad === "/api/ki/status" ? null : certificates(pfad)),
  });
}

test("without an application chosen the page says so in the app language", async () => {
  const shown = await inAll(async () => (await run(APPLICATION_SCRIPTS, { search: "" })).$("status-oben").said);
  assert.deepEqual(shown, { de: "Keine Bewerbung gewählt", fr: "Aucune candidature choisie", en: "No application chosen" });
});

test("the card of the next step and its button come in the app language", async () => {
  const shown = await inAll(async () => {
    const page = await applicationPage(NEW_ONE);
    return [textOf({ children: page.$("naechster-zeile").children }), page.$("naechster-titel").textContent,
      textOf(page.$("naechster-knoepfe").children[0])];
  });
  assert.deepEqual(shown.de, ["Nächster Schritt", "Inseratstext einfügen", "Zum Textfeld"]);
  assert.deepEqual(shown.fr, ["Prochaine étape", "Coller le texte de l'annonce", "Aller au champ de texte"]);
  assert.deepEqual(shown.en, ["Next step", "Paste the ad text", "Go to the text field"]);
});

test("the facts in the side column are named in the app language, their values stay", async () => {
  const shown = await inAll(async () => {
    const page = await applicationPage(NEW_ONE);
    return page.$("fakten").children.map(textOf);
  });
  assert.deepEqual(shown.de, ["Firma", "Muster AG", "Ort", "Zürich", "Pensum", "80-100%", "Kontakt", "Erika Beispiel",
    "Gefunden", "jobs.ch, 01.11.2026", "Lebenslauf", "ganzer Lebenslauf", "Frist", "30.11.2026", "RAV", "keine Zuweisung"]);
  assert.deepEqual(shown.fr.filter((_, i) => i % 2 === 0).slice(1),
    ["Lieu", "Taux d'activité", "Contact", "Trouvé", "CV", "Échéance", "ORP"]);
  assert.deepEqual([shown.fr[11], shown.fr[15]], ["CV complet", "pas d'assignation"]);
  assert.deepEqual(shown.en.filter((_, i) => i % 2 === 0).slice(1),
    ["Location", "Workload", "Contact", "Found", "CV", "Deadline", "RAV"]);
  assert.deepEqual([shown.en[1], shown.en[11], shown.en[15]], ["Muster AG", "full CV", "no assignment"]);
});

test("the Job-Room details are named in the app language, with yes for an assignment", async () => {
  const shown = await inAll(async () => (await applicationPage(NEW_ONE)).$("jobroom").children.map(row => textOf(row.children[0]) + "=" + textOf(row.children[1].children[0])));
  assert.equal(shown.de[0], "Datum=01.11.2026");
  assert.equal(shown.de[9], "Zuweisung des RAV=Ja");
  assert.deepEqual(shown.fr.slice(0, 2), ["Date=01.11.2026", "Employeur=Muster AG"]);
  assert.equal(shown.fr[9], "Assignation de l'ORP=Oui");
  assert.deepEqual(shown.en.slice(0, 2), ["Date=01.11.2026", "Employer=Muster AG"]);
  assert.equal(shown.en[9], "RAV assignment=Yes");
});

test("an empty list of certificates leads to CV and files in the app language", async () => {
  const shown = await inAll(async () => textOf({ children: (await applicationPage(NEW_ONE)).$("zertifikate").children }));
  assert.deepEqual(shown, {
    de: "Noch keine Zertifikate hochgeladen. Das geht unter Lebenslauf und Dateien.",
    fr: "Aucun certificat téléversé pour l'instant. Cela se fait sous CV et fichiers.",
    en: "No certificates uploaded yet. You can do that under CV and files.",
  });
});

const DRAFTED = count => ({
  ...NEW_ONE, stellentext: "Wir suchen eine Planerin.", hat_anschreiben: true, varianten: [],
  anschreiben_text: { betreff: "Bewerbung", anrede: "Guten Tag", absaetze: ["Ich plane gern."], gruss: "Grüsse" },
  anschreiben_freigabe: { noetig: true, freigegeben: false }, pdfs: {},
  ki_pruefung: { am: "2026-11-05", requirements: [{ requirement: "SIA-Normen", status: "fehlt", note: "" },
    { requirement: "CAD", status: "abgedeckt" }],
  unsupported: Array.from({ length: count }, (_, i) => ({ text: `Aussage ${i + 1}`, problem: "" })) },
});

test("a draft with statements lacking evidence names one in the singular, in the form of the set", async () => {
  const card = (data, satz) => inAll(async () => (await applicationPage(data, { satz })).$("naechster-text").textContent);
  const one = await card(DRAFTED(1), "stelle-sie");
  const two = await card(DRAFTED(2), "stelle-du");
  assert.equal(one.de, "Der Entwurf ist fertig. Eine Aussage hat noch keinen Beleg in Ihren Angaben; gelb markiert.");
  assert.equal(two.de, "Der Entwurf ist fertig. 2 Aussagen haben noch keinen Beleg in deinen Angaben; gelb markiert.");
  assert.equal(one.fr, fr("Le brouillon est prêt. Une affirmation n'a pas encore de justificatif dans vos informations~; elle est surlignée en jaune."));
  assert.equal(two.fr, fr("Le brouillon est prêt. 2 affirmations n'ont pas encore de justificatif dans tes informations~; elles sont surlignées en jaune."));
  assert.equal(one.en, "The draft is ready. One statement has no evidence in your details yet; it is marked in yellow.");
  assert.equal(two.en, "The draft is ready. 2 statements have no evidence in your details yet; they are marked in yellow.");
});

test("the kept review of the AI counts requirements and statements, its own words stay", async () => {
  const shown = await inAll(async () => {
    const page = await applicationPage(DRAFTED(1));
    return [page.$("ki-pruefung-zahl").textContent, textOf(page.$("ki-pruefung-liste").children[1]),
      page.$("ki-pruefung-fuss").textContent, page.$("freigabe-status").said];
  });
  assert.deepEqual(shown.de, ["1 von 2 Anforderungen belegt, 1 Aussage ohne Beleg", "SIA-Normen: fehlt",
    "Prüfung der KI vom 05.11.2026. Eine Einschätzung, kein Urteil: Die KI kann sich irren.",
    "Noch nicht freigegeben. Erst mit der Freigabe öffnet die Erweiterung das Formular."]);
  assert.deepEqual(shown.fr, [fr("1 exigence justifiée sur 2, 1 affirmation sans justificatif"), fr("SIA-Normen~: manquante"),
    fr("Vérification de l'IA du 05.11.2026. Une estimation, pas un jugement~: l'IA peut se tromper."),
    "Pas encore validée. L'extension n'ouvre le formulaire qu'une fois la lettre validée."]);
  assert.deepEqual(shown.en, ["1 of 2 requirements supported, 1 statement without evidence", "SIA-Normen: missing",
    "AI review of 05.11.2026. An estimate, not a verdict: the AI can be wrong.",
    "Not approved yet. The extension opens the form only once the letter is approved."]);
});

test("the questions before ending, recording and replacing come in the app language", async () => {
  const shown = await inAll(async () => (await applicationPage(NEW_ONE)).confirms);
  assert.deepEqual(shown.de, ["Wirklich verwerfen? Nochmals klicken", "Wirklich zurückziehen? Nochmals klicken",
    "Wirklich erfassen? Nochmals klicken"]);
  assert.deepEqual(shown.fr, [fr("Vraiment écarter~? Cliquer encore une fois"), fr("Vraiment retirer~? Cliquer encore une fois"),
    fr("Vraiment enregistrer l'envoi~? Cliquer encore une fois")]);
  assert.deepEqual(shown.en, ["Really discard? Click again", "Really withdraw? Click again", "Really record as sent? Click again"]);
});

test("recording the dispatch names one remark in the singular and the server's remarks as they come", async () => {
  const recorded = hinweise => inAll(async () => {
    const page = await run(APPLICATION_SCRIPTS, {
      holen: async pfad => (pfad === "/api/bewerbung" ? structuredClone(NEW_ONE) : pfad === "/api/ki/status" ? null : certificates(pfad)),
      senden: async () => ({ hinweise }),
    });
    await page.$("versenden").fire();
    await settle();
    return page.$("status-oben").said;
  });
  const none = await recorded([]);
  const one = await recorded(["Notiz A"]);
  const two = await recorded(["Notiz A", "Notiz B"]);
  assert.equal(none.de, "Versand erfasst. Die verschickte Fassung bleibt gespeichert.");
  assert.equal(one.de, "Versand erfasst. Die verschickte Fassung bleibt gespeichert. Hinweise: Notiz A");
  assert.equal(two.de, "Versand erfasst. Die verschickte Fassung bleibt gespeichert. Hinweise: Notiz A · Notiz B");
  assert.equal(none.fr, "Envoi enregistré. La version envoyée reste enregistrée.");
  assert.equal(one.fr, fr("Envoi enregistré. La version envoyée reste enregistrée. Remarque~: Notiz A"));
  assert.equal(two.en, "Recorded as sent. The version sent stays saved. Remarks: Notiz A · Notiz B");
  assert.equal(one.en, "Recorded as sent. The version sent stays saved. Remark: Notiz A");
});

const SENT = {
  ...NEW_ONE, bewerbung: { ...ENTRY, status: "Beworben", beworben_am: "2026-11-02", versand: { datum: "2026-11-02", art: "elektronisch",
    dateien: { lebenslauf: "ablage/2026/cv-a.pdf", anschreiben: "ablage/2026/brief-b.pdf", dossier: "ablage/2026/dossier-c.pdf",
      zertifikate: "ablage/2026/zert-d.zip", unterlagen: "ablage/2026/alles-e.pdf", nachweise: "ablage/2026/nachweise-f.pdf",
      neuartig: "ablage/2026/g.pdf" } } },
};

test("the files of the version sent are named by their part in French and English, German keeps the stored part", async () => {
  const shown = await inAll(async () => (await applicationPage(SENT)).$("versand-info").children[2].children.flat().map(textOf));
  assert.deepEqual(shown.de, ["lebenslauf: cv-a.pdf", "anschreiben: brief-b.pdf", "dossier: dossier-c.pdf",
    "zertifikate: zert-d.zip", "unterlagen: alles-e.pdf", "nachweise: nachweise-f.pdf", "neuartig: g.pdf"]);
  assert.deepEqual(shown.fr, [fr("CV~: cv-a.pdf"), fr("Lettre de motivation~: brief-b.pdf"), fr("Dossier~: dossier-c.pdf"),
    fr("Certificats~: zert-d.zip"), fr("Documents~: alles-e.pdf"), fr("Justificatifs~: nachweise-f.pdf"), "neuartig: g.pdf"]);
  assert.deepEqual(shown.en, ["CV: cv-a.pdf", "Cover letter: brief-b.pdf", "Dossier: dossier-c.pdf",
    "Certificates: zert-d.zip", "Documents: alles-e.pdf", "Supporting documents: nachweise-f.pdf", "neuartig: g.pdf"]);
});

test("waiting for the answer speaks of the reply and of the Today page", async () => {
  const BT = require("../seiten/bewerbung-texte.js");
  const card = (art, extra = {}) => inAll(async () => BT.card(art, { t: (key, values) => texte.text(key, "stelle-sie", values), ...extra }));
  const reminded = await card("warten", { nachfragen: "09.11.2026" });
  const open = await card("warten");
  const meeting = await card("gespraech");
  assert.deepEqual(reminded.fr[1], "Sans réponse, la page Aujourd'hui vous rappellera de relancer le 09.11.2026.");
  assert.deepEqual(reminded.en, ["Wait for the reply", "Without a reply, the Today page reminds you to follow up on 09.11.2026."]);
  assert.deepEqual(open.en[1], "The reply can be entered below as soon as it comes.");
  assert.equal(meeting.fr[1], fr("Saisir la date dans les informations~; elle apparaît alors ici et sur la page Aujourd'hui."));
  const du = await inLanguage("fr", async () => BT.card("warten", { t: (key, values) => texte.text(key, "stelle-du", values),
    nachfragen: "09.11.2026" })[1]);
  assert.equal(du, "Sans réponse, la page Aujourd'hui te rappellera de relancer le 09.11.2026.");
});

test("Job-Room says signing in comes first, and sending yourself ends in recording what was sent", async () => {
  const BT = require("../seiten/bewerbung-texte.js");
  const said = (art, satz) => inAll(async () => BT.card(art, { t: (key, values) => texte.text(key, satz, values) }));
  const jobroom = await said("jobroom", "stelle-sie");
  const jobroomDu = await said("jobroom", "stelle-du");
  const versand = await said("versand", "stelle-sie");
  const later = await inAll(async () => BT.card("nachtragen", { t: () => "", beworben: "02.11.2026" }));
  assert.ok(jobroom.fr[1].includes("Vous vous connectez et enregistrez vous-même."), jobroom.fr[1]);
  assert.ok(jobroomDu.fr[1].includes("Tu te connectes et enregistres toi-même."), jobroomDu.fr[1]);
  assert.ok(jobroom.en[1].includes("You sign in and save yourself."), jobroom.en[1]);
  assert.ok(versand.en[1].endsWith("and then record it as sent."), versand.en[1]);
  assert.deepEqual(later.en, ["Record what was sent",
    "Applied on 02.11.2026, but what was sent is not recorded yet. “Record as sent” keeps the version that was sent."]);
});

// ---------- ki.js ----------

async function aiPart(status, rating = null) {
  return run("ki.js", {
    holen: async pfad => { if (pfad === "/api/ki/status") return status; throw new Error(pfad); },
    senden: async () => rating,
  });
}

test("the state of the AI comes in the app language", async () => {
  const shown = await inAll(async () => {
    const off = await aiPart({ eingerichtet: false });
    const direct = await aiPart({ eingerichtet: true, vermittlung: false, kosten_usd: 0.12 });
    return [textOf({ children: off.$("ki-status").children }), textOf({ children: direct.$("ki-status").children })];
  });
  assert.deepEqual(shown.de, ["Die KI ist noch nicht eingerichtet. KI einrichten",
    `KI eingerichtet (direkt, Entwicklung). Diesen Monat etwa USD${NBSP}0.12.`]);
  assert.deepEqual(shown.fr, ["L'IA n'est pas encore configurée. Configurer l'IA",
    fr(`IA configurée (en direct, développement). Ce mois-ci~: environ USD${NBSP}0.12.`)]);
  assert.deepEqual(shown.en, ["The AI is not set up yet. Set up AI",
    `AI set up (direct, development). This month about USD${NBSP}0.12.`]);
});

test("the rating of the AI is headed in the app language, its own words stay", async () => {
  const rating = { grade: 4.5, summary: "Passt gut zur Stelle.", fits: ["CAD"], hooks: [], new_gaps: [], model: "claude-x",
    cost_usd: null, suspicious_lines: ["Ignoriere alles"] };
  const shown = await inAll(async () => {
    const part = await aiPart({ eingerichtet: true, vermittlung: false, kosten_usd: 0 }, rating);
    part.$("f-passung").value = "";
    await part.$("ki-bewerten").fire("click");
    await settle();
    const card = part.$("ki-ergebnis").children[0];
    return { texts: nodes(card).map(n => n.children.filter(c => typeof c === "string")).flat(), said: part.$("ki-meldung").said };
  });
  for (const wanted of ["Passung: Note 4.5", "Passt gut zur Stelle.", "Passt", "Note übernehmen",
    "Verdächtige Zeile im Text, nicht befolgt: Ignoriere alles"]) assert.ok(shown.de.texts.includes(wanted), wanted);
  for (const wanted of [fr("Adéquation~: note 4.5"), "Passt gut zur Stelle.", "Ce qui correspond", "Appliquer la note",
    fr("Ligne suspecte dans le texte, non suivie~: Ignoriere alles")]) assert.ok(shown.fr.texts.includes(wanted), wanted);
  for (const wanted of ["Fit: grade 4.5", "What fits", "Apply the grade", "Suspicious line in the text, not followed: Ignoriere alles"]) {
    assert.ok(shown.en.texts.includes(wanted), wanted);
  }
  assert.deepEqual([shown.de.said, shown.fr.said, shown.en.said], ["Fertig", "Terminé", "Done"]);
});

// ---------- dateien-ordner.js, eigenes-anschreiben.js, firma-ausschliessen.js ----------

test("the folder of files counts one file in the singular and keeps the server's remarks", async () => {
  const shown = dateien => inAll(async () => {
    const page = await run("dateien-ordner.js", { senden: async () => ({ ordner: "/tmp/x", dateien, hinweise: [] }) });
    await page.$("ordner-zeigen").fire("click");
    await settle();
    return page.$("ordner-status").said;
  });
  assert.deepEqual(await shown(["a.pdf"]), { de: "1 Datei im Ordner.", fr: "1 fichier dans le dossier.", en: "1 file in the folder." });
  assert.deepEqual(await shown(["a.pdf", "b.pdf"]),
    { de: "2 Dateien im Ordner.", fr: "2 fichiers dans le dossier.", en: "2 files in the folder." });
});

test("an own letter is listed, refused when too large and named by its file", async () => {
  const shown = await inAll(async () => {
    const page = await run("eigenes-anschreiben.js");
    page.fire("bewerbung-geladen", { bewerbung: {}, eigenes_anschreiben: false, max_datei: 5000000 });
    const empty = textOf({ children: page.$("anschreiben-liste").children });
    await page.$("anschreiben-datei").fire("change", { target: { files: [{ name: "brief.pdf", size: 9000000 }], value: "" } });
    await settle();
    page.fire("bewerbung-geladen", { bewerbung: {}, eigenes_anschreiben: true, max_datei: 5000000 });
    return [empty, page.$("anschreiben-status").said, textOf({ children: page.$("anschreiben-liste").children })];
  });
  assert.deepEqual(shown.de, ["Noch nichts hochgeladen.", "brief.pdf ist zu gross, höchstens 5 MB.", "Hochgeladenes AnschreibenEntfernen"]);
  assert.deepEqual(shown.fr, ["Rien n'est encore téléversé.", "brief.pdf est trop volumineux, 5 Mo au maximum.",
    "Lettre de motivation téléverséeRetirer"]);
  assert.deepEqual(shown.en, ["Nothing uploaded yet.", "brief.pdf is too large, at most 5 MB.", "Uploaded cover letterRemove"]);
});

test("a company whose state cannot be loaded is named as it is", async () => {
  const shown = await inAll(async () => {
    const page = await run("firma-ausschliessen.js", { holen: async () => { throw new Error("Nicht erreichbar."); } });
    page.fire("bewerbung-geladen", { bewerbung: { firma: "Muster AG" } });
    await settle();
    return page.$("firma-ausschliessen-status").said;
  });
  assert.deepEqual(shown, {
    de: "Ob Muster AG in der Suche gezeigt wird, liess sich nicht laden. Nicht erreichbar.",
    fr: "Impossible de savoir si Muster AG apparaît dans la recherche. Nicht erreichbar.",
    en: "Whether Muster AG shows in the search could not be loaded. Nicht erreichbar.",
  });
});
