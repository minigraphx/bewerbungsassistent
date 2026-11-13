// Heute and the first start (#260, A1 and A2, G55, G38): what waits today, dates and deadlines, the stand by stage,
// the pass over saved jobs and the four steps to the first application.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const L = require("../seiten/uebersicht-logik.js");
const H = require("../seiten/heute-logic.js");
const texte = require("../seiten/texte.js");

const PAGES = path.join(__dirname, "..", "seiten");
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const b = (id, status, fields = {}) => ({ id, firma: `Firma ${id}`, stelle: `Stelle ${id}`, status, eingetragen_am: "2026-11-01", ...fields });
const TODAY = "2026-11-12";

test("two or more saved jobs become one item, the pass over them (G38)", () => {
  const rows = L.mitSchritten([b("m1", "Gemerkt"), b("m2", "Gemerkt", { frist: "2026-11-20" }), b("g", "Gespräch")]);
  const due = L.stehtAn(rows, Infinity);
  assert.deepEqual(due.map(e => [e.art, e.eintraege.map(z => z.bewerbung.id)]), [["gespraech", ["g"]], ["entscheiden", ["m2", "m1"]]]);
  const single = L.stehtAn(L.mitSchritten([b("m1", "Gemerkt")]), Infinity);
  assert.deepEqual(single.map(e => e.eintraege.length), [1]);
});

test("dates and deadlines come from the register, today and later, soonest first", () => {
  const rows = L.mitSchritten([
    b("a", "Gemerkt", { frist: "2026-11-20", stelle: "Netzplaner:in", firma: "Beispiel Energie AG" }),
    b("w", "Beworben", { beworben_am: "2026-11-10", firma: "Beispiel Versicherung" }),
    b("g", "Gespräch", { gespraech_am: "2026-11-18", firma: "Muster Bank" }),
    b("old", "Bewerben", { frist: "2026-11-01" }),
    b("done", "Absage", { frist: "2026-11-15" }),
  ]);
  assert.deepEqual(H.dates(rows, TODAY), [
    { date: "2026-11-16", day: "16.11.", text: "Gespräch bei Muster Bank vorbereiten" },
    { date: "2026-11-18", day: "18.11.", text: "Gespräch bei Muster Bank" },
    { date: "2026-11-20", day: "20.11.", text: "Frist für Netzplaner:in, Beispiel Energie AG" },
    { date: "2026-11-24", day: "24.11.", text: "Nachfragen bei Beispiel Versicherung, falls keine Antwort da ist" },
  ]);
  assert.equal(H.dates(rows, TODAY, { max: 1 }).length, 1);
  assert.equal(H.dates(rows, TODAY, { interview: "Einladung" })[1].text, "Einladung bei Muster Bank");
  assert.deepEqual(H.dates([], TODAY), []);
});

test("a deadline counts until the application is sent, from today on (#269)", () => {
  const rows = L.mitSchritten([
    b("ready", "Bewerben", { frist: "2026-11-25", stelle: "Planer:in", firma: "Muster AG" }),
    b("due", "Gemerkt", { frist: TODAY, stelle: "Analyst:in", firma: "Beispiel GmbH" }),
    b("sent", "Beworben", { frist: "2026-11-14" }),
  ]);
  assert.deepEqual(H.dates(rows, TODAY).map(entry => [entry.day, entry.text]), [
    ["12.11.", "Frist für Analyst:in, Beispiel GmbH"],
    ["25.11.", "Frist für Planer:in, Muster AG"],
  ]);
});

test("the follow-up date stays while the Job-Room entry is still open (#269)", () => {
  const job = b("r", "Beworben", { beworben_am: "2026-11-05", firma: "Beispiel Logistik" });
  const rows = L.mitSchritten([job], new Map(), new Map([["r", null]]));
  assert.equal(rows[0].schritt.art, "rav");
  assert.deepEqual(H.dates(rows, TODAY), [
    { date: "2026-11-19", day: "19.11.", text: "Nachfragen bei Beispiel Logistik, falls keine Antwort da ist" },
  ]);
});

