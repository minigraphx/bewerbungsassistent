"use strict";
// What the search brings on Suche einstellen (G103, #375): the yield line and the mark «ohne Ertrag» at each term (drawn
// by suchliste.js), one caption under the list, the empty searches per term and portal, and in the card Region und
// Pensum what each place brought. The numbers come from GET /api/suche/ertrag, the words from suche-ertrag-logik.js.
window.SucheErtrag = (() => {
  const { el } = window.App;
  const E = window.SucheErtragLogik;
  const $ = id => document.getElementById(id);

  const marke = () => el("span", { class: "term term--flag" }, el("span", { class: "term__word" }, E.OHNE_ERTRAG));

  function zeigeBegriffe(ertrag, lehrstelle) {
    window.Suchliste.ertrag(E.nachBegriff(ertrag));
    const hinweis = $("suchliste-ertrag");
    hinweis.textContent = [E.hinweis(ertrag.laeufe, lehrstelle), E.ohneAngabe(ertrag.ohne_angabe, lehrstelle)].filter(Boolean).join(" ");
    hinweis.hidden = !ertrag.begriffe.length;
    const leer = ertrag.leer;
    $("ertrag-leer").hidden = !leer.length;
    $("ertrag-leer-titel").textContent = E.leerTitel(leer.length, lehrstelle);
    $("ertrag-leer-liste").replaceChildren(...leer.map(eintrag => el("li", {}, E.leerZeile(eintrag))));
  }

  function ortZeile(ort) {
    return el("li", {}, `${E.ortName(ort)}: `, ...window.DotLine.render(E.teile(ort), el), ...(ort.ohne_ertrag ? [" ", marke()] : []));
  }

  function zeigeOrte(orte) {
    $("orte-ertrag").hidden = !orte.length;
    $("orte-ertrag-liste").replaceChildren(...orte.map(ortZeile));
  }

  /** `ertrag` as the route gives it; an apprenticeship search has no places (radius search). */
  function zeige(ertrag) {
    const lehrstelle = ertrag.art === "lehrstelle";
    zeigeBegriffe(ertrag, lehrstelle);
    zeigeOrte(lehrstelle ? [] : ertrag.orte);
  }

  return { zeige };
})();
