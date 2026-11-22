// Known jobs (G109, #385): the words of the UI/UX review for reposts, the same ad of one portal, recruiter suggestions
// and the hint after a run. Invented data only.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const W = require("../seiten/wieder-logik.js");
const texte = require("../seiten/texte.js");

const PAGES = path.join(__dirname, "..", "seiten");
const NO_BREAK_SPACE = String.fromCharCode(160);
const read = name => fs.readFileSync(path.join(PAGES, name), "utf8");
const repost = (datum, portal = "jobs.ch", link = `https://www.jobs.ch/x/${datum}`) => ({ datum, portal, link });
const saved = satz => n => texte.text("suche.wieder-bewerbungen", satz, { anzahl: n });

test("the application's page says when the job came again, once and several times", () => {
  assert.deepEqual(W.applicationNotice({ status: "Beworben", wieder_ausgeschrieben: [repost("2026-11-18")] }), {
    title: "Wieder ausgeschrieben", text: "Am 18. November stand dieses Inserat nochmals auf jobs.ch.",
    link: "https://www.jobs.ch/x/2026-11-18", linkText: "Neues Inserat öffnen",
  });
  const three = { wieder_ausgeschrieben: [repost("2026-11-04", "jobscout24", "https://www.jobscout24.ch/a"), repost("2026-11-18"), repost("2026-11-11")] };
  assert.equal(W.applicationNotice(three).text, "Zuletzt am 18. November auf jobs.ch, insgesamt 3-mal.");
  assert.equal(W.applicationNotice({ link: "https://www.jobs.ch/alt" }), null);
});

test("a full repost list says «mindestens», since the app keeps only the newest 20", () => {
  const days = n => Array.from({ length: n }, (_, i) => repost(`2026-11-${String(i + 1).padStart(2, "0")}`));
  assert.equal(W.applicationNotice({ wieder_ausgeschrieben: days(20) }).text,
    "Zuletzt am 20. November auf jobs.ch, insgesamt mindestens 20-mal.");
  assert.equal(W.applicationNotice({ wieder_ausgeschrieben: days(19) }).text, "Zuletzt am 19. November auf jobs.ch, insgesamt 19-mal.");
});

test("the list Bewerbungen names the repost for open applications only", () => {
  const entry = status => ({ status, wieder_ausgeschrieben: [repost("2026-11-18")] });
  assert.equal(W.listPart(entry("Gemerkt")), "wieder ausgeschrieben am 18.11.");
  assert.equal(W.listPart(entry("Beworben")), "wieder ausgeschrieben am 18.11.");
  for (const status of ["Absage", "Zusage", "Zurückgezogen", "Verworfen"]) assert.equal(W.listPart(entry(status)), "");
});

test("a discarded hit says it came again and stays discarded", () => {
  const hit = { zustand: "verworfen", wieder_ausgeschrieben: [repost("2026-11-18")] };
  assert.deepEqual(W.discardedLine(hit), { text: "Wieder ausgeschrieben am 18.11. Die Stelle bleibt verworfen.",
                                          link: "https://www.jobs.ch/x/2026-11-18", linkText: "Neues Inserat öffnen" });
  assert.equal(W.discardedLine({ ...hit, zustand: "neu" }), null);
});

test("the same ad of one portal is one hit with a link per ad; +N counts other portals only", () => {
  const hit = { portal: "jobs.ch", weitere: [
    { portal: "jobscout24", link: "https://www.jobscout24.ch/a" },
    { portal: "jobs.ch", link: "https://www.jobs.ch/2", datum: "2026-11-12" },
    { portal: "jobs.ch", link: "https://www.jobs.ch/3", datum: "2026-11-13" },
    { portal: "jobs.ch", link: "https://www.jobs.ch/4", datum: "2026-11-14" },
    { portal: "jobs.ch", link: "https://www.jobs.ch/5", datum: "2026-11-15" },
  ] };
  assert.deepEqual(W.sameAds(hit).summary, "Dasselbe Inserat 4-mal mehr auf jobs.ch");
  assert.deepEqual(W.sameAds(hit).links[0], { text: "Inserat vom 12.11. öffnen", link: "https://www.jobs.ch/2" });
  assert.deepEqual(W.otherPortals(hit), [{ text: "Auch auf jobscout24", link: "https://www.jobscout24.ch/a" }]);
  assert.equal(W.otherPortalCount(hit), 1);
  assert.equal(W.otherPortalCount({ portal: "jobs.ch", weitere: hit.weitere.slice(1) }), 0);
  assert.equal(W.sameAds({ portal: "jobs.ch", weitere: hit.weitere.slice(0, 2) }).summary, "Dasselbe Inserat einmal mehr auf jobs.ch");
  assert.equal(W.sameAds({ portal: "jobs.ch", weitere: hit.weitere.slice(0, 1) }), null);
});