test("an interview date shows even before the stage is changed, and replaces the follow-up (#269)", () => {
  const rows = L.mitSchritten([b("i", "Beworben", { beworben_am: "2026-11-05", gespraech_am: "2026-11-16", firma: "Muster Bank" })]);
  assert.deepEqual(H.dates(rows, TODAY).map(entry => entry.text), ["Gespräch bei Muster Bank vorbereiten", "Gespräch bei Muster Bank"]);
  const past = L.mitSchritten([b("p", "Beworben", { beworben_am: "2026-11-05", gespraech_am: "2026-11-10" })]);
  assert.deepEqual(H.dates(past, TODAY), [], "a past interview neither shows nor brings the follow-up back");
});

test("an interview date brings a reminder to prepare it two days ahead (#268)", () => {
  const interview = gespraech_am => L.mitSchritten([b("i", "Beworben", { beworben_am: "2026-11-02", gespraech_am, firma: "Muster Bank" })]);
  const shown = (rows, options) => H.dates(rows, TODAY, options).map(entry => [entry.day, entry.text]);
  assert.deepEqual(shown(interview("2026-11-20")), [["18.11.", "Gespräch bei Muster Bank vorbereiten"], ["20.11.", "Gespräch bei Muster Bank"]]);
  assert.deepEqual(shown(interview("2026-11-13")), [["12.11.", "Gespräch bei Muster Bank vorbereiten"], ["13.11.", "Gespräch bei Muster Bank"]],
    "an interview tomorrow is prepared today");
  assert.deepEqual(shown(interview(TODAY)), [["12.11.", "Gespräch bei Muster Bank"]], "on the day itself only the interview");
  assert.deepEqual(shown(interview("2026-11-20"), { interview: "Einladung" }).map(([, text]) => text),
    ["Einladung bei Muster Bank vorbereiten", "Einladung bei Muster Bank"]);
  const talk = L.mitSchritten([b("g", "Gespräch", { gespraech_am: "2026-11-25", firma: "Beispiel AG" })]);
  assert.deepEqual(shown(talk), [["23.11.", "Gespräch bei Beispiel AG vorbereiten"], ["25.11.", "Gespräch bei Beispiel AG"]]);
});

test("with an interview date the next step is to prepare it, no longer to wait and follow up (#268)", () => {
  const job = b("i", "Beworben", { beworben_am: "2026-11-02", gespraech_am: "2026-11-20", firma: "Muster Bank" });
  const [row] = L.mitSchritten([job]);
  assert.deepEqual(row.schritt, { art: "gespraech", frist: "2026-11-20" });
  const t = (key, values) => texte.text(key, "stelle-sie", values);
  assert.deepEqual(L.schrittText(row.schritt, 1, t), { titel: "Gespräch vorbereiten", zusatz: "20.11.2026" });
  const [first] = L.stehtAn(L.mitSchritten([b("w", "Beworben", { beworben_am: "2026-11-01" }), job]));
  assert.deepEqual([first.art, first.eintraege[0].bewerbung.id], ["gespraech", "i"], "Heute shows the interview first");
  const [withRav] = L.mitSchritten([job], new Map(), new Map([["i", null]]));
  assert.equal(withRav.schritt.art, "rav", "an open Job-Room entry still comes first, as on the application");
});

