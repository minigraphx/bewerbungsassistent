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
    window.Suchliste.ertrag(E.nachBegriff(ertrag), ertrag.laeufe);
    const mitListe = ertrag.begriffe.length > 0;
    const pflicht = ertrag.ohne_pflichtbezug || [];
    const hinweis = $("suchliste-ertrag");
    hinweis.textContent = E.hinweis(ertrag.laeufe, lehrstelle, pflicht.length > 0);
    hinweis.hidden = !mitListe;
    const ohneAngabe = $("suchliste-ohne-angabe");
    ohneAngabe.textContent = E.ohneAngabe(ertrag.ohne_angabe, lehrstelle);
    ohneAngabe.hidden = !mitListe || !ohneAngabe.textContent;
    const leer = ertrag.leer;
    $("ertrag-leer").hidden = !leer.length;
    $("ertrag-leer-titel").textContent = E.leerTitel(leer.length, lehrstelle);
    $("ertrag-leer-liste").replaceChildren(...leer.map(eintrag => el("li", {}, E.leerZeile(eintrag))));
    // G110: what the required words of a term kept out
    $("ertrag-pflicht").hidden = !pflicht.length;
    $("ertrag-pflicht-titel").textContent = E.pflichtTitel(pflicht);
    $("ertrag-pflicht-liste").replaceChildren(...pflicht.map(eintrag => el("li", {}, E.pflichtZeile(eintrag))));
  }

  function ortZeile(ort) {
    const ausserhalb = E.ausserhalbOrte(ort);  // G111: where the niche hits outside the region lay
    return el("li", {}, `${E.ortName(ort)}: `, ...window.DotLine.render(E.teile(ort), el), ...(ort.ohne_ertrag ? [" ", marke()] : []),
      ...(ausserhalb ? [el("p", { class: "caption ertrag-ausserhalb" }, ausserhalb)] : []));
  }

  function zeigeOrte(orte, laeufe, du) {
    $("orte-ertrag").hidden = !orte.length;
    $("orte-ertrag-hinweis").textContent = E.ortHinweis(laeufe, orte.some(ort => ort.ausserhalb_region > 0), du);
    $("orte-ertrag-liste").replaceChildren(...orte.map(ortZeile));
  }

  /** `ertrag` as the route gives it; an apprenticeship search has no places (radius search). `satz`: the text set. */
  function zeige(ertrag, satz) {
    const lehrstelle = ertrag.art === "lehrstelle";
    zeigeBegriffe(ertrag, lehrstelle);
    zeigeOrte(lehrstelle ? [] : ertrag.orte, ertrag.laeufe, satz === "stelle-du");
  }

  return { zeige };
})();
