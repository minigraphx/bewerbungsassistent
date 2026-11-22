"use strict";
// «Was die App gezählt hat» on /suchbegriffe (G108, #383): above the proposal, from GET /api/suchbegriffe/gezaehlt,
// shown at once while the AI works, since the app counts without it. Only flagged keywords are listed, each with a
// .term--flag chip; every keyword with its numbers stands in the details below, then the niches (#393). The words come
// from SuchbegriffeLogik.
(() => {
  const { holen, el } = window.App;
  const L = window.SuchbegriffeLogik;
  const $ = id => document.getElementById(id);

  const flag = wort => el("span", { class: "term term--flag" }, el("span", { class: "term__word" }, wort));

  function zeile({ name, marke, rest }) {
    return el("li", { class: "terms-counted__row" }, el("span", { class: "term__name" }, name), " ", flag(marke), rest);
  }

  function tabelle(reihen) {
    const kopf = el("tr", {}, ...L.TABELLE_SPALTEN.map((spalte, i) => el("th", { scope: "col", class: i ? "num" : "" }, spalte)));
    const zeilen = reihen.map(r => el("tr", {},
      el("th", { scope: "row" }, ...window.DotLine.render([r.begriff, r.zusatz], el), ...(r.marke ? [" ", flag(r.marke)] : [])),
      ...r.zahlen.map(zahl => el("td", { class: "num" }, String(zahl)))));
    return el("table", { class: "table terms-counted__table" }, el("thead", {}, kopf), el("tbody", {}, ...zeilen));
  }

  function zeichne(z) {
    const wenige = L.zuWenigeLaeufe(z);
    const markiert = L.markiert(z);
    $("gezaehlt-titel").textContent = L.GEZAEHLT_TITEL;
    $("gezaehlt-unterzeile").textContent = wenige || L.gezaehltUnterzeile(z);
    $("gezaehlt-liste").replaceChildren(...markiert.map(zeile));
    $("gezaehlt-liste").hidden = !markiert.length;
    $("gezaehlt-nichts").textContent = L.NICHTS_MARKIERT;
    $("gezaehlt-nichts").hidden = Boolean(wenige) || markiert.length > 0;
    $("gezaehlt-alle-titel").textContent = L.TABELLE_TITEL;
    const reihen = L.tabellenZeilen(z);
    $("gezaehlt-tabelle").replaceChildren(tabelle(reihen));
    $("gezaehlt-alle").hidden = Boolean(wenige) || !reihen.length;
    $("gezaehlt").hidden = false;
  }

  /** A failed request names its reason in the section; the proposal does not depend on it. */
  function fehler(grund) {
    $("gezaehlt-titel").textContent = L.GEZAEHLT_TITEL;
    $("gezaehlt-unterzeile").textContent = L.gezaehltFehler(grund);
    $("gezaehlt-liste").hidden = true;
    $("gezaehlt-nichts").hidden = true;
    $("gezaehlt-alle").hidden = true;
    $("gezaehlt").hidden = false;
  }

  /** Without a job profile the section stays hidden. */
  async function zeige() {
    let z;
    try {
      z = await holen("/api/suchbegriffe/gezaehlt");
    } catch (grund) {
      fehler(grund.message);
      return;
    }
    if (z.verfuegbar) zeichne(z);
  }

  window.SuchbegriffeGezaehlt = { zeige };
})();