test("an interview without a date asks for it, so the app can remind in time (#268, A1)", () => {
  const [row] = L.mitSchritten([b("g", "Gespräch", { firma: "Muster Bank" })]);
  const titel = satz => L.schrittText(row.schritt, 1, (key, values) => texte.text(key, satz, values)).titel;
  assert.equal(titel("stelle-sie"), "Termin fürs Gespräch eintragen");
  assert.equal(titel("lehrstelle-du"), "Termin für die Einladung eintragen");
  assert.equal(texte.text("heute.gespraech.ohne-termin", "stelle-sie", { firma: "Muster Bank" }),
    "Muster Bank hat Sie eingeladen. Mit dem Termin erinnert die App Sie rechtzeitig an die Vorbereitung.");
  assert.equal(texte.text("heute.gespraech.ohne-termin", "stelle-du", { firma: "Muster Bank" }),
    "Muster Bank hat dich eingeladen. Mit dem Termin erinnert dich die App rechtzeitig an die Vorbereitung.");
  const page = read("uebersicht.js");
  assert.match(page, /"Termin eintragen"/);
  assert.match(page, /#termin/);
  assert.match(read("bewerbung.js"), /location\.hash === "#termin"/, "the application opens its facts at the date field");
});

test("the list is cut after the soonest dates, never before them (#269)", () => {
  const rows = L.mitSchritten(["2026-12-05", "2026-11-13", "2026-11-30", "2026-11-14", "2026-12-01", "2026-11-20"]
    .map((frist, index) => b(`f${index}`, "Gemerkt", { frist })));
  assert.deepEqual(H.dates(rows, TODAY, { max: 5 }).map(entry => entry.date),
    ["2026-11-13", "2026-11-14", "2026-11-20", "2026-11-30", "2026-12-01"]);
});

test("the stand counts each stage with a short hint", () => {
  const rows = L.mitSchritten([
    b("m1", "Gemerkt", { frist: "2026-11-16" }), b("m2", "Gemerkt", { frist: "2026-12-01" }), b("m3", "Bewerben"),
    b("w", "Beworben"), b("g", "Gespräch"), b("z", "Zusage"), b("a1", "Absage"), b("a2", "Absage"),
  ]);
  assert.deepEqual(H.stand(rows, { count: 8, last: "2026-11-10T09:00:00" }, TODAY), {
    neu: { count: 8, hint: "aus der Suche vom 10.11." },
    gemerkt: { count: 3, hint: "1 Frist in dieser Woche" },
    beworben: { count: 2, hint: "1 Gespräch" },
    abgeschlossen: { count: 3, hint: "1 Zusage, 2 Absagen" },
  });
  const empty = H.stand([], null, TODAY);
  assert.deepEqual(empty.neu, { count: 0, hint: "noch keine Suche" });
  assert.deepEqual(empty.gemerkt, { count: 0, hint: "" });
  assert.equal(H.stand(L.mitSchritten([b("g", "Gespräch"), b("h", "Gespräch")]), null, TODAY, { interview: ["Einladung", "Einladungen"] }).beworben.hint, "2 Einladungen");
});

test("the line under the title says how many things wait, in words up to twelve", () => {
  assert.deepEqual(H.waiting(0), { key: "heute.wartet.nichts", values: {} });
  assert.deepEqual(H.waiting(1), { key: "heute.wartet.eins", values: {} });
  assert.deepEqual(H.waiting(4), { key: "heute.wartet.viele", values: { anzahl: "Vier" } });
  assert.deepEqual(H.waiting(13), { key: "heute.wartet.viele", values: { anzahl: "13" } });
  assert.equal(texte.text("heute.wartet.viele", "stelle-sie", { anzahl: "Vier" }), "Vier Dinge warten auf Sie, das wichtigste zuoberst.");
  assert.equal(texte.text("heute.wartet.viele", "stelle-du", { anzahl: "Vier" }), "Vier Dinge warten auf dich, das wichtigste zuoberst.");
});

test("the pass shows the fetched ad, or why it is missing and how to get it (G37, G38)", () => {
  const job = { link: "https://www.job-room.ch/job-search/abc" };
  assert.deepEqual(H.passAd(job, "Stelle: Data Analyst\n\nWir suchen.", null), { text: "Stelle: Data Analyst\n\nWir suchen." });
  const missing = { grund: "linkedin.com ist keines der Portale, die automatisches Laden erlauben.", weg: "Das Inserat öffnen." };
  assert.deepEqual(H.passAd(job, "Stelle: Data Analyst", missing),
    { zeilen: ["Zu dieser Stelle fehlt der Inseratstext.", missing.grund, missing.weg], link: job.link });
  assert.deepEqual(H.passAd({ link: "" }, "", null), { zeilen: ["Zu dieser Stelle fehlt der Inseratstext."], link: "" });
  assert.equal(H.passAd({ link: "javascript:alert(1)" }, "", null).link, "", "only web links are offered");
});

test("the pass takes the saved jobs one after the other, the closest deadline first", () => {
  const rows = L.mitSchritten([b("m1", "Gemerkt"), b("m2", "Gemerkt", { frist: "2026-11-20" }), b("x", "Bewerben"), b("w", "Beworben")]);
  assert.deepEqual(H.passQueue(rows), ["m2", "m1"]);
  assert.equal(H.passProgress(0, 2), "1 von 2");
  assert.equal(H.passResult({ bewerben: 2, verworfen: 1, spaeter: 1 }), "Durchgang fertig: 2 zum Bewerben, 1 verworfen, 1 für später.");
  assert.equal(H.passResult({ bewerben: 0, verworfen: 0, spaeter: 3 }), "Durchgang fertig: 3 für später.");
  assert.equal(H.passResult({}), "Durchgang fertig.");
});

test("Heute is laid out as in A1: next step, Danach, dates and deadlines, the RAV hint and Ihr Stand", () => {
  const html = read("uebersicht.html");
  assert.match(html, /<title>Heute<\/title>/);
  assert.match(html, /<h1 id="steht-an-titel">Das steht heute an<\/h1>/);
  assert.match(html, /<p class="today__line" id="heute-zeile"><\/p>/);
  for (const [id, title] of [["danach", "Danach"], ["termine", "Termine und Fristen"]]) {
    assert.match(html, new RegExp(`<h2 id="${id}-titel">${title}</h2>`));
  }
  assert.match(html, /<h2 id="stand-titel" data-text="heute.stand">Ihr Stand<\/h2>/);
  const rav = html.indexOf('id="rav-hinweis"');
  assert.ok(rav > html.indexOf('id="termine-titel"') && rav < html.indexOf('id="stand-titel"'), "RAV hint under the dates");
  for (const view of ["neu", "gemerkt", "beworben", "abgeschlossen"]) assert.match(html, new RegExp(`data-stand="${view}"`));
  assert.match(html, /<dialog class="dialog pass" id="pass-dialog"/);
});

test("the first start shows four steps to the first application and what is good to know (A2)", () => {
  const html = read("uebersicht.html");
  const start = html.slice(html.indexOf('id="erststart"'), html.indexOf("</section>\n\n", html.indexOf('id="erststart"')));
  assert.match(start, /<h2 id="weg-titel" data-text="heute.weg">Ihr Weg zur ersten Bewerbung<\/h2>/);
  const steps = [...start.matchAll(/<li class="path__step"[^>]*data-step="(\w+)"/g)].map(m => m[1]);
  assert.deepEqual(steps, ["einrichtung", "angaben", "suchen", "bewerbung"]);
  assert.match(start, /href="\/angaben#feld=unterlagen"[^>]*>Lebenslauf hochladen und vorbefüllen<\/a>/);
  assert.match(start, /href="\/angaben"[^>]*>Von Hand ausfüllen<\/a>/);
  assert.match(start, /<h2 id="wissen-titel">Gut zu wissen<\/h2>/);
  assert.match(start, /Anleitung mit Bildern öffnen/);
  assert.doesNotMatch(start, /So geht es weiter/);
});

test("every text Heute speaks to the person with exists in both forms", () => {
  for (const key of ["heute.wartet.nichts", "heute.wartet.eins", "heute.wartet.viele", "heute.stand", "heute.weg",
                     "heute.durchgang.unter", "heute.start.einrichtung", "heute.start.suchen", "heute.start.bewerbung",
                     "heute.wissen.computer", "heute.wissen.entscheiden", "heute.wissen.weg", "heute.rav",
                     "heute.gespraech.termin", "heute.gespraech.ohne-termin"]) {
    assert.ok(texte.TEXTE[key], key);
  }
  const html = read("uebersicht.html");
  for (const [, key] of html.matchAll(/data-text="([^"]+)"/g)) assert.ok(texte.TEXTE[key], key);
});
