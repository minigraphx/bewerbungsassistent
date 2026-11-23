"use strict";
// Known jobs (G109, #385): the words for an ad the app knew already. A saved job advertised again carries its reposts
// (`wieder_ausgeschrieben`: datum, portal, link), so does a discarded hit; one portal's same ad is one hit with several
// links (`weitere` of its own portal, each with its day); a recruiter's ad may point to saved jobs (`vielleicht_dieselbe`).
// No DOM, so it can be tested (tests/wieder_logik.test.cjs); the pages set every text with textContent. Texts in the app
// language through Texte.t (#420, tests/applications_languages.test.cjs).
(function (global) {
  // Loaded before this file on every page; required in the tests.
  const texts = () => (typeof module !== "undefined" ? require("./texte.js") : global.Texte);
  // Bewerbungen shows a repost only while the application is still open, as the brief of the UI/UX review says.
  const FINISHED = ["Absage", "Zusage", "Zurückgezogen", "Verworfen"];
  const REPOSTS = "wieder_ausgeschrieben";
  const MAX_SUSPECTS = 2;
  // reposts.MAX_REPOSTS: the app keeps only the newest, so a full list may stand for more reposts
  const MAX_REPOSTS = 20;

  const parts = iso => (typeof iso === "string" && /^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso.split("-").map(Number) : null);

  /** „18.11.“ */
  function short(iso) {
    const p = parts(iso);
    return p ? `${String(p[2]).padStart(2, "0")}.${String(p[1]).padStart(2, "0")}.` : "";
  }

  /** „18. November“ in the app language, „1er décembre“ in French; German keeps its plain space. */
  function long(iso) {
    const p = parts(iso);
    if (!p) return "";
    const Texte = texts();
    const monat = Texte.monthName(p[1]);
    return p[2] === 1 ? Texte.t("1. {monat}", { monat }) : Texte.t("{tag}. {monat}", { tag: p[2], monat });
  }

  /** Only an https link becomes an address on the page; the app checked it already, the page does not trust that. */
  function safeLink(link) {
    return typeof link === "string" && link.startsWith("https://") && !/\s/.test(link) ? link : "";
  }

  function reposts(record) {
    const list = record && Array.isArray(record[REPOSTS]) ? record[REPOSTS] : [];
    return list.filter(r => r && parts(r.datum) && safeLink(r.link));
  }

  function latest(record) {
    const list = reposts(record);
    return list.length ? list.reduce((a, b) => (b.datum >= a.datum ? b : a)) : null;
  }

  /** The notice on the application's page: { title, text, link } or null. */
  function applicationNotice(entry) {
    const last = latest(entry);
    if (!last) return null;
    const Texte = texts();
    const count = reposts(entry).length;
    const words = { datum: long(last.datum), portal: last.portal, anzahl: count };
    const text = count === 1 ? Texte.t("Am {datum} stand dieses Inserat nochmals auf {portal}.", words)
      : count >= MAX_REPOSTS ? Texte.t("Zuletzt am {datum} auf {portal}, insgesamt mindestens {anzahl}-mal.", words)
        : Texte.t("Zuletzt am {datum} auf {portal}, insgesamt {anzahl}-mal.", words);
    return { title: Texte.t("Wieder ausgeschrieben"), text, link: last.link, linkText: Texte.t("Neues Inserat öffnen") };
  }

  /** The part of the list Bewerbungen, only for open applications; "" otherwise. */
  function listPart(entry) {
    const last = latest(entry);
    const Texte = texts();
    return last && !FINISHED.includes(entry.status) ? Texte.t("wieder ausgeschrieben am {datum}", { datum: short(last.datum) }) : "";
  }

  /** The line below the head of a discarded hit: { text, link, linkText } or null. */
  function discardedLine(hit) {
    const last = hit && hit.zustand === "verworfen" ? latest(hit) : null;
    if (!last) return null;
    const Texte = texts();
    return { text: Texte.t("Wieder ausgeschrieben am {datum} Die Stelle bleibt verworfen.", { datum: short(last.datum) }),
             link: last.link, linkText: Texte.t("Neues Inserat öffnen") };
  }

  const links = hit => (hit && Array.isArray(hit.weitere) ? hit.weitere.filter(w => w && safeLink(w.link)) : []);

  /** Links of other portals, „Auch auf jobscout24“ as before. */
  function otherPortals(hit) {
    const Texte = texts();
    return links(hit).filter(w => w.portal !== hit.portal)
      .map(w => ({ text: Texte.t("Auch auf {portal}", { portal: w.portal }), link: w.link }));
  }

  /** „+1“ in the list counts the other portals, each once. */
  function otherPortalCount(hit) {
    return new Set(links(hit).filter(w => w.portal !== hit.portal).map(w => w.portal)).size;
  }

  /** The same ad on the hit's own portal: { summary, links } or null. */
  function sameAds(hit) {
    const same = links(hit).filter(w => w.portal === hit.portal);
    if (!same.length) return null;
    const Texte = texts();
    const words = { anzahl: same.length, portal: hit.portal };
    return {
      summary: same.length === 1 ? Texte.t("Dasselbe Inserat einmal mehr auf {portal}", words)
        : Texte.t("Dasselbe Inserat {anzahl}-mal mehr auf {portal}", words),
      links: same.map(w => ({
        text: parts(w.datum) ? Texte.t("Inserat vom {datum} öffnen", { datum: short(w.datum) }) : Texte.t("Inserat öffnen"),
        link: w.link,
      })),
    };
  }

  /** A recruiter's ad that may be a saved job: { sentence, entries: [{ text, href }] } or null. */
  function suspected(hit) {
    const found = hit && hit.vielleicht_dieselbe;
    const entries = found && Array.isArray(found.bewerbungen) ? found.bewerbungen.filter(e => e && typeof e.id === "string") : [];
    if (!entries.length) return null;
    const Texte = texts();
    return {
      sentence: typeof found.satz === "string" ? found.satz : "",
      entries: entries.slice(0, MAX_SUSPECTS).map(e => ({ text: Texte.t("„{stelle}“ öffnen", { stelle: e.stelle }),
                                                          href: `/bewerbung?id=${encodeURIComponent(e.id)}` })),
    };
  }

  /**
   * After a run: „12 Inserate aus dem letzten Suchlauf kannte die App schon, mit neuem Link: 9 aus Ihren Bewerbungen,
   * 3 verworfene. Sie stehen nicht unter Neu.“ A part with 0 falls away; `saved` words the first part (Sie or du).
   */
  function runHint(run, saved) {
    const counts = (run && run[REPOSTS]) || {};
    const inRegister = Number.isInteger(counts.bewerbungen) ? counts.bewerbungen : 0;
    const discarded = Number.isInteger(counts.verworfen) ? counts.verworfen : 0;
    const total = inRegister + discarded;
    if (total <= 0) return "";
    const Texte = texts();
    const discardedPart = discarded === 1 ? Texte.t("1 verworfene") : Texte.t("{anzahl} verworfene", { anzahl: discarded });
    const teile = [inRegister ? saved(inRegister) : "", discarded ? discardedPart : ""].filter(Boolean).join(", ");
    return total === 1
      ? Texte.t("1 Inserat aus dem letzten Suchlauf kannte die App schon, mit neuem Link: {teile}. Es steht nicht unter Neu.", { teile })
      : Texte.t("{anzahl} Inserate aus dem letzten Suchlauf kannte die App schon, mit neuem Link: {teile}. Sie stehen nicht unter Neu.",
                { anzahl: total, teile });
  }

  const logic = {
    // A getter, so the mark of Stellen (treffer-wieder.js) follows the app language without a change there.
    get SUSPECT_MARK() {
      const Texte = texts();
      return Texte.t("vielleicht dieselbe Stelle");
    },
    short, long, safeLink, applicationNotice, listPart, discardedLine, otherPortals, otherPortalCount, sameAds, suspected, runHint,
  };
  if (typeof module !== "undefined") module.exports = logic;
  else global.WiederLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