test("a link that is not https never becomes an address", () => {
  const hit = { portal: "jobs.ch", weitere: [{ portal: "jobs.ch", link: "javascript:alert(1)", datum: "2026-11-12" }] };
  assert.equal(W.sameAds(hit), null);
  assert.equal(W.discardedLine({ zustand: "verworfen", wieder_ausgeschrieben: [repost("2026-11-18", "jobs.ch", "http://x")] }), null);
});

test("a recruiter's ad points to at most two saved jobs", () => {
  const hit = { vielleicht_dieselbe: { satz: "Könnte dieselbe Stelle sein wie „Data Engineer“ bei Muster AG (Gemerkt) in Ihren Bewerbungen.",
    bewerbungen: [{ id: "muster-ag", stelle: "Data Engineer" }, { id: "b", stelle: "B" }, { id: "c", stelle: "C" }] } };
  const found = W.suspected(hit);
  assert.equal(found.sentence, hit.vielleicht_dieselbe.satz);
  assert.deepEqual(found.entries, [{ text: "„Data Engineer“ öffnen", href: "/bewerbung?id=muster-ag" }, { text: "„B“ öffnen", href: "/bewerbung?id=b" }]);
  assert.equal(W.suspected({}), null);
  assert.equal(W.SUSPECT_MARK, "vielleicht dieselbe Stelle");
  assert.equal(texte.text("suche.vielleicht-titel", "stelle-sie"), "Vielleicht schon in Ihren Bewerbungen");
  assert.equal(texte.text("suche.vielleicht-titel", "stelle-du"), "Vielleicht schon in deinen Bewerbungen");
});

test("the hint after a run counts what the app knew, without a part at 0", () => {
  const run = (bewerbungen, verworfen) => ({ wieder_ausgeschrieben: { bewerbungen, verworfen } });
  assert.equal(W.runHint(run(9, 3), saved("stelle-sie")),
    "12 Inserate aus dem letzten Suchlauf kannte die App schon, mit neuem Link: 9 aus Ihren Bewerbungen, 3 verworfene. Sie stehen nicht unter Neu.");
  assert.equal(W.runHint(run(9, 3), saved("stelle-du")),
    "12 Inserate aus dem letzten Suchlauf kannte die App schon, mit neuem Link: 9 aus deinen Bewerbungen, 3 verworfene. Sie stehen nicht unter Neu.");
  assert.equal(W.runHint(run(0, 3), saved("stelle-sie")),
    "3 Inserate aus dem letzten Suchlauf kannte die App schon, mit neuem Link: 3 verworfene. Sie stehen nicht unter Neu.");
  assert.equal(W.runHint(run(1, 0), saved("stelle-sie")),
    "1 Inserat aus dem letzten Suchlauf kannte die App schon, mit neuem Link: 1 aus Ihren Bewerbungen. Es steht nicht unter Neu.");
  assert.equal(W.runHint({ portale: {} }, saved("stelle-sie")), "");
});

test("the pages load the logic, the app serves it, and no text has a raw no-break space", () => {
  const app = fs.readFileSync(path.join(__dirname, "..", "app.py"), "utf8");
  assert.match(app, /"\/wieder-logik\.js": "wieder-logik\.js"/);
  for (const page of ["treffer.html", "bewerbungen.html", "bewerbung.html"]) assert.match(read(page), /<script src="\/wieder-logik\.js"><\/script>/);
  for (const file of ["wieder-logik.js", "treffer-wieder.js", "bewerbung-wieder.js"]) assert.ok(!read(file).includes(NO_BREAK_SPACE), file);
});
