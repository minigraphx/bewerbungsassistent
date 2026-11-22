"use strict";
// Stellen, known jobs (G109, #385): the line of a discarded job advertised again, the notice of a recruiter's ad that
// may be a saved job, its chip in the list, and the same ad of one portal behind a details. Words in wieder-logik.js;
// every text goes in with textContent (App.el), every address passed WiederLogik.safeLink.
(() => {
  const { el } = window.App;
  const W = window.WiederLogik;
  const outside = (href, text) => el("a", { href, target: "_blank", rel: "noopener" }, text);

  /** Below the head of a discarded hit: when it came again, and the new ad. */
  function zeile(treffer) {
    const line = W.discardedLine(treffer);
    return line ? el("p", { class: "search__hint" }, `${line.text} `, outside(line.link, line.linkText)) : null;
  }

  /** The hit stays listed; the notice names the saved jobs it may be, and the person decides. */
  function vermittler(treffer, titel) {
    const found = W.suspected(treffer);
    if (!found) return null;
    return el("div", { class: "notice" }, el("span", { class: "notice__title" }, titel),
      el("p", { class: "notice__body" }, found.sentence),
      el("ul", { class: "search__more" }, found.entries.map(e => el("li", {}, el("a", { href: e.href }, e.text)))));
  }

  /** The chip in the row of such a hit, or "" so that the «·» line leaves it out. */
  function marke(treffer) {
    return W.suspected(treffer) ? el("span", { class: "term term--flag" }, el("span", { class: "term__word" }, W.SUSPECT_MARK)) : "";
  }

  /** „Dasselbe Inserat 4-mal mehr auf jobs.ch“, closed; a link per ad with its day. */
  function gleicheInserate(treffer) {
    const same = W.sameAds(treffer);
    if (!same) return null;
    return el("details", { class: "search__same" }, el("summary", {}, same.summary),
      el("ul", { class: "search__more" }, same.links.map(ad => el("li", {}, outside(ad.link, ad.text)))));
  }

  window.TrefferWieder = { zeile, vermittler, marke, gleicheInserate };
})();
