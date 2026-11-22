"use strict";
// Known jobs (G109, #385): the words for an ad the app knew already. A saved job advertised again carries its reposts
// (`wieder_ausgeschrieben`: datum, portal, link), so does a discarded hit; one portal's same ad is one hit with several
// links (`weitere` of its own portal, each with its day); a recruiter's ad may point to saved jobs (`vielleicht_dieselbe`).
// No DOM, so it can be tested (tests/wieder_logik.test.cjs); the pages set every text with textContent.
(function (global) {
  const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];
  // Bewerbungen shows a repost only while the application is still open, as the brief of the UI/UX review says.
  const FINISHED = ["Absage", "Zusage", "Zurückgezogen", "Verworfen"];
  const REPOSTS = "wieder_ausgeschrieben";
  const TITLE = "Wieder ausgeschrieben";
  const OPEN_NEW = "Neues Inserat öffnen";
  const SUSPECT_MARK = "vielleicht dieselbe Stelle";
  const MAX_SUSPECTS = 2;

  const parts = iso => (typeof iso === "string" && /^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso.split("-").map(Number) : null);

  /** „18.11.“ */
  function short(iso) {
    const p = parts(iso);
    return p ? `${String(p[2]).padStart(2, "0")}.${String(p[1]).padStart(2, "0")}.` : "";
  }

  /** „18. November“ */
  function long(iso) {
    const p = parts(iso);
    return p ? `${p[2]}. ${MONTHS[p[1] - 1]}` : "";
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
    const count = reposts(entry).length;
    const text = count === 1 ? `Am ${long(last.datum)} stand dieses Inserat nochmals auf ${last.portal}.`
      : `Zuletzt am ${long(last.datum)} auf ${last.portal}, insgesamt ${count}-mal.`;
    return { title: TITLE, text, link: last.link, linkText: OPEN_NEW };
  }

  /** The part of the list Bewerbungen, only for open applications; "" otherwise. */
  function listPart(entry) {
    const last = latest(entry);
    return last && !FINISHED.includes(entry.status) ? `wieder ausgeschrieben am ${short(last.datum)}` : "";
  }

  /** The line below the head of a discarded hit: { text, link, linkText } or null. */
  function discardedLine(hit) {
    const last = hit && hit.zustand === "verworfen" ? latest(hit) : null;
    return last ? { text: `Wieder ausgeschrieben am ${short(last.datum)} Die Stelle bleibt verworfen.`, link: last.link, linkText: OPEN_NEW } : null;
  }

  const links = hit => (hit && Array.isArray(hit.weitere) ? hit.weitere.filter(w => w && safeLink(w.link)) : []);

  /** Links of other portals, „Auch auf jobscout24“ as before. */
  function otherPortals(hit) {
    return links(hit).filter(w => w.portal !== hit.portal).map(w => ({ text: `Auch auf ${w.portal}`, link: w.link }));
  }

  /** „+1“ in the list counts the other portals, each once. */
  function otherPortalCount(hit) {
    return new Set(links(hit).filter(w => w.portal !== hit.portal).map(w => w.portal)).size;
  }

  /** The same ad on the hit's own portal: { summary, links } or null. */
  function sameAds(hit) {
    const same = links(hit).filter(w => w.portal === hit.portal);
    if (!same.length) return null;
    const times = same.length === 1 ? "einmal" : `${same.length}-mal`;
    return {
      summary: `Dasselbe Inserat ${times} mehr auf ${hit.portal}`,
      links: same.map(w => ({ text: parts(w.datum) ? `Inserat vom ${short(w.datum)} öffnen` : "Inserat öffnen", link: w.link })),
    };
  }

  /** A recruiter's ad that may be a saved job: { sentence, entries: [{ text, href }] } or null. */
  function suspected(hit) {
    const found = hit && hit.vielleicht_dieselbe;
    const entries = found && Array.isArray(found.bewerbungen) ? found.bewerbungen.filter(e => e && typeof e.id === "string") : [];
    if (!entries.length) return null;
    return {
      sentence: typeof found.satz === "string" ? found.satz : "",
      entries: entries.slice(0, MAX_SUSPECTS).map(e => ({ text: `„${e.stelle}“ öffnen`, href: `/bewerbung?id=${encodeURIComponent(e.id)}` })),
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
    const named = [inRegister ? saved(inRegister) : "", discarded ? `${discarded} verworfene` : ""].filter(Boolean).join(", ");
    const ads = total === 1 ? "1 Inserat" : `${total} Inserate`;
    return `${ads} aus dem letzten Suchlauf kannte die App schon, mit neuem Link: ${named}. ${total === 1 ? "Es steht" : "Sie stehen"} nicht unter Neu.`;
  }

  const logic = { SUSPECT_MARK, TITLE, OPEN_NEW, short, long, safeLink, applicationNotice, listPart, discardedLine,
                  otherPortals, otherPortalCount, sameAds, suspected, runHint };
  if (typeof module !== "undefined") module.exports = logic;
  else global.WiederLogik = logic;
})(typeof window !== "undefined" ? window : globalThis);
