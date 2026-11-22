"use strict";
// Erweitert › Titelfilter on Suche einstellen (G104, #382): the two lists of terms, each with the titles of the last
// run it let through or kept out, and the link under «Im Titel» that opens Erweitert at this section. Words and
// order come from titelfilter-logik.js; the terms from /api/suche/rahmen, the examples from /api/suche/ertrag.
window.TitelfilterBeispiele = (() => {
  const { el } = window.App;
  const L = window.TitelfilterLogik;
  const $ = id => document.getElementById(id);
  let stand = { positiv: [], ausschluss: [], beispiele: null };

  function gruppe(teil) {
    const liste = el("ul", { class: "titelfilter-liste" }, ...teil.eintraege.map(eintrag => el("li", {},
      el("span", { class: "titelfilter-liste__begriff" }, eintrag.begriff),
      ...(eintrag.zeile ? [el("span", { class: "caption titelfilter-liste__zeile" }, eintrag.zeile)] : []))));
    const nachsatz = teil.nachsatz ? [el("p", { class: "caption titelfilter-nachsatz" }, teil.nachsatz)] : [];
    return el("div", { class: "titelfilter-gruppe" }, el("p", { class: "field__label" }, teil.titel), liste, ...nachsatz);
  }

  function zeichne() {
    const ansicht = L.ansicht(stand.positiv, stand.ausschluss, stand.beispiele);
    const kopf = [ansicht.leer, ansicht.hinweis].filter(Boolean).map(satz => el("p", { class: "field__hint" }, satz));
    $("titelfilter-beispiele").replaceChildren(...kopf, ...ansicht.gruppen.map(gruppe));
  }

  /** The terms of the profile; the examples stay until newer ones arrive. */
  function begriffe(positiv, ausschluss) {
    stand = { ...stand, positiv: positiv || [], ausschluss: ausschluss || [] };
    zeichne();
  }

  /** The examples of the last run as the yield route gives them; null for an apprenticeship search. */
  function beispiele(daten) {
    stand = { ...stand, beispiele: daten || null };
    zeichne();
  }

  /** Erweitert opens and the heading of the section takes the focus, so a screen reader starts there. */
  function oeffne() {
    $("erweitert").open = true;
    const titel = $("titelfilter-titel");
    titel.scrollIntoView({ block: "start" });
    titel.focus();
  }

  $("titelfilter-link").addEventListener("click", event => {
    event.preventDefault();
    oeffne();
  });

  return { begriffe, beispiele, oeffne };
})();
