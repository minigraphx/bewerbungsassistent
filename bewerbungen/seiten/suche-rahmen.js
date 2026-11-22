"use strict";
// Region und Pensum, Was nicht and the title filter on Suche einstellen (#286, G64): „Ändern“ opens the card's own
// form, „Speichern“ writes to the search profile with drafts, and the page loads anew. Logic in suche-rahmen-logik.js.
// Was nicht also holds the excluded companies (#226, G65), saved to their own list in the data folder, in the same
// request as the profile (#303).
window.SucheRahmen = (() => {
  const { senden, status, el } = window.App;
  const L = window.SucheRahmenLogik;
  const $ = id => document.getElementById(id);
  const KARTEN = ["region", "nicht", "titelfilter"];
  const GESPEICHERT = "Gespeichert. Gilt ab der nächsten Suche.";
  const NICHT_GESPEICHERT = "Nicht gespeichert.";
  const JOBSCOUT24 = "regionen_jobscout24";
  let stand = { werte: {}, laengen: {}, alleKantone: [], alleRegionen: [], alleRegionenJobscout24: [], lehrstelle: false, firmen: [] };

  function kantone(gewaehlt) {
    const an = new Set(gewaehlt || []);
    $("region-kantone").replaceChildren(...stand.alleKantone.map(kanton => el("li", {},
      el("label", { class: "check" }, el("input", { type: "checkbox", value: kanton, checked: an.has(kanton) }), ` ${kanton}`))));
  }

  function regionen(liste, alle, gewaehlt) {
    const an = new Set(gewaehlt || []);
    $(liste).replaceChildren(...alle.map(region => el("li", {},
      el("label", { class: "check" }, el("input", { type: "checkbox", value: region.wert, checked: an.has(region.wert) }), ` ${region.name}`))));
  }

  const gewaehlteRegionen = liste => [...$(liste).querySelectorAll("input:checked")].map(kasten => kasten.value);

  /**
   * The place lines of single portals (#301): only those the profile has, as they go before Wohnort and Kantone; the
   * jobscout24 regions (G107) in every job profile.
   */
  function fuellePortale(werte) {
    const sichtbar = L.portalFelder(werte, stand.lehrstelle);
    const mitRegionen = L.regionenJobscout24(stand.lehrstelle);
    for (const feld of ["orte", "plz", "regionen"]) $(`region-${feld}-feld`).hidden = !sichtbar.includes(feld);
    $(`region-${JOBSCOUT24}-feld`).hidden = !mitRegionen;
    $("region-portale").hidden = !sichtbar.length && !mitRegionen;
    $("region-orte").value = L.alsText(werte.orte);
    $("region-plz").value = L.alsText(werte.plz);
    regionen("region-regionen", stand.alleRegionen, werte.regionen);
    regionen(`region-${JOBSCOUT24}`, stand.alleRegionenJobscout24, werte[JOBSCOUT24]);
  }

  function portalFelder() {
    const gezeigt = feld => !$("region-portale").hidden && !$(`region-${feld}-feld`).hidden;
    const werte = {
      orte: $("region-orte").value,
      plz: $("region-plz").value,
      regionen: gewaehlteRegionen("region-regionen"),
      [JOBSCOUT24]: gewaehlteRegionen(`region-${JOBSCOUT24}`),
    };
    return Object.fromEntries(Object.entries(werte).filter(([feld]) => gezeigt(feld)));
  }

  /** As long as Meine Angaben takes the value (#302); the server checks it again. */
  function begrenze(id, laenge) {
    if (Number.isInteger(laenge)) $(id).maxLength = laenge;
  }

  function fuelleRegion(werte) {
    begrenze("region-wohnort", stand.laengen.wohnort);
    begrenze("region-pensum", stand.laengen.pensum);
    $("region-wohnort").value = werte.wohnort || "";
    kantone(werte.kantone);
    $("kantone-hinweis").textContent = L.kantoneHinweis(stand.lehrstelle);
    $("region-umkreis-feld").hidden = !stand.lehrstelle;
    $("region-umkreis").replaceChildren(...L.umkreisWahl(werte.umkreis_km).map(w => el("option", { value: String(w.wert) }, w.text)));
    $("region-umkreis").value = String(L.umkreisGewaehlt(werte.umkreis_km));
    $("region-pensum-feld").hidden = stand.lehrstelle;
    $("region-pensum").value = werte.pensum || "";
    fuellePortale(werte);
  }

  function fuelle(karte) {
    const werte = stand.werte;
    if (karte === "region") return fuelleRegion(werte);
    if (karte === "nicht") {
      $("nicht-inserat").value = L.alsText(werte.ausschluss);
      $("nicht-im-titel").value = L.alsText(werte.titel_ausschluss);
      $("nicht-firmen").value = L.alsText(stand.firmen.map(firma => firma.name));
      return;
    }
    $("titelfilter-positiv").value = L.alsText(werte.titel_positiv);
    $("titelfilter-ausschluss").value = L.alsText(werte.titel_ausschluss);
  }

  function felder(karte) {
    if (karte === "region") {
      const gewaehlt = [...$("region-kantone").querySelectorAll("input:checked")].map(kasten => kasten.value);
      return { wohnort: $("region-wohnort").value, kantone: gewaehlt, umkreis: $("region-umkreis").value, pensum: $("region-pensum").value,
        ...portalFelder() };
    }
    if (karte === "nicht") return { inserat: $("nicht-inserat").value, titel: $("nicht-im-titel").value, firmen: $("nicht-firmen").value };
    return { positiv: $("titelfilter-positiv").value, ausschluss: $("titelfilter-ausschluss").value };
  }

  function oeffne(karte, offen) {
    const form = $(`${karte}-form`);
    const knopf = $(`${karte}-aendern`);
    if (offen) fuelle(karte);
    form.hidden = !offen;
    knopf.hidden = offen;
    knopf.setAttribute("aria-expanded", String(offen));
    if (offen) [...form.querySelectorAll("input, textarea")].find(feld => !feld.closest("[hidden]"))?.focus();
    else knopf.focus();
  }

  async function speichere(karte, event) {
    event.preventDefault();
    const meldung = $(`${karte}-meldung`);
    try {
      const { pfad, koerper } = L.anfrage(karte, felder(karte), stand.lehrstelle);
      await senden(pfad, koerper);
      oeffne(karte, false);
      status(meldung, GESPEICHERT, "ok");
      document.dispatchEvent(new CustomEvent("suchprofil-geaendert"));
      // Listed hits of a company that is now excluded or back leave or join the list.
      if (karte === "nicht") document.dispatchEvent(new CustomEvent(window.SidebarLogic.HITS_CHANGED));
    } catch (fehler) {
      status(meldung, `${NICHT_GESPEICHERT} ${fehler.message}`, "fehler",
        { input: window.Meldungen.isInputRejection(fehler) ? $(`${karte}-form`) : null });
    }
  }

  /** The values of the profile; a form that is open keeps what the person is typing. */
  function zeige(rahmen, lehrstelle, firmen = []) {
    stand = { werte: rahmen.werte || {}, laengen: rahmen.laengen || {}, alleKantone: rahmen.alle_kantone || [],
      alleRegionen: rahmen.alle_regionen || [], alleRegionenJobscout24: rahmen.alle_regionen_jobscout24 || [], lehrstelle, firmen };
    const proPortal = lehrstelle ? [] : L.proPortalText(rahmen.orte_pro_portal);
    $("portale-orte-titel").hidden = !proPortal.length;
    $("portale-orte-text").hidden = !proPortal.length;
    $("portale-orte-text").replaceChildren(...window.DotLine.render(proPortal, el));
  }

  /** «Regionen wählen» (G107): the region form open, the focus on the first jobscout24 region. */
  function oeffneRegionen() {
    if ($("region-form").hidden) oeffne("region", true);
    $(`region-${JOBSCOUT24}`).querySelector("input")?.focus();
  }

  for (const karte of KARTEN) {
    $(`${karte}-aendern`).addEventListener("click", () => oeffne(karte, true));
    $(`${karte}-abbrechen`).addEventListener("click", () => oeffne(karte, false));
    $(`${karte}-form`).addEventListener("submit", event => speichere(karte, event));
  }

  return { zeige, oeffneRegionen };
})();
